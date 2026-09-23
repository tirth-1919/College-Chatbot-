from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.admin.auth import get_current_admin
from backend.app.models.automation import MaintenanceState
from backend.app.models.admin_system import SystemBackup
from backend.app.automation.jobs import job_backup_creation, job_restore_verification

router = APIRouter(prefix="/maintenance", tags=["Admin Maintenance & Disaster Recovery"])

class ModeUpdateRequest(BaseModel):
    mode: str  # NORMAL, MAINTENANCE, READ_ONLY, EMERGENCY
    message: Optional[str] = None

@router.get("/mode")
def get_maintenance_mode(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Retrieves current system operational mode."""
    state = db.query(MaintenanceState).order_by(MaintenanceState.updated_at.desc()).first()
    if not state:
        state = MaintenanceState(mode="NORMAL", user_message="System is operating normally.")
        db.add(state)
        db.commit()

    return {
        "mode": state.mode,
        "user_message": state.user_message,
        "updated_by": state.updated_by,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None
    }

@router.post("/mode")
def update_maintenance_mode(
    req: ModeUpdateRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Sets system operational mode (NORMAL, MAINTENANCE, READ_ONLY, EMERGENCY)."""
    valid_modes = ["NORMAL", "MAINTENANCE", "READ_ONLY", "EMERGENCY"]
    target_mode = req.mode.upper()
    if target_mode not in valid_modes:
        raise HTTPException(status_code=400, detail=f"Mode must be one of {valid_modes}")

    state = db.query(MaintenanceState).order_by(MaintenanceState.updated_at.desc()).first()
    if not state:
        state = MaintenanceState()
        db.add(state)

    state.mode = target_mode
    if req.message:
        state.user_message = req.message
    elif target_mode == "MAINTENANCE":
        state.user_message = "AI-Powered Colleges Chatbot is undergoing scheduled maintenance. Please check back shortly."
    elif target_mode == "READ_ONLY":
        state.user_message = "System is in read-only mode. New mutations are temporarily suspended."
    elif target_mode == "EMERGENCY":
        state.user_message = "Emergency mode active. Only essential verified knowledge responses are served."
    else:
        state.user_message = "System is operating normally."

    state.updated_by = current_admin.email
    state.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "success": True,
        "mode": state.mode,
        "user_message": state.user_message,
        "updated_at": state.updated_at.isoformat()
    }

@router.get("/backups")
def list_backups(db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Lists database backups and storage paths."""
    backups = db.query(SystemBackup).order_by(SystemBackup.created_at.desc()).limit(20).all()
    return {
        "count": len(backups),
        "backups": [
            {
                "id": b.id,
                "filename": b.filename,
                "backup_type": b.backup_type,
                "size_bytes": b.file_size_bytes,
                "status": b.status,
                "created_by": b.created_by,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in backups
        ]
    }

@router.post("/backups/create")
def trigger_backup(current_admin = Depends(get_current_admin)):
    """Triggers an instant automated backup."""
    return job_backup_creation({})

@router.post("/restore/verify")
def trigger_restore_verification(current_admin = Depends(get_current_admin)):
    """Triggers an automated restore verification check."""
    return job_restore_verification({})
