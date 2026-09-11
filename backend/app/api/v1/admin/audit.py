from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, PERM_AUDIT_READ, PERM_SECURITY_READ
from backend.app.models.audit import AuditLog, SecurityEvent
from backend.app.models.user import User

router = APIRouter(prefix="/security", tags=["Admin Audit & Security"])

@router.get("/audit-logs")
def list_audit_logs(
    limit: int = 100,
    current_user: User = Depends(require_permission(PERM_AUDIT_READ)),
    db: Session = Depends(get_db)
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "resource": l.resource,
            "status": l.status,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat() if l.created_at else None
        }
        for l in logs
    ]

@router.get("/security-events")
def list_security_events(
    limit: int = 50,
    current_user: User = Depends(require_permission(PERM_SECURITY_READ)),
    db: Session = Depends(get_db)
):
    events = (
        db.query(SecurityEvent)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "ip_address": e.ip_address,
            "user_id": e.user_id,
            "payload": e.payload,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in events
    ]
