import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from backend.app.core.database import Base
try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # SQLite/dev environments keep the existing JSON fallback.
    class Vector(TypeDecorator):
        impl = JSON
        cache_ok = True
        def __init__(self, dimensions=None, **kwargs):
            super().__init__(**kwargs)
            self.dimensions = dimensions

def generate_uuid():
    return str(uuid.uuid4())

# Document visibility states (P0-3: replaces dangerous NULL=public pattern)
# PRIVATE_USER: belongs to a specific authenticated user only
# ADMIN_PENDING: uploaded by admin, awaiting review/publish
# ADMIN_VERIFIED: reviewed and published by admin, enters institutional RAG
# PUBLIC_INSTITUTIONAL: explicit public institutional content (website snapshots)
VISIBILITY_PRIVATE_USER = "PRIVATE_USER"
VISIBILITY_ADMIN_PENDING = "ADMIN_PENDING"
VISIBILITY_ADMIN_VERIFIED = "ADMIN_VERIFIED"
VISIBILITY_PUBLIC_INSTITUTIONAL = "PUBLIC_INSTITUTIONAL"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    # user_id: owner of this document. For institutional docs (visibility=ADMIN_VERIFIED),
    # this is the admin who uploaded it. The old NULL=public pattern is removed.
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    doc_type = Column(String(50), nullable=False)  # pdf, docx, txt, institutional_page
    source_url = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=False)
    # visibility controls RAG access:
    # PRIVATE_USER     -> only the owning user can access in RAG
    # ADMIN_PENDING    -> uploaded by admin, not yet in institutional RAG
    # ADMIN_VERIFIED   -> in institutional RAG, retrieved for all users
    # PUBLIC_INSTITUTIONAL -> website snapshots, always publicly retrievable
    visibility = Column(String(30), nullable=False, default=VISIBILITY_PRIVATE_USER, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="documents")
    __table_args__ = (
        UniqueConstraint("college_id", "content_hash", "visibility", name="uq_documents_college_hash_visibility"),
    )

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # Kept as a compatibility/backfill source for SQLite and existing rows.
    embedding_json = Column(Text, nullable=True)
    # Production PostgreSQL retrieval uses this native pgvector column.
    embedding_vector = Column(Vector(64), nullable=True)
    metadata_ = Column(JSON, default=dict)
    embedding_model = Column(String(120), nullable=True, index=True)
    embedding_version = Column(String(50), nullable=True)
    indexed_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )

    document = relationship("Document", back_populates="chunks")
