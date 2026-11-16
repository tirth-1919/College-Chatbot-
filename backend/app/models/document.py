"""PDF Document Ingestion & OCR SQLAlchemy ORM Models.

Entities for managing original uploaded files, deconstructed pages, and paragraphs.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User


class Document(Base, UUIDPrimaryKeyMixin):
    """Metadata for college PDF documents uploaded into private Supabase Storage."""

    __tablename__ = "documents"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processing_status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PROCESSING", "PENDING_REVIEW", "COMPLETED", "FAILED", "UPLOADED",
            "VALIDATING", "QUEUED", "OCR_PROCESSING", "EXTRACTED", "REPROCESSING", "DELETED",
            name="document_status", create_type=False
        ),
        default="PROCESSING",
        nullable=False,
        index=True
    )
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="GENERAL", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), default="PYMUPDF", nullable=False)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="documents")
    uploader: Mapped[Optional["User"]] = relationship("User", back_populates="uploaded_documents")
    pages: Mapped[List["DocumentPage"]] = relationship(
        "DocumentPage", back_populates="document", cascade="all, delete-orphan"
    )
    paragraphs: Mapped[List["DocumentParagraph"]] = relationship(
        "DocumentParagraph", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentPage(Base, UUIDPrimaryKeyMixin):
    """Extracted text and OCR telemetry for an individual document page."""

    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_page"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    college_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), default="PYMUPDF", nullable=False)
    tables_markdown: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    has_tables: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="pages")
    paragraphs: Mapped[List["DocumentParagraph"]] = relationship(
        "DocumentParagraph", back_populates="page", cascade="all, delete-orphan"
    )


class DocumentParagraph(Base, UUIDPrimaryKeyMixin):
    """Individual paragraphs and visual bounding coordinates inside a page."""

    __tablename__ = "document_paragraphs"

    page_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paragraph_index: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_text: Mapped[str] = mapped_column(Text, nullable=False)
    bounding_box: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    page: Mapped["DocumentPage"] = relationship("DocumentPage", back_populates="paragraphs")
    document: Mapped["Document"] = relationship("Document", back_populates="paragraphs")

