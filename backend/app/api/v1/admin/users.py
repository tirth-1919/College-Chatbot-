from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_super_admin, require_permission, log_admin_audit, PERM_USERS_MANAGE
from backend.app.models.user import User, UserSession
from backend.app.models.conversation import Conversation

router = APIRouter(prefix="/users", tags=["Admin User Management"])

class RoleChangeRequest(BaseModel):
    role: str  # STUDENT, ADMIN, SUPER_ADMIN

class StatusChangeRequest(BaseModel):
    is_active: bool

@router.get("")
def list_users(
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role_filter and role_filter != "ALL":
        query = query.filter(User.role == role_filter)
    if search:
        s = f"%{search}%"
        query = query.filter((User.email.ilike(s)) | (User.full_name.ilike(s)))

    users = query.order_by(User.created_at.desc()).limit(100).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "mfa_enabled": u.mfa_enabled,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]

@router.post("/{user_id}/role")
def update_user_role(
    user_id: str,
    req: RoleChangeRequest,
    current_user: User = Depends(require_super_admin),  # SUPER_ADMIN ONLY!
    db: Session = Depends(get_db)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role_upper = req.role.upper()
    if role_upper not in ["STUDENT", "ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified")

    old_role = target.role
    target.role = role_upper
    db.commit()

    log_admin_audit(db, current_user, "CHANGE_USER_ROLE", "USER", {
        "target_user_id": target.id,
        "old_role": old_role,
        "new_role": role_upper
    })

    return {"message": f"User role updated to {role_upper}", "user_id": target.id}

@router.post("/{user_id}/status")
def toggle_user_status(
    user_id: str,
    req: StatusChangeRequest,
    current_user: User = Depends(require_permission(PERM_USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    target.is_active = req.is_active
    db.commit()

    log_admin_audit(db, current_user, "TOGGLE_USER_STATUS", "USER", {
        "target_user_id": target.id,
        "is_active": target.is_active
    })

    return {"message": f"User account {'activated' if target.is_active else 'deactivated'}"}

@router.get("/{user_id}/conversations")
def inspect_user_conversations(
    user_id: str,
    current_user: User = Depends(require_permission(PERM_USERS_MANAGE)),
    db: Session = Depends(get_db)
):
    """
    Privacy-controlled, auditable access to student conversation titles & metadata.
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(20)
        .all()
    )

    log_admin_audit(db, current_user, "AUDITED_CONVERSATION_ACCESS", "CONVERSATION", {
        "target_user_id": user_id,
        "record_count": len(conversations)
    })

    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "message_count": len(c.messages)
        }
        for c in conversations
    ]
