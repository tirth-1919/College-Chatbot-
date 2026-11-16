"""User Account SQLAlchemy ORM Model.

Master account table for students, college admins, and super admins.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.membership import CollegeMembership
    from app.models.document import Document
    from app.models.knowledge import KnowledgeReview
    from app.models.chat import ChatSession
    from app.models.feedback_support import Feedback, SupportTicket
    from app.models.audit import AuditLog


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account entity for all platform actors."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        PG_ENUM("STUDENT", "COLLEGE_ADMIN", "SUPER_ADMIN", name="user_role", create_type=False),
        default="STUDENT",
        nullable=False,
        index=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_password_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    preferences: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    memberships: Mapped[List["CollegeMembership"]] = relationship(
        "CollegeMembership", back_populates="user", cascade="all, delete-orphan"
    )
    uploaded_documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="uploader"
    )
    reviews_performed: Mapped[List["KnowledgeReview"]] = relationship(
        "KnowledgeReview", back_populates="reviewer"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user"
    )
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="user"
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user", foreign_keys="SupportTicket.user_id"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor"
    )

