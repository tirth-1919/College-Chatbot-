import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from backend.app.core.database import Base

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    class Vector(TypeDecorator):
        impl = JSON
        cache_ok = True
        def __init__(self, dimensions=None, **kwargs):
            super().__init__(**kwargs)
            self.dimensions = dimensions

def generate_uuid():
    return str(uuid.uuid4())

# Status constants conforming to requirements
LEARNING_STATUS_PENDING_REVIEW = "PENDING_REVIEW"
LEARNING_STATUS_APPROVED = "APPROVED"
LEARNING_STATUS_REJECTED = "REJECTED"
LEARNING_STATUS_MERGED = "MERGED"
LEARNING_STATUS_DUPLICATE = "DUPLICATE"

VALID_LEARNING_STATUSES = {
    LEARNING_STATUS_PENDING_REVIEW,
    LEARNING_STATUS_APPROVED,
    LEARNING_STATUS_REJECTED,
    LEARNING_STATUS_MERGED,
    LEARNING_STATUS_DUPLICATE,
}

class LearningCandidate(Base):
    __tablename__ = "learning_candidates"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    # Every LearningCandidate MUST belong to exactly one college
    college_id = Column(String(36), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)

    # Question details
    question = Column(Text, nullable=False)
    normalized_question = Column(Text, nullable=False, index=True)
    detected_intent = Column(String(100), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)

    # Generated answer & provenance
    generated_answer = Column(Text, nullable=True)
    answer_source = Column(String(50), nullable=True, index=True)  # GEMINI_UNVERIFIED, OFFICIAL_WEBSITE, ADMIN_VERIFIED
    verification_status = Column(String(50), default="UNVERIFIED", nullable=False)

    # Status & occurrence tracking
    status = Column(String(30), default=LEARNING_STATUS_PENDING_REVIEW, nullable=False, index=True)
    occurrence_count = Column(Integer, default=1, nullable=False)
    variations = Column(JSON, default=list)
    first_asked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_asked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Embedding / Vector (compatible with pgvector & SQLite dev fallback)
    embedding_json = Column(Text, nullable=True)
    embedding_vector = Column(Vector(64), nullable=True)

    # Context & metadata
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_json = Column("metadata", JSON, default=dict)

    # Feedback aggregation
    positive_feedback_count = Column(Integer, default=0, nullable=False)
    negative_feedback_count = Column(Integer, default=0, nullable=False)

    # Admin review workflow
    reviewed_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    change_request_id = Column(String(36), ForeignKey("change_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    similar_candidate_id = Column(String(36), ForeignKey("learning_candidates.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    college = relationship("College", back_populates="learning_candidates")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    change_request = relationship("ChangeRequest", foreign_keys=[change_request_id])

    def to_dict(self):
        return {
            "id": self.id,
            "college_id": self.college_id,
            "college_name": self.college.name if self.college else None,
            "question": self.question,
            "normalized_question": self.normalized_question,
            "detected_intent": self.detected_intent,
            "category": self.category,
            "generated_answer": self.generated_answer,
            "answer_source": self.answer_source,
            "verification_status": self.verification_status,
            "status": self.status,
            "occurrence_count": self.occurrence_count,
            "variations": self.variations or [],
            "first_asked_at": self.first_asked_at.isoformat() if self.first_asked_at else None,
            "last_asked_at": self.last_asked_at.isoformat() if self.last_asked_at else None,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata_json or {},
            "positive_feedback_count": self.positive_feedback_count,
            "negative_feedback_count": self.negative_feedback_count,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "rejection_reason": self.rejection_reason,
            "change_request_id": self.change_request_id,
            "similar_candidate_id": self.similar_candidate_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
