"""College Tenant SQLAlchemy ORM Model.

Represents an academic institution tenant (e.g. AIT College, RCTI College).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB
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

    # 1. Institutional Identity & Classification
    short_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cover_image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    institution_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    established_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 2. Address & Geolocation
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    maps_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 3. Official & Departmental Contacts
    admission_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    examination_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    placement_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    admission_helpline: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    alternate_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    working_hours: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)

    # 4. Recognition & Accreditation
    affiliated_university: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recognized_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    aicte_approval: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ugc_recognition: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    naac_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nba_accreditation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    accreditation_validity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approval_document_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 5. About Institution & Leadership
    short_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    about_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    mission: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    leader_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    leader_designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 6. Social Media
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    instagram_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    facebook_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    youtube_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    twitter_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 7. Branding & Theming
    favicon_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_brand_color: Mapped[Optional[str]] = mapped_column(String(20), default="#10B981", nullable=True)
    secondary_brand_color: Mapped[Optional[str]] = mapped_column(String(20), default="#6366F1", nullable=True)

    # 8. Draft Profile State
    draft_profile: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

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

