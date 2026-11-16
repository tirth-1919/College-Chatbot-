"""College Administrator Schemas for Institutional Knowledge, Crawling & Review.

Strictly multi-tenant schemas for college admin workspace operations.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# 1. College Profile
# ==============================================================================

class CollegeProfileResponse(BaseModel):
    """Institutional profile information accessible to College Admin."""

    id: uuid.UUID
    name: str
    slug: str
    official_domain: str
    contact_email: str
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None
    status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeProfileUpdateRequest(BaseModel):
    """Permitted fields for institutional profile updates by College Admin."""

    name: Optional[str] = None
    official_domain: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None


# ==============================================================================
# 2. Website Sources & Crawler
# ==============================================================================

class WebsiteSourceCreateRequest(BaseModel):
    """Payload to register an official college website source for crawling."""

    base_url: str = Field(description="Must belong to verified institutional domain")
    allowed_subdomains: Optional[str] = None
    max_depth: int = Field(default=2, ge=1, le=5)
    max_pages: int = Field(default=50, ge=5, le=500)
    crawl_frequency: str = Field(default="WEEKLY")


class WebsiteSourceUpdateRequest(BaseModel):
    """Payload to update website source crawling parameters."""

    allowed_subdomains: Optional[str] = None
    max_depth: Optional[int] = Field(default=None, ge=1, le=5)
    max_pages: Optional[int] = Field(default=None, ge=5, le=500)
    crawl_frequency: Optional[str] = None
    is_active: Optional[bool] = None


class WebsiteSourceResponse(BaseModel):
    """Website source entity serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    base_url: str
    allowed_subdomains: Optional[str] = None
    max_depth: int
    max_pages: int
    crawl_frequency: str
    is_active: bool
    last_crawled_at: Optional[datetime] = None
    pages_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlJobResponse(BaseModel):
    """Asynchronous website crawl job serialization."""

    id: uuid.UUID
    source_id: uuid.UUID
    college_id: uuid.UUID
    base_url: Optional[str] = None
    status: str  # PENDING, RUNNING, COMPLETED, FAILED, PAUSED
    pages_discovered: int
    pages_crawled: int
    pages_failed: int
    failure_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlEventResponse(BaseModel):
    """Log entry emitted during crawler execution."""

    id: uuid.UUID
    crawl_job_id: uuid.UUID
    log_level: str
    message: str
    metadata_: Dict[str, Any] = Field(default_factory=dict, alias="metadata")
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _extract_orm_metadata(cls, data: Any) -> Any:
        """Resolve the SQLAlchemy metadata_ column value from ORM instances.

        SQLAlchemy's DeclarativeBase places a class-level ``metadata`` attribute
        (a ``sqlalchemy.sql.schema.MetaData`` object) on every mapped class.
        When Pydantic reads from an ORM object with ``from_attributes=True`` and
        this field has ``alias='metadata'``, it resolves ``obj.metadata`` to that
        internal object instead of the mapped JSONB column, producing a
        ``ValidationError`` that surfaces as HTTP 500.

        This validator runs before field-level coercion: it extracts the correct
        value from ``obj.metadata_`` (the mapped Python attribute) and returns a
        plain dict so the alias lookup never touches SQLAlchemy internals.
        """
        if not isinstance(data, dict) and hasattr(data, "metadata_"):
            meta_val = getattr(data, "metadata_", {})
            if not isinstance(meta_val, dict):
                meta_val = {}
            return {
                "id": getattr(data, "id", None),
                "crawl_job_id": getattr(data, "crawl_job_id", None),
                "log_level": getattr(data, "log_level", "INFO"),
                "message": getattr(data, "message", ""),
                "metadata": meta_val,
                "created_at": getattr(data, "created_at", None),
            }
        return data

    class Config:
        from_attributes = True
        populate_by_name = True


class WebsitePageResponse(BaseModel):
    """Extracted text page serialization."""

    id: uuid.UUID
    source_id: uuid.UUID
    college_id: uuid.UUID
    crawl_job_id: Optional[uuid.UUID] = None
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    content_hash: str
    cleaned_text: str
    content_length: Optional[int] = 0
    http_status: int
    fetched_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# 3. Document Management
# ==============================================================================

class DocumentCreateRequest(BaseModel):
    """Metadata payload for document upload."""

    original_filename: str
    file_size_bytes: int
    mime_type: str = "application/pdf"
    category: Optional[str] = "GENERAL"
    description: Optional[str] = None


class DocumentDetailResponse(BaseModel):
    """Document metadata serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    original_filename: str
    storage_path: str
    file_size_bytes: int
    total_pages: int
    checksum_sha256: str
    processing_status: str
    mime_type: str
    title: Optional[str] = None
    category: Optional[str] = "GENERAL"
    description: Optional[str] = None
    failure_reason: Optional[str] = None
    extraction_method: Optional[str] = "PYMUPDF"
    ocr_applied: Optional[bool] = False
    download_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentPageResponse(BaseModel):
    """Extracted text and OCR data for an individual PDF page."""

    id: uuid.UUID
    document_id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    page_number: int
    extracted_text: str
    is_scanned: bool
    ocr_applied: bool
    ocr_confidence: Optional[float] = None
    extraction_method: str = "PYMUPDF"
    tables_markdown: List[str] = []
    has_tables: bool = False
    word_count: int = 0
    char_count: int = 0
    processed_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    """Real-time processing status and telemetry."""

    id: uuid.UUID
    college_id: uuid.UUID
    processing_status: str
    total_pages: int
    pages_extracted: int
    ocr_applied: bool
    failure_reason: Optional[str] = None
    updated_at: datetime


class DocumentSignedUrlResponse(BaseModel):
    """Signed temporary download/viewing URL for private PDF."""

    document_id: uuid.UUID
    original_filename: str
    download_url: str
    expires_in_seconds: int = 3600


# ==============================================================================
# 4. Knowledge Base & Human-in-the-Loop Review
# ==============================================================================

class KnowledgeChunkResponse(BaseModel):
    """Semantic knowledge chunk serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    source_type: str  # WEBSITE, DOCUMENT, ADMIN_STRUCTURED, FAQ
    source_id: uuid.UUID
    source_url: Optional[str] = None
    page_number: Optional[int] = None
    category: str = "OTHER"
    heading: Optional[str] = None
    content_hash: Optional[str] = None
    chunk_text: str
    chunk_metadata: Dict[str, Any] = {}
    status: str  # PENDING_REVIEW, APPROVED, PUBLISHED, REJECTED, STALE, SUPERSEDED, FAILED
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class KnowledgeReviewDecisionRequest(BaseModel):
    """College Admin decision on a pending knowledge chunk."""

    decision: str = Field(description="APPROVE or REJECT")
    comments: Optional[str] = None


class BulkKnowledgeReviewRequest(BaseModel):
    """Bulk approval or rejection of pending knowledge chunks."""

    chunk_ids: List[uuid.UUID] = Field(..., min_length=1)
    decision: str = Field(..., description="APPROVE or REJECT")
    comments: Optional[str] = None


class BulkKnowledgePublishRequest(BaseModel):
    """Bulk publishing of approved knowledge chunks."""

    chunk_ids: List[uuid.UUID] = Field(..., min_length=1)


class KnowledgeProcessTriggerRequest(BaseModel):
    """Triggers knowledge pipeline extraction on crawled pages or documents."""

    source_type: str = Field(..., description="WEBSITE or DOCUMENT")
    source_id: uuid.UUID = Field(..., description="CrawlJob ID, WebsiteSource ID, or Document ID")


class KnowledgeChunkTextUpdate(BaseModel):
    """Payload to edit chunk text before approving."""

    chunk_text: str


# ==============================================================================
# 5. Structured College Information (Extracted Facts)
# ==============================================================================

class ExtractedFactCreateRequest(BaseModel):
    """Payload to add a structured college factual record."""

    category: str = Field(description="ABOUT, COURSES, ADMISSIONS, DEPARTMENTS, FACILITIES, FAQS")
    fact_key: str = Field(description="Property or label (e.g. 'Eligibility Criteria')")
    fact_value: str = Field(description="Detailed factual description")


class ExtractedFactUpdateRequest(BaseModel):
    """Payload to update an existing structured factual record."""

    category: Optional[str] = None
    fact_key: Optional[str] = None
    fact_value: Optional[str] = None
    verification_status: Optional[str] = None


class ExtractedFactResponse(BaseModel):
    """Structured fact serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    source_type: str
    source_id: uuid.UUID
    category: str
    fact_key: str
    fact_value: str
    verification_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# 6. College Analytics
# ==============================================================================

class CollegeAnalyticsResponse(BaseModel):
    """College-scoped telemetry & student query statistics."""

    total_queries: int
    daily_queries: List[Dict[str, Any]] = []
    popular_questions: List[Dict[str, Any]] = []
    unanswered_questions: List[str] = []
    source_usage: Dict[str, int] = {}
    badge_distribution: Dict[str, int] = {}
    satisfaction_score: float = 4.8


# ==============================================================================
# 7. Support, Feedback & Notifications
# ==============================================================================

class CollegeSupportTicketResponse(BaseModel):
    """Student escalated support inquiry serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    student_name: str
    student_email: str
    subject: str
    message: str
    status: str  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeSupportTicketResolution(BaseModel):
    """Payload to resolve or update student support inquiry."""

    status: str
    response_notes: Optional[str] = None


class CollegeFeedbackResponse(BaseModel):
    """Student rating and comments serialization."""

    id: uuid.UUID
    message_id: uuid.UUID
    user_email: Optional[str] = None
    rating: int
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeNotificationItem(BaseModel):
    """Real-time college admin notification item."""

    id: str
    title: str
    message: str
    type: str  # INFO, WARNING, SUCCESS, ERROR
    created_at: datetime


# ==============================================================================
# 8. Dashboard Aggregation
# ==============================================================================

class CollegeDashboardStats(BaseModel):
    """Summary metric counters for College Admin dashboard cards."""

    total_website_sources: int
    total_crawled_pages: int
    total_documents: int
    pending_reviews: int
    published_chunks: int
    total_queries: int
    recent_crawls_count: int
    recent_documents_count: int
    satisfaction_score: float
    open_tickets_count: int


class CollegeAdminDashboardResponse(BaseModel):
    """Aggregated dashboard payload for authenticated College Admin."""

    college: CollegeProfileResponse
    stats: CollegeDashboardStats
    recent_crawl_jobs: List[CrawlJobResponse] = []
    recent_documents: List[DocumentDetailResponse] = []
    recent_pending_reviews: List[KnowledgeChunkResponse] = []
    recent_tickets: List[CollegeSupportTicketResponse] = []

