from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.app.core.database import get_db
from backend.app.api.v1.admin.auth import get_current_admin
from backend.app.models.automation import SystemAlert
from backend.app.models.audit import SecurityEvent

router = APIRouter(prefix="/alerts", tags=["Admin Alerts & Security"])

class AlertResolveRequest(BaseModel):
    notes: Optional[str] = "Resolved by administrator."

@router.get("")
def list_system_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Lists system alerts with optional filtering by status and severity."""
    query = db.query(SystemAlert)
    if status:
        query = query.filter(SystemAlert.status == status.upper())
    if severity:
        query = query.filter(SystemAlert.severity == severity.upper())

    alerts = query.order_by(SystemAlert.created_at.desc()).limit(100).all()
    return {
        "total": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "source": a.source,
                "title": a.title,
                "message": a.message,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "acknowledged_by": a.acknowledged_by,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
                "resolved_by": a.resolved_by,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "resolution_notes": a.resolution_notes,
                "metadata": a.metadata_json
            }
            for a in alerts
        ]
    }

@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db), current_admin = Depends(get_current_admin)):
    """Acknowledges an open system alert."""
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = current_admin.email
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "status": "ACKNOWLEDGED", "alert_id": alert_id}

@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    req: AlertResolveRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Resolves a system alert with resolution notes."""
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "RESOLVED"
    alert.resolved_by = current_admin.email
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_notes = req.notes
    db.commit()

    return {"success": True, "status": "RESOLVED", "alert_id": alert_id}

@router.get("/security-events")
def list_security_events(
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """Lists recorded security events (failed logins, token misuse, injection attempts)."""
    query = db.query(SecurityEvent)
    if severity:
        query = query.filter(SecurityEvent.severity == severity.upper())

    events = query.order_by(SecurityEvent.created_at.desc()).limit(limit).all()
    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "source_ip": e.source_ip,
                "user_id": e.user_id,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }
