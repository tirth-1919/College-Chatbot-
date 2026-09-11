from typing import List, Optional, Callable
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import decode_token
from backend.app.models.user import User
from backend.app.models.audit import AuditLog

# Standard System Permissions
PERM_KNOWLEDGE_READ = "knowledge.read"
PERM_KNOWLEDGE_CREATE = "knowledge.create"
PERM_KNOWLEDGE_UPDATE = "knowledge.update"
PERM_KNOWLEDGE_PUBLISH = "knowledge.publish"
PERM_KNOWLEDGE_ROLLBACK = "knowledge.rollback"
PERM_KNOWLEDGE_DELETE = "knowledge.delete"
PERM_WEBSITE_SYNC = "website.sync"
PERM_DOCUMENTS_MANAGE = "documents.manage"
PERM_IMAGES_MANAGE = "images.manage"
PERM_RAG_MANAGE = "rag.manage"
PERM_CONFLICTS_REVIEW = "conflicts.review"
PERM_AI_READ = "ai.read"
PERM_AI_CONFIGURE = "ai.configure"
PERM_AI_FAILOVER = "ai.failover"
PERM_AI_QUOTA_READ = "ai.quota.read"
PERM_AI_MODEL_CHANGE = "ai.model.change"
PERM_USERS_READ = "users.read"
PERM_USERS_MANAGE = "users.manage"
PERM_ANALYTICS_READ = "analytics.read"
PERM_AUTOMATION_MANAGE = "automation.manage"
PERM_JOBS_MANAGE = "jobs.manage"
PERM_SECURITY_READ = "security.read"
PERM_AUDIT_READ = "audit.read"
PERM_SYSTEM_CONFIGURE = "system.configure"
PERM_BACKUP_MANAGE = "backup.manage"
PERM_SUPERADMIN_MANAGE = "superadmin.manage"

ALL_ADMIN_PERMISSIONS = [
    PERM_KNOWLEDGE_READ, PERM_KNOWLEDGE_CREATE, PERM_KNOWLEDGE_UPDATE, PERM_KNOWLEDGE_PUBLISH,
    PERM_KNOWLEDGE_ROLLBACK, PERM_KNOWLEDGE_DELETE, PERM_WEBSITE_SYNC, PERM_DOCUMENTS_MANAGE,
    PERM_IMAGES_MANAGE, PERM_RAG_MANAGE, PERM_CONFLICTS_REVIEW, PERM_AI_READ, PERM_AI_CONFIGURE,
    PERM_AI_FAILOVER, PERM_AI_QUOTA_READ, PERM_AI_MODEL_CHANGE, PERM_USERS_READ, PERM_USERS_MANAGE,
    PERM_ANALYTICS_READ, PERM_AUTOMATION_MANAGE, PERM_JOBS_MANAGE, PERM_SECURITY_READ, PERM_AUDIT_READ,
    PERM_SYSTEM_CONFIGURE, PERM_BACKUP_MANAGE
]

def get_current_admin_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates token and ensures user has an active administrative role (ADMIN or SUPER_ADMIN).
    Rejects unauthorized student users with HTTP 403.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired"
        )
    
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated"
        )
    
    user_role = (user.role or "").upper()
    if user_role not in ["ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    
    return user

def require_super_admin(current_user: User = Depends(get_current_admin_user)) -> User:
    """Ensures caller has SUPER_ADMIN role for high-risk operations."""
    if (current_user.role or "").upper() != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action restricted to Super Administrators only."
        )
    return current_user

def require_permission(permission: str) -> Callable:
    """Dependency factory checking if admin has the requested permission."""
    def dependency(current_user: User = Depends(get_current_admin_user)) -> User:
        user_role = (current_user.role or "").upper()
        if user_role == "SUPER_ADMIN":
            return current_user
        
        user_perms = current_user.permissions or []
        # Normal ADMIN has ALL_ADMIN_PERMISSIONS by default unless explicitly restricted
        if permission in user_perms or permission in ALL_ADMIN_PERMISSIONS:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: '{permission}'"
        )
    return dependency

def log_admin_audit(
    db: Session,
    user: Optional[User],
    action: str,
    resource: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    status_str: str = "SUCCESS"
):
    """Immutable audit trail logger for admin operations."""
    audit = AuditLog(
        user_id=user.id if user else None,
        action=action,
        resource=resource,
        status=status_str,
        details=details or {},
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
