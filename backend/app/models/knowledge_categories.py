"""
Dynamic Knowledge Database: Categories and Records.

Extends (does not replace) the existing AitEntity knowledge system.
Every record that becomes Active+verified is mirrored into ait_entities
by the admin API layer so the existing chatbot retrieval
(KnowledgeDatabase.query_entities / source hierarchy) keeps working
unchanged, with correct source attribution (never labelled as official
website data unless it truly is).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(120), nullable=False, unique=True, index=True)
    key = Column(String(80), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # emoji or icon name
    display_order = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)  # ACTIVE | INACTIVE
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    records = relationship("KnowledgeRecord", back_populates="category", cascade="all, delete-orphan")


class KnowledgeRecord(Base):
    __tablename__ = "knowledge_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    category_id = Column(String(36), ForeignKey("knowledge_categories.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # course linkage kept nullable; resolved course code stored in academic fields
    course = Column(String(120), nullable=True, index=True)  # human-readable course, e.g. 'BCA'
    academic_year = Column(String(20), nullable=True, index=True)  # e.g. '2026-27'

    title = Column(String(255), nullable=False, index=True)
    field_name = Column(String(120), nullable=True)   # optional field label, e.g. 'Tuition Fee'
    value = Column(Text, nullable=True)               # primary value / summary
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, default=dict)  # category-specific structured fields

    # Source & verification metadata (compatible with existing hierarchy)
    source_type = Column(String(40), default="ADMIN_VERIFIED", nullable=False)  # AIT_OFFICIAL | GTU_OFFICIAL | ADMIN_VERIFIED | OTHER_VERIFIED
    source_url = Column(String(500), nullable=True)
    source_title = Column(String(255), nullable=True)
    verified = Column(Boolean, default=False, index=True)
    verified_by = Column(String(36), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)

    status = Column(String(20), default="DRAFT", nullable=False, index=True)  # DRAFT | ACTIVE | INACTIVE | ARCHIVED
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    category = relationship("KnowledgeCategory", back_populates="records")

    def to_dict(self):
        return {
            "id": self.id,
            "college_id": self.college_id,
            "category_id": self.category_id,
            "course": self.course,
            "academic_year": self.academic_year,
            "title": self.title,
            "field_name": self.field_name,
            "value": self.value,
            "description": self.description,
            "metadata": self.metadata_json or {},
            "source_type": self.source_type,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "verified": self.verified,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
