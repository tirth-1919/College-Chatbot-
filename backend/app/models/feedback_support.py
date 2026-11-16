"""Student Feedback & Escalated Support Tickets SQLAlchemy ORM Models.

Entities for capturing message ratings, support tickets, and threaded resolution replies.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User
    from app.models.chat import ChatMessage, ChatSession


class Feedback(Base, UUIDPrimaryKeyMixin):
    """Student feedback and rating on individual assistant answers."""

    __tablename__ = "feedback"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (helpful) or -1 (unhelpful)
    category: Mapped[str] = mapped_column(
        String(50), default="ACCURACY", nullable=False
    )  # ACCURACY, MISSING_INFO, INCORRECT_INFO, TECHNICAL_ISSUE, GENERAL
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="feedbacks")
    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="feedbacks")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="feedbacks")


class SupportTicket(Base, UUIDPrimaryKeyMixin):
    """Inquiries escalated directly to the college administration or super admins."""

    __tablename__ = "support_tickets"

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
    student_name: Mapped[str] = mapped_column(String(255), nullable=False)
    student_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="OTHER", nullable=False, index=True
    )  # LOGIN, CHATBOT, INCORRECT_ANSWER, MISSING_INFO, DOCUMENT, TECHNICAL, OTHER
    priority: Mapped[str] = mapped_column(
        String(20), default="MEDIUM", nullable=False
    )  # LOW, MEDIUM, HIGH, URGENT
    status: Mapped[str] = mapped_column(
        PG_ENUM("OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "WAITING_FOR_USER", name="support_ticket_status", create_type=False),
        default="OPEN",
        nullable=False,
        index=True
    )
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="support_tickets")
    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="support_tickets", foreign_keys=[user_id]
    )
    assigned_staff: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    replies: Mapped[List["SupportTicketReply"]] = relationship(
        "SupportTicketReply", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketReply.created_at"
    )


class SupportTicketReply(Base, UUIDPrimaryKeyMixin):
    """Threaded conversation message in a support ticket."""

    __tablename__ = "support_ticket_replies"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sender_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_role: Mapped[str] = mapped_column(String(50), nullable=False)  # STUDENT, COLLEGE_ADMIN, SUPER_ADMIN
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="replies")
    sender: Mapped[Optional["User"]] = relationship("User")
