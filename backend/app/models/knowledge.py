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
    category = Column(String(50), nullable=False, index=True)  # program, department, faculty, facility, fee, event, contact, calendar
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)  # e.g., 'BCA', 'DBMS', 'CE'
    details = Column(JSON, default=dict)  # structured metadata
    source_url = Column(String(500), nullable=False)
    source_page = Column(String(255), nullable=True)
    authority = Column(String(100), default="Official AIT Website")
    is_verified = Column(Boolean, default=True)
    content_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    versions = relationship("AitKnowledgeVersion", back_populates="entity", cascade="all, delete-orphan")

class AitKnowledgeVersion(Base):
    __tablename__ = "ait_knowledge_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
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
    user_query = Column(Text, nullable=False)
    detected_intent = Column(String(100), nullable=True)
    missing_entity = Column(String(100), nullable=True)
    occurred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved = Column(Boolean, default=False)
