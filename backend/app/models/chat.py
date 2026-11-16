"""Chat Conversation SQLAlchemy ORM Models.

Entities for managing student chat sessions and conversational message logs.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User
    from app.models.feedback_support import Feedback


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Conversational thread scoped to an academic institution."""

    __tablename__ = "chat_sessions"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visitor_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_title: Mapped[str] = mapped_column(String(255), default="New Conversation", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="chat_sessions")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base, UUIDPrimaryKeyMixin):
    """Turn-by-turn user prompts, AI answers, verification flags, and citations."""

    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    answer_source_type: Mapped[str] = mapped_column(
        PG_ENUM(
            "OFFICIAL_WEBSITE", "ADMIN_VERIFIED", "GEMINI_UNVERIFIED",
            "SECONDARY_AI_FALLBACK", "NO_RELIABLE_INFORMATION",
            "AI_GUIDANCE", "OPENAI_UNVERIFIED", "XKIRO_UNVERIFIED",
            name="answer_source_type", create_type=False
        ),
        default="NO_RELIABLE_INFORMATION",
        nullable=False,
    )
    source_citations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    # Failover metadata fields — added by migration 002_ai_failover_columns.sql.
    # All are nullable/defaulted so existing rows loaded before migration cause no AttributeError.
    answer_mode: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    actual_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actual_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    request_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="message", cascade="all, delete-orphan"
    )

