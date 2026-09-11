from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_CONFLICTS_REVIEW
from backend.app.models.admin_system import KnowledgeConflict
from backend.app.models.user import User
from backend.app.knowledge.conflict_detector import conflict_detector

router = APIRouter(prefix="/conflicts", tags=["Admin Knowledge Conflicts"])

class ConflictResolveRequest(BaseModel):
    resolution_status: str  # RESOLVED_A, RESOLVED_B, SUPERSEDED, DISMISSED
    resolution_notes: Optional[str] = ""

@router.get("")
def list_conflicts(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(KnowledgeConflict)
    if status_filter and status_filter != "ALL":
        query = query.filter(KnowledgeConflict.resolution_status == status_filter)

    conflicts = query.order_by(KnowledgeConflict.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "topic": c.topic,
            "source_a": c.source_a,
            "source_b": c.source_b,
            "value_a": c.value_a,
            "value_b": c.value_b,
            "discrepancy": c.detected_discrepancy,
            "resolution_status": c.resolution_status,
            "resolution_notes": c.resolution_notes,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None
        }
        for c in conflicts
    ]

@router.post("/scan")
def trigger_conflict_scan(
    current_user: User = Depends(require_permission(PERM_CONFLICTS_REVIEW)),
    db: Session = Depends(get_db)
):
    detected = conflict_detector.scan_for_conflicts(db)
    log_admin_audit(db, current_user, "SCAN_KNOWLEDGE_CONFLICTS", "CONFLICTS", {"detected": len(detected)})
    return {
        "status": "success",
        "new_conflicts": len(detected),
        "items": detected
    }

@router.post("/{conflict_id}/resolve")
def resolve_conflict(
    conflict_id: str,
    req: ConflictResolveRequest,
    current_user: User = Depends(require_permission(PERM_CONFLICTS_REVIEW)),
    db: Session = Depends(get_db)
):
    resolved = conflict_detector.resolve_conflict(
        db=db,
        conflict_id=conflict_id,
        resolution_status=req.resolution_status,
        admin_id=current_user.id,
        notes=req.resolution_notes or ""
    )
    if not resolved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict record not found")

    log_admin_audit(db, current_user, "RESOLVE_KNOWLEDGE_CONFLICT", "CONFLICT", {
        "id": conflict_id,
        "status": req.resolution_status
    })

    return {
        "message": "Conflict resolved successfully",
        "resolution_status": resolved.resolution_status
    }
