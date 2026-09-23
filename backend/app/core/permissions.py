from typing import List, Optional, Callable
from fastapi import Depends, HTTPException, status, Header
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

from backend.app.models.college import College

# Standard Roles
ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_COLLEGE_ADMIN = "COLLEGE_ADMIN"
ROLE_STUDENT = "STUDENT"

def get_current_admin_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Validates token and ensures user has an active administrative role (SUPER_ADMIN or COLLEGE_ADMIN).
    Rejects unauthorized students and validates that the college is not suspended.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    payload = decode_token(raw_token)
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
    if user_role not in ["ADMIN", "COLLEGE_ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    
    # If user belongs to a college, check college suspension status
    if user.college_id and user_role != "SUPER_ADMIN":
        college = db.query(College).filter(College.id == user.college_id).first()
        if not college:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="College record not found."
            )
        if college.status == "SUSPENDED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="College account is suspended. Contact platform administrator."
            )
        if college.status in ["REJECTED", "ARCHIVED"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"College account status is {college.status}. Access denied."
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

def require_college_admin(current_user: User = Depends(get_current_admin_user)) -> User:
    """Ensures caller is at least a COLLEGE_ADMIN or SUPER_ADMIN."""
    role = (current_user.role or "").upper()
    if role not in ["COLLEGE_ADMIN", "ADMIN", "SUPER_ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action restricted to College Administrators."
        )
    return current_user

def verify_tenant_access(current_user: User, target_college_id: Optional[str]) -> None:
    """
    Enforces strict tenant isolation.
    SUPER_ADMIN has platform-wide visibility.
    COLLEGE_ADMIN and STUDENT are strictly confined to their own college.
    """
    if (current_user.role or "").upper() == "SUPER_ADMIN":
        return
    if not current_user.college_id or current_user.college_id != target_college_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Cannot access another college's resources."
        )

def require_permission(permission: str) -> Callable:
    """Dependency factory checking if admin has the requested permission."""
    def dependency(current_user: User = Depends(get_current_admin_user)) -> User:
        user_role = (current_user.role or "").upper()
        if user_role == "SUPER_ADMIN":
            return current_user
        
        user_perms = current_user.permissions or []
        allowed_permissions = ALL_ADMIN_PERMISSIONS if current_user.permissions is None else user_perms
        if "*" in allowed_permissions or permission in allowed_permissions:
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
    status_str: str = "SUCCESS",
    college_id: Optional[str] = None
):
    """Immutable audit trail logger for admin operations, recording college_id."""
    cid = college_id or (user.college_id if user else None)
    audit = AuditLog(
        user_id=user.id if user else None,
        college_id=cid,
        action=action,
        resource=resource,
        status=status_str,
        details=details or {},
        ip_address=ip_address
    )
    db.add(audit)
    db.commit()
