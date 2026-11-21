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
    updated_at: Optional[datetime] = None

    # 1. Institution Identity
    short_name: Optional[str] = None
    cover_image_url: Optional[str] = None
    institution_type: Optional[str] = None
    established_year: Optional[int] = None
    website_url: Optional[str] = None

    # 2. Address & Location
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    postal_code: Optional[str] = None
    maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # 3. Official Contacts
    admission_email: Optional[str] = None
    examination_email: Optional[str] = None
    placement_email: Optional[str] = None
    admission_helpline: Optional[str] = None
    alternate_phone: Optional[str] = None
    working_hours: Optional[str] = None

    # 4. Recognition & Accreditation
    affiliated_university: Optional[str] = None
    recognized_by: Optional[str] = None
    aicte_approval: Optional[str] = None
    ugc_recognition: Optional[str] = None
    naac_grade: Optional[str] = None
    nba_accreditation: Optional[str] = None
    accreditation_validity: Optional[str] = None
    approval_document_url: Optional[str] = None

    # 5. About Institution & Leadership
    short_description: Optional[str] = None
    about_text: Optional[str] = None
    vision: Optional[str] = None
    mission: Optional[str] = None
    leader_name: Optional[str] = None
    leader_designation: Optional[str] = None

    # 6. Social Media
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    twitter_url: Optional[str] = None

    # 7. Branding
    favicon_url: Optional[str] = None
    primary_brand_color: Optional[str] = "#10B981"
    secondary_brand_color: Optional[str] = "#6366F1"

    # 8. Draft State
    draft_profile: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CollegeProfileUpdateRequest(BaseModel):
    """Permitted fields for institutional profile updates by College Admin."""

    name: Optional[str] = None
    official_domain: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    logo_url: Optional[str] = None

    # 1. Institution Identity
    short_name: Optional[str] = None
    cover_image_url: Optional[str] = None
    institution_type: Optional[str] = None
    established_year: Optional[int] = None
    website_url: Optional[str] = None

    # 2. Address & Location
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    maps_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # 3. Official Contacts
    admission_email: Optional[str] = None
    examination_email: Optional[str] = None
    placement_email: Optional[str] = None
    admission_helpline: Optional[str] = None
    alternate_phone: Optional[str] = None
    working_hours: Optional[str] = None

    # 4. Recognition & Accreditation
    affiliated_university: Optional[str] = None
    recognized_by: Optional[str] = None
    aicte_approval: Optional[str] = None
    ugc_recognition: Optional[str] = None
    naac_grade: Optional[str] = None
    nba_accreditation: Optional[str] = None
    accreditation_validity: Optional[str] = None
    approval_document_url: Optional[str] = None

    # 5. About Institution & Leadership
    short_description: Optional[str] = None
    about_text: Optional[str] = None
    vision: Optional[str] = None
    mission: Optional[str] = None
    leader_name: Optional[str] = None
    leader_designation: Optional[str] = None

    # 6. Social Media
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    twitter_url: Optional[str] = None

    # 7. Branding
    favicon_url: Optional[str] = None
    primary_brand_color: Optional[str] = None
    secondary_brand_color: Optional[str] = None


class CollegeDraftSaveRequest(BaseModel):
    """Payload to save an in-progress draft profile."""

    draft_data: Dict[str, Any]


class CollegeProfileHistoryItemResponse(BaseModel):
    """Historical audit entry for profile modifications."""

    id: uuid.UUID
    action_type: str
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    actor_email: Optional[str] = None
    payload_diff: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileAssetUploadResponse(BaseModel):
    """Response returned upon successful asset upload."""

    asset_url: str
    asset_type: str
    file_name: str
    file_size_bytes: int


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
    pages_count: int = 0  # Computed separately; not a DB column — always defaults to 0
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Override to safely handle the computed pages_count field missing on the ORM object."""
        if not isinstance(obj, dict) and not hasattr(obj, "pages_count"):
            data = {
                "id": obj.id,
                "college_id": obj.college_id,
                "base_url": obj.base_url,
                "allowed_subdomains": obj.allowed_subdomains,
                "max_depth": obj.max_depth,
                "max_pages": obj.max_pages,
                "crawl_frequency": obj.crawl_frequency,
                "is_active": obj.is_active,
                "last_crawled_at": obj.last_crawled_at,
                "pages_count": 0,
                "created_at": obj.created_at,
            }
            return super().model_validate(data, **kwargs)
        return super().model_validate(obj, **kwargs)


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

        Guard also covers the case where data is already a dict but its
        ``metadata`` key holds a SQLAlchemy MetaData() object (e.g. injected by
        a buggy test fixture or future serializer).
        """
        import sqlalchemy  # local import avoids circular deps at module load

        def _safe_meta(val: Any) -> dict:
            """Return val if it is a plain dict, else an empty dict."""
            if isinstance(val, dict):
                return val
            # Explicitly guard against sqlalchemy MetaData objects
            if isinstance(val, sqlalchemy.MetaData):
                return {}
            return {}

        if isinstance(data, dict):
            # Already a dict: sanitise the metadata key in place if poisoned.
            if not isinstance(data.get("metadata"), dict):
                data = {**data, "metadata": _safe_meta(data.get("metadata"))}
            return data

        if hasattr(data, "metadata_"):
            # ORM instance path: read the Python-side attribute name (metadata_)
            # to avoid resolving the class-level MetaData descriptor.
            return {
                "id": getattr(data, "id", None),
                "crawl_job_id": getattr(data, "crawl_job_id", None),
                "log_level": getattr(data, "log_level", "INFO"),
                "message": getattr(data, "message", ""),
                "metadata": _safe_meta(getattr(data, "metadata_", {})),
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
    """Metadata payload for document upload (JSON pre-upload registration)."""

    original_filename: str
    file_size_bytes: int
    mime_type: str = "application/pdf"
    category: Optional[str] = "GENERAL"
    description: Optional[str] = None
    checksum_sha256: Optional[str] = Field(
        default=None,
        description="Real SHA-256 hex checksum (64 chars) of the already-uploaded file.",
    )


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

