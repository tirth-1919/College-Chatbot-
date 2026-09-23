from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_totp_secret,
    verify_totp_code
)
from backend.app.core.permissions import get_current_admin_user, log_admin_audit
from backend.app.models.user import User, UserSession
from backend.app.security.rate_limiter import rate_limiter

router = APIRouter(prefix="/auth", tags=["Admin Authentication"])

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None

class AdminMfaVerifyRequest(BaseModel):
    temp_token: str
    totp_code: str

class RefreshRequest(BaseModel):
    refresh_token: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login")
def admin_login(req: AdminLoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    user = db.query(User).filter(User.email == req.email).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    # Check account lock
    now = datetime.now(timezone.utc)
    if user.locked_until and user.locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account temporarily locked due to multiple failed attempts. Try again later."
        )

    if not user.hashed_password or not verify_password(req.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    # Verify role
    role = (user.role or "").upper()
    if role not in ["ADMIN", "SUPER_ADMIN", "COLLEGE_ADMIN"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Not an administrator account.")

    # Check 2FA
    if user.mfa_enabled:
        if not req.totp_code:
            # Issue temporary token for MFA challenge
            temp_token = create_access_token({"sub": user.id, "type": "mfa_challenge"}, expires_delta=timedelta(minutes=5))
            return {
                "mfa_required": True,
                "temp_token": temp_token,
                "message": "Two-Factor Authentication code required."
            }
        else:
            if not verify_totp_code(user.mfa_secret, req.totp_code):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA / TOTP code")

    # Successful login: reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "college_id": user.college_id,
        "is_admin": True
    })
    refresh_token = create_refresh_token({"sub": user.id})

    # Record active session
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=get_password_hash(refresh_token[:16]),
        ip_address=ip,
        device_info=request.headers.get("User-Agent", "Unknown Admin Browser")[:255],
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    log_admin_audit(db, user, "ADMIN_LOGIN", "AUTH", {"ip": ip}, ip)

    return {
        "mfa_required": False,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "must_change_password": bool(user.must_change_password),
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "college_id": user.college_id,
            "mfa_enabled": user.mfa_enabled
        }
    }

@router.post("/mfa-verify")
def verify_mfa_challenge(req: AdminMfaVerifyRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    payload = decode_token(req.temp_token)
    if not payload or payload.get("type") != "mfa_challenge":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA challenge expired or invalid. Please sign in again.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="MFA is not configured for this admin account")

    if not verify_totp_code(user.mfa_secret, req.totp_code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA / TOTP code")

    now = datetime.now(timezone.utc)
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "college_id": user.college_id,
        "is_admin": True
    })
    refresh_token = create_refresh_token({"sub": user.id})

    session = UserSession(
        user_id=user.id,
        refresh_token_hash=get_password_hash(refresh_token[:16]),
        ip_address=ip,
        device_info=request.headers.get("User-Agent", "Admin Browser")[:255],
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(session)
    db.commit()

    log_admin_audit(db, user, "ADMIN_MFA_VERIFIED", "AUTH", {"ip": ip}, ip)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "must_change_password": bool(user.must_change_password),
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "college_id": user.college_id,
            "mfa_enabled": True
        }
    }

@router.post("/refresh")
def refresh_admin_token(req: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    rate_limiter.enforce("login", request)

    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.query(User).filter(
        User.id == payload.get("sub"),
        User.is_active == True,
        User.role.in_(["ADMIN", "COLLEGE_ADMIN", "SUPER_ADMIN"]),
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Administrator account is no longer active")

    now = datetime.now(timezone.utc)
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_revoked == False,
        UserSession.expires_at > now,
    ).all()
    valid_session = next(
        (session for session in sessions if verify_password(req.refresh_token[:16], session.refresh_token_hash)),
        None,
    )
    if not valid_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or revoked")

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "college_id": user.college_id,
        "is_admin": True,
    })
    return {"access_token": access_token}

@router.get("/me")
def get_admin_profile(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
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
                "assistant_name": college.assistant_name,
                "primary_color": college.primary_color,
                "secondary_color": college.secondary_color,
                "accent_color": college.accent_color,
                "status": college.status,
                "official_website": college.official_website,
            }
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "college_id": current_user.college_id,
        "must_change_password": bool(current_user.must_change_password),
        "mfa_enabled": current_user.mfa_enabled,
        "permissions": current_user.permissions or [],
        "college": college_info
    }

@router.post("/logout")
def admin_logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    now = datetime.now(timezone.utc)
    db.query(UserSession).filter(
        UserSession.user_id == payload["sub"],
        UserSession.is_revoked == False,
    ).update({"is_revoked": True, "revoked_at": now}, synchronize_session=False)
    db.commit()
    return {"message": "Logged out successfully"}

@router.post("/mfa/setup")
def setup_mfa(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    secret = generate_totp_secret()
    current_user.mfa_secret = secret
    current_user.mfa_enabled = True
    db.commit()

    otpauth_url = f"otpauth://totp/AIT-AI-Assistant:{current_user.email}?secret={secret}&issuer=AIT-Ahmedabad"
    return {
        "secret": secret,
        "otpauth_url": otpauth_url,
        "manual_entry_key": secret,
        "message": "Scan the QR code with Google Authenticator, Authy, or enter the secret manually. Keep this secret safe."
    }

@router.get("/sessions")
def list_admin_sessions(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id, UserSession.is_revoked == False)
        .order_by(UserSession.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": s.id,
            "ip_address": s.ip_address,
            "device_info": s.device_info or "Standard Browser Session",
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "last_activity_at": s.last_activity_at.isoformat() if s.last_activity_at else None
        }
        for s in sessions
    ]

@router.post("/sessions/{session_id}/revoke")
def revoke_admin_session(
    session_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    session = (
        db.query(UserSession)
        .filter(UserSession.id == session_id, UserSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.is_revoked = True
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    log_admin_audit(db, current_user, "REVOKE_SESSION", "USER_SESSION", {"session_id": session_id})
    return {"message": "Session revoked successfully"}

class FirstPasswordChangeRequest(BaseModel):
    email: EmailStr
    temporary_password: str
    new_password: str


@router.post("/change-password")
def change_admin_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    if not current_user.hashed_password or not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")

    current_user.hashed_password = get_password_hash(req.new_password)
    current_user.must_change_password = False
    db.commit()
    log_admin_audit(db, current_user, "CHANGE_PASSWORD", "USER", {})
    return {"message": "Password updated successfully", "must_change_password": False}


@router.post("/change-first-password")
def change_first_password(req: FirstPasswordChangeRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.hashed_password or not verify_password(req.temporary_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current temporary password incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 8 characters")

    user.hashed_password = get_password_hash(req.new_password)
    user.must_change_password = False
    db.commit()

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "college_id": user.college_id,
        "is_admin": True
    })
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "message": "Password changed successfully. You may now access your College Dashboard.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "must_change_password": False,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "college_id": user.college_id,
            "mfa_enabled": user.mfa_enabled,
            "must_change_password": False
        }
    }

# Alias for compatibility
get_current_admin = get_current_admin_user

