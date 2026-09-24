import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class College(Base):
    __tablename__ = "colleges"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)  # e.g., 'AIT', 'ABC'
    slug = Column(String(100), unique=True, index=True, nullable=False)  # e.g., 'ait', 'abc'
    official_email = Column(String(255), nullable=True)
    official_website = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    university_affiliation = Column(String(255), nullable=True)
    contact_person = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    logo_url = Column(String(500), nullable=True)
    auth_document_path = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    additional_info = Column(Text, nullable=True)

    status = Column(String(30), default="PENDING", nullable=False, index=True)  # PENDING, UNDER_REVIEW, ACTIVE, SUSPENDED, REJECTED, NEED_MORE_INFORMATION
    registration_status = Column(String(30), default="PENDING", nullable=False)
    application_id = Column(String(50), unique=True, index=True, nullable=True, default=lambda: f"COL-2026-{str(uuid.uuid4())[:6].upper()}")
    rejection_reason = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    timezone = Column(String(50), default="Asia/Kolkata")

    # Branding
    assistant_name = Column(String(100), default="AI Assistant")
    welcome_message = Column(Text, nullable=True)
    primary_color = Column(String(20), default="#0b0a3e")
    secondary_color = Column(String(20), default="#1a2345")
    accent_color = Column(String(20), default="#f08518")
    supported_languages = Column(JSON, default=lambda: ["en", "gu", "hi"])

    # Limits
    max_users = Column(Integer, default=1000)
    max_storage_mb = Column(Integer, default=5120)
    max_documents = Column(Integer, default=500)
    max_ai_requests_per_day = Column(Integer, default=10000)

    # Subdomain preparation
    subdomain = Column(String(100), unique=True, index=True, nullable=True)
    custom_domain = Column(String(255), unique=True, index=True, nullable=True)

    # Connection Health & Verification (Production Multi-College Requirements)
    # These fields track whether a college has usable verified knowledge infrastructure
    connection_status = Column(String(30), default="NOT_CONNECTED", index=True)  # CONNECTED_VERIFIED, CONNECTED_PARTIAL, REGISTERED_PENDING_SETUP, NOT_CONNECTED
    website_last_checked_at = Column(DateTime, nullable=True)
    website_last_success_at = Column(DateTime, nullable=True)
    website_last_failure_at = Column(DateTime, nullable=True)
    website_http_status = Column(Integer, nullable=True)
    website_pages_indexed = Column(Integer, default=0)
    website_error_message = Column(Text, nullable=True)
    knowledge_last_updated_at = Column(DateTime, nullable=True)
    verified_records_count = Column(Integer, default=0)
    rag_documents_count = Column(Integer, default=0)
    broken_sources_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)

    # Relationships
    users = relationship("User", back_populates="college", foreign_keys="User.college_id")
    aliases = relationship("CollegeAlias", back_populates="college", cascade="all, delete-orphan")
    change_requests = relationship("ChangeRequest", back_populates="college", cascade="all, delete-orphan")
    sync_histories = relationship("WebsiteSyncHistory", back_populates="college", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "slug": self.slug,
            "official_email": self.official_email,
            "official_website": self.official_website,
            "phone": self.phone,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "university_affiliation": self.university_affiliation,
            "contact_person": self.contact_person,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "logo_url": self.logo_url,
            "status": self.status,
            "registration_status": self.registration_status,
            "application_id": self.application_id,
            "rejection_reason": self.rejection_reason,
            "review_notes": self.review_notes,
            "timezone": self.timezone,
            "branding": {
                "assistant_name": self.assistant_name or "AI Assistant",
                "welcome_message": self.welcome_message,
                "primary_color": self.primary_color or "#0b0a3e",
                "secondary_color": self.secondary_color or "#1a2345",
                "accent_color": self.accent_color or "#f08518",
                "supported_languages": self.supported_languages or ["en", "gu", "hi"],
            },
            "limits": {
                "max_users": self.max_users,
                "max_storage_mb": self.max_storage_mb,
                "max_documents": self.max_documents,
                "max_ai_requests_per_day": self.max_ai_requests_per_day,
            },
            "subdomain": self.subdomain,
            "custom_domain": self.custom_domain,
            "connection_health": {
                "connection_status": self.connection_status,
                "website_last_checked_at": self.website_last_checked_at.isoformat() if self.website_last_checked_at else None,
                "website_last_success_at": self.website_last_success_at.isoformat() if self.website_last_success_at else None,
                "website_last_failure_at": self.website_last_failure_at.isoformat() if self.website_last_failure_at else None,
                "website_http_status": self.website_http_status,
                "website_pages_indexed": self.website_pages_indexed,
                "website_error_message": self.website_error_message,
                "knowledge_last_updated_at": self.knowledge_last_updated_at.isoformat() if self.knowledge_last_updated_at else None,
                "verified_records_count": self.verified_records_count,
                "rag_documents_count": self.rag_documents_count,
                "broken_sources_count": self.broken_sources_count,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class CollegeAlias(Base):
    """Database-backed alias resolution (Part A §11): many user-written forms
    ('RC Technical', 'R.C. Technical', 'RCT', ...) resolve to one College."""
    __tablename__ = "college_aliases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    alias = Column(String(255), nullable=False)
    normalized_alias = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    college = relationship("College", back_populates="aliases", foreign_keys=[college_id])


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type = Column(String(100), nullable=False)  # FEES, FACULTY, COURSES, CATEGORY, RECORD, WEBSITE, SETTING
    entity_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE
    title = Column(String(255), nullable=True)  # human-readable summary e.g. "Update BCA Fee"
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(String(30), default="PENDING", nullable=False, index=True)  # PENDING, APPROVED, APPLIED, REJECTED, NEEDS_CLARIFICATION, CANCELLED, FAILED
    clarification_response = Column(Text, nullable=True)  # college admin response to NEEDS_CLARIFICATION
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    college = relationship("College", back_populates="change_requests")

    def to_dict(self):
        return {
            "id": self.id,
            "college_id": self.college_id,
            "college_name": self.college.name if self.college else None,
            "requested_by": self.requested_by,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "title": self.title,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "reason": self.reason,
            "status": self.status,
            "clarification_response": self.clarification_response,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="INFO")  # INFO, WARNING, SUCCESS, ERROR
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class WebsiteSyncHistory(Base):
    __tablename__ = "website_sync_histories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    pages_discovered = Column(Integer, default=0)
    pages_changed = Column(Integer, default=0)
    pages_added = Column(Integer, default=0)
    pages_removed = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)
    error_details = Column(JSON, default=list)
    status = Column(String(30), default="COMPLETED", nullable=False)  # RUNNING, COMPLETED, FAILED

    college = relationship("College", back_populates="sync_histories")


class StagedUploadRecord(Base):
    __tablename__ = "staged_upload_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, default=0)
    detected_category = Column(String(100), default="General", index=True)
    academic_year = Column(String(50), nullable=True)
    course_department = Column(String(100), nullable=True)
    extracted_data = Column(JSON, default=dict)
    raw_snippet = Column(Text, nullable=True)
    confidence_score = Column(Integer, default=90)
    status = Column(String(30), default="PENDING_REVIEW", index=True)  # PENDING_REVIEW, APPROVED, REJECTED
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    college = relationship("College", foreign_keys=[college_id])

    def to_dict(self):
        return {
            "id": self.id,
            "college_id": self.college_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "detected_category": self.detected_category,
            "academic_year": self.academic_year,
            "course_department": self.course_department,
            "extracted_data": self.extracted_data or {},
            "raw_snippet": self.raw_snippet,
            "confidence_score": self.confidence_score,
            "status": self.status,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
