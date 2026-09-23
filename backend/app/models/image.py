import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AitImage(Base):
    __tablename__ = "ait_images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)  # campus, building, classroom, lab, computer_lab, library, sports, canteen, event, faculty, logo
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    source_url = Column(String(500), nullable=False)
    source_page = Column(String(255), nullable=True)
    source_type = Column(String(50), default="official_website")
    source_domain = Column(String(100), default="aitindia.in")
    official_source = Column(Boolean, default=True)
    verified = Column(Boolean, default=True)
    verification_status = Column(String(50), default="PUBLISHED")  # DISCOVERED, DOWNLOADED, HASHED, VERIFIED, PUBLISHED, STALE, ARCHIVED
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    width = Column(Integer, default=800)
    height = Column(Integer, default=600)
    license_basis = Column(String(100), default="Official Institutional Asset")
    retrieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_verified_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    provenance = relationship("ImageProvenance", back_populates="image", uselist=False, cascade="all, delete-orphan")

class ImageProvenance(Base):
    __tablename__ = "image_provenance"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    image_id = Column(String(36), ForeignKey("ait_images.id", ondelete="CASCADE"), nullable=False, index=True)
    source_url = Column(String(500), nullable=False)
    source_domain = Column(String(100), nullable=False)
    extracted_page = Column(String(255), nullable=True)
    alt_text = Column(String(255), nullable=True)
    discovered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    verified_by = Column(String(100), default="AIT Image Ingestion Pipeline")
    verification_method = Column(String(100), default="Official Domain Whitelist & Bundle Inspection")

    image = relationship("AitImage", back_populates="provenance")
