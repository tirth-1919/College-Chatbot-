import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="STUDENT", nullable=False)  # STUDENT, ADMIN, SUPER_ADMIN
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(64), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    permissions = Column(JSON, default=list)  # Granular explicit permission overrides
    oauth_provider = Column(String(50), nullable=True)  # e.g., 'google'
    oauth_id = Column(String(255), nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="SET NULL"), nullable=True, index=True)
    # Persistent user-side college PREFERENCE (Part A §4): the college the user
    # normally asks about. Distinct from User.college_id (tenant/admin linkage).
    default_college_id = Column(String(36), ForeignKey("colleges.id", ondelete="SET NULL"), nullable=True, index=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    college = relationship("College", back_populates="users", foreign_keys=[college_id])
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

class UserSession(Base):
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_hash = Column(String(255), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_info = Column(String(255), nullable=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="sessions")

