from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from backend.app.core.database import get_db
from backend.app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from backend.app.core.config import settings
from backend.app.models.user import User, UserSession
from backend.app.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

def _validate_password_policy(password: str) -> None:
    """P2-13: Enforce minimum password security requirements."""
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Password must contain at least one digit")

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication token")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid or expired")
    user = db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user

def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    return db.query(User).filter(User.id == payload["sub"], User.is_active == True).first()

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    # P1-9: rate limiting
    rate_limiter.enforce("signup", request)
    # P2-13: password policy
    _validate_password_policy(req.password)

    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    # Default signup links user to AIT (first tenant) for backward compatibility.
    # Future: accept college_code or slug in the signup request.
    from backend.app.models.college import College
    AIT_TENANT_ID = "ait-default-tenant-0001"
    ait_college = db.query(College).filter(College.id == AIT_TENANT_ID, College.status == "ACTIVE").first()
    if not ait_college:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Platform not fully configured. Contact administrator.")

    new_user = User(
        email=req.email,
        hashed_password=get_password_hash(req.password),
        full_name=req.full_name,
        role="STUDENT",
        college_id=AIT_TENANT_ID,
        is_verified=True  # For development ease
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token({"sub": new_user.id, "email": new_user.email, "role": new_user.role, "college_id": new_user.college_id})
    refresh_token = create_refresh_token({"sub": new_user.id})

    # Save session
    session = UserSession(
        user_id=new_user.id,
        refresh_token_hash=get_password_hash(refresh_token[:16]),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "college_id": new_user.college_id
        }
    }

@router.post("/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    # P1-9: rate limiting
    rate_limiter.enforce("login", request)

    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    # Validate college status for non-super-admin users
    if user.college_id and (user.role or "").upper() != "SUPER_ADMIN":
        from backend.app.models.college import College
        college = db.query(College).filter(College.id == user.college_id).first()
        if college and college.status == "SUSPENDED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your college account is suspended. Contact platform administrator.")

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role, "college_id": user.college_id})
    refresh_token = create_refresh_token({"sub": user.id})

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=get_password_hash(refresh_token[:16]),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "must_change_password": bool(user.must_change_password),
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "college_id": user.college_id
        }
    }

@router.post("/refresh")
def refresh_token(req: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    # P1-9: rate limiting
    rate_limiter.enforce("login", request)

    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer active")

    # P1-6 FIX: Validate that a non-revoked, non-expired session exists for this user.
    # This prevents refresh token reuse after logout or session revocation.
    now = datetime.now(timezone.utc)
    valid_sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False,
        UserSession.expires_at > now
    ).all()
    valid_session = next(
        (session for session in valid_sessions
         if verify_password(req.refresh_token[:16], session.refresh_token_hash)),
        None,
    )
    if not valid_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Refresh token is invalid or has been revoked. Please log in again.")

    new_access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role, "college_id": user.college_id})
    return {"access_token": new_access_token}

@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """P1-8: Revoke the current user's active sessions (logout)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload["sub"]
    # Revoke all active sessions for this user
    now = datetime.now(timezone.utc)
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_revoked == False
    ).all()
    for s in sessions:
        s.is_revoked = True
        s.revoked_at = now
    db.commit()

    return {"message": "Logged out successfully"}

@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    college_info = None
    if current_user.college_id:
        from backend.app.models.college import College
        college = db.query(College).filter(College.id == current_user.college_id).first()
        if college:
            college_info = {
                "id": college.id,
                "name": college.name,
                "code": college.code,
                "slug": college.slug,
                "logo_url": college.logo_url,
                "assistant_name": college.assistant_name or "AI Assistant",
                "welcome_message": college.welcome_message,
                "primary_color": college.primary_color or "#0b0a3e",
                "secondary_color": college.secondary_color or "#1a2345",
                "accent_color": college.accent_color or "#f08518",
                "status": college.status,
            }
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "college_id": current_user.college_id,
        "must_change_password": bool(current_user.must_change_password),
        "is_verified": current_user.is_verified,
        "college": college_info,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

class FirstPasswordChangeRequest(BaseModel):
    new_password: str

@router.post("/change-first-password")
def change_first_password(
    req: FirstPasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force-password-change endpoint for College Admins logging in for the first time."""
    if not current_user.must_change_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password change not required.")
    _validate_password_policy(req.new_password)
    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "Password changed successfully. Please log in again with your new password."}

@router.post("/privacy/export")
def export_my_data(current_user: User = Depends(get_current_user)):
    """Exports user conversations and attachments (GDPR / Privacy compliant)."""
    from backend.app.security.privacy import privacy_manager
    return privacy_manager.export_user_data(current_user.id)

@router.delete("/privacy/delete-account")
def delete_my_account(current_user: User = Depends(get_current_user)):
    """Permanently erases user account and all personal conversation data."""
    from backend.app.security.privacy import privacy_manager
    return privacy_manager.delete_user_account(current_user.id)

@router.get("/oauth/google/status")
def google_oauth_status():
    """
    Returns OAuth availability. If not configured, gracefully provides notification
    without breaking email/password authentication.
    """
    is_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    return {
        "provider": "google",
        "is_configured": is_configured,
        "client_id": settings.GOOGLE_CLIENT_ID if is_configured else None,
        "status_message": "Google OAuth is ready" if is_configured else "Google OAuth credentials not configured in environment. Please log in with email/password."
    }
