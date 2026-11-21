"""Tenant-owned course catalogue, fee schedules, and college gallery metadata."""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, UUIDPrimaryKeyMixin, utc_now


class AcademicCourse(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "academic_courses"
    __table_args__ = (UniqueConstraint("college_id", "course_name"), UniqueConstraint("id", "college_id"))

    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(80))
    course_abbreviation: Mapped[Optional[str]] = mapped_column(String(80))
    course_category: Mapped[str] = mapped_column(String(100), default="OTHER", nullable=False)
    branch_name: Mapped[Optional[str]] = mapped_column(String(255))
    program_level: Mapped[Optional[str]] = mapped_column(String(80))
    duration: Mapped[Optional[str]] = mapped_column(String(100))
    total_semesters: Mapped[Optional[int]] = mapped_column(Integer)
    eligibility: Mapped[Optional[str]] = mapped_column(Text)
    admission_information: Mapped[Optional[str]] = mapped_column(Text)
    syllabus_information: Mapped[Optional[str]] = mapped_column(Text)
    active_status: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    source_document: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AcademicFee(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "academic_fees"
    __table_args__ = (Index("ix_academic_fees_lookup", "college_id", "course_id", "academic_year", "semester_number"),)

    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("academic_courses.id", ondelete="CASCADE"), nullable=False)
    semester_number: Mapped[Optional[int]] = mapped_column(Integer)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    fee_type: Mapped[str] = mapped_column(String(80), default="SEMESTER", nullable=False)
    academic_year: Mapped[Optional[str]] = mapped_column(String(20))
    effective_from: Mapped[Optional[date]] = mapped_column(Date)
    effective_until: Mapped[Optional[date]] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    source_document: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CollegeGalleryImage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "college_gallery_images"
    __table_args__ = (UniqueConstraint("college_id", "content_hash", name="uq_gallery_college_hash"),)

    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_title: Mapped[str] = mapped_column(String(255), nullable=False)
    image_description: Mapped[Optional[str]] = mapped_column(Text)
    image_category: Mapped[str] = mapped_column(String(100), default="OTHER", nullable=False)
    facility_name: Mapped[Optional[str]] = mapped_column(String(255))
    event_name: Mapped[Optional[str]] = mapped_column(String(255))
    event_date: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_document: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    source_page: Mapped[Optional[int]] = mapped_column(Integer)
    verification_status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AcademicChangeHistory(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "academic_change_history"
    college_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    change_action: Mapped[str] = mapped_column(String(40), nullable=False)
    change_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
