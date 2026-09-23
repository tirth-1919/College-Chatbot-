import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AitEntity(Base):
    __tablename__ = "ait_entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(50), nullable=False, index=True)  # program, department, faculty, facility, fee, event, contact, calendar
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)  # e.g., 'BCA', 'DBMS', 'CE'
    details = Column(JSON, default=dict)  # structured metadata
    academic_year = Column(String(20), nullable=True, index=True)  # e.g., '2026-27', '2025-26'
    source_url = Column(String(500), nullable=False)
    source_page = Column(String(255), nullable=True)
    # Provenance type: OFFICIAL_WEBSITE | COLLEGE_UPLOAD | DEMO | OTHER
    source_type = Column(String(50), nullable=True, index=True)
    is_official = Column(Boolean, nullable=True)
    authority = Column(String(100), default="Official College Website")
    is_verified = Column(Boolean, default=True)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship("AitKnowledgeVersion", back_populates="entity", cascade="all, delete-orphan")

class AitKnowledgeVersion(Base):
    __tablename__ = "ait_knowledge_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_id = Column(String(36), ForeignKey("ait_entities.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(50), default="PUBLISHED")  # DISCOVERED, EXTRACTED, PENDING_REVIEW, VERIFIED, PUBLISHED, SUPERSEDED, ARCHIVED
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    entity = relationship("AitEntity", back_populates="versions")

class WebsiteSnapshot(Base):
    __tablename__ = "website_snapshots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    url = Column(String(500), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=False)
    text_content = Column(Text, nullable=False)
    status_code = Column(Integer, default=200)
    last_crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    user_query = Column(Text, nullable=False)
    detected_intent = Column(String(100), nullable=True)
    missing_entity = Column(String(100), nullable=True)
    occurred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved = Column(Boolean, default=False)

    # ── Knowledge Gap Center (normalized dedup + review workflow) ──
    # Normalized dedup key (lowercase, punctuation/whitespace-normalized query).
    # Unique grouping is enforced at the service layer per (college_id, dedup_key)
    # so identical questions increment occurrence_count instead of new rows.
    dedup_key = Column(String(255), nullable=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(30), default="OPEN", nullable=False, index=True)
    # OPEN, UNDER_REVIEW, IN_PROGRESS, RESOLVED, DISMISSED, DUPLICATE
    occurrence_count = Column(Integer, default=1, nullable=False)
    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sample_answer = Column(Text, nullable=True)
    reason = Column(String(50), nullable=True)  # e.g. no_verified_source, low_confidence, user_reported
    category = Column(String(50), nullable=True, index=True)  # Admissions, Fees, Hostel... (admin editable)
    course = Column(String(100), nullable=True, index=True)
    academic_year = Column(String(20), nullable=True, index=True)
    priority = Column(String(20), default="Medium", nullable=True, index=True)  # High/Medium/Low (explainable)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(36), nullable=True)


class MessageFeedback(Base):
    """User feedback / wrong-answer reports on assistant messages.

    One row per (message_id, user_id) — repeated clicks UPDATE the existing
    record instead of creating duplicates. college_id is always derived
    server-side from the conversation, never trusted from the client.
    """
    __tablename__ = "message_feedback"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # POSITIVE | NEGATIVE | REPORT
    feedback_type = Column(String(20), nullable=False, index=True)
    # For NEGATIVE: incorrect|outdated|wrong_college|missing_details|not_relevant|could_not_answer|other
    # For REPORT: incorrect|outdated|wrong_college|missing_source|contradicts_official|other
    reason = Column(String(50), nullable=True, index=True)
    details = Column(Text, nullable=True)  # free-text description (no secrets)
    status = Column(String(30), default="UNRESOLVED", nullable=False, index=True)
    # UNRESOLVED, RESOLVED, DISMISSED
    source_type = Column(String(100), nullable=True)
    source_url = Column(String(500), nullable=True)
    knowledge_record_id = Column(String(36), nullable=True)
    grounding_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
