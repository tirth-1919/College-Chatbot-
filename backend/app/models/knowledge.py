"""Knowledge Base & Human Review SQLAlchemy ORM Models.

Entities for atomic facts, vector knowledge chunks (pgvector), and review audit logs.
"""

import importlib
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID, ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now
from app.core.config import settings

# Load pgvector.sqlalchemy.Vector dynamically to avoid static missing-import warnings
Vector = None
try:
    _pgvector_sa = importlib.import_module("pgvector.sqlalchemy")
    Vector = getattr(_pgvector_sa, "Vector", None)
except Exception:
    Vector = None

if Vector is None:
    from sqlalchemy.types import UserDefinedType

    class Vector(UserDefinedType):  # type: ignore
        def __init__(self, dim: int):
            self.dim = dim

        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

if TYPE_CHECKING:
    from app.models.college import College
    from app.models.user import User


class ExtractedFact(Base, UUIDPrimaryKeyMixin):
    """Atomic factual claims extracted from documents or web pages."""

    __tablename__ = "extracted_facts"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    fact_key: Mapped[str] = mapped_column(String(255), nullable=False)
    fact_value: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="extracted_facts")


class KnowledgeChunk(Base, UUIDPrimaryKeyMixin):
    """Semantic vector search chunk storing text and pgvector embeddings."""

    __tablename__ = "knowledge_chunks"

    college_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(String(100), default="OTHER", nullable=False, index=True)
    heading: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    embedding: Mapped[Optional[list]] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    status: Mapped[str] = mapped_column(
        PG_ENUM(
            "PROCESSING", "PENDING_REVIEW", "APPROVED", "PUBLISHED",
            "REJECTED", "STALE", "SUPERSEDED", "FAILED",
            name="knowledge_status", create_type=False
        ),
        default="PENDING_REVIEW",
        nullable=False,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    college: Mapped["College"] = relationship("College", back_populates="knowledge_chunks")
    reviews: Mapped[List["KnowledgeReview"]] = relationship(
        "KnowledgeReview", back_populates="chunk", cascade="all, delete-orphan"
    )


class KnowledgeReview(Base, UUIDPrimaryKeyMixin):
    """Audit record of human-in-the-loop review actions on knowledge chunks."""

    __tablename__ = "knowledge_reviews"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    review_action: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_chunk_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    chunk: Mapped["KnowledgeChunk"] = relationship("KnowledgeChunk", back_populates="reviews")
    reviewer: Mapped[Optional["User"]] = relationship("User", back_populates="reviews_performed")

