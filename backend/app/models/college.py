"""College Tenant SQLAlchemy ORM Model.

Represents an academic institution tenant (e.g. AIT College, RCTI College).
"""

from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.membership import CollegeMembership
    from app.models.website import WebsiteSource, WebsitePage, CrawlJob
    from app.models.document import Document
    from app.models.knowledge import ExtractedFact, KnowledgeChunk
    from app.models.chat import ChatSession
    from app.models.feedback_support import Feedback, SupportTicket
    from app.models.audit import AuditLog


class College(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Root tenant entity representing individual colleges."""

    __tablename__ = "colleges"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    official_domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        PG_ENUM("PENDING", "APPROVED", "SUSPENDED", "REJECTED", name="college_status", create_type=False),
        default="PENDING",
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    memberships: Mapped[List["CollegeMembership"]] = relationship(
        "CollegeMembership", back_populates="college", cascade="all, delete-orphan"
    )
    website_sources: Mapped[List["WebsiteSource"]] = relationship(
        "WebsiteSource", back_populates="college", cascade="all, delete-orphan"
    )
    website_pages: Mapped[List["WebsitePage"]] = relationship(
        "WebsitePage", back_populates="college", cascade="all, delete-orphan"
    )
    crawl_jobs: Mapped[List["CrawlJob"]] = relationship(
        "CrawlJob", back_populates="college", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="college", cascade="all, delete-orphan"
    )
    extracted_facts: Mapped[List["ExtractedFact"]] = relationship(
        "ExtractedFact", back_populates="college", cascade="all, delete-orphan"
    )
    knowledge_chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="college", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="college", cascade="all, delete-orphan"
    )
    feedbacks: Mapped[List["Feedback"]] = relationship(
        "Feedback", back_populates="college", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[List["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="college", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="college"
    )

