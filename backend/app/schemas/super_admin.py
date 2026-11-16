"""Super Administrator Schemas for Governance, AI, Audits & Telemetry."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# 1. AI Provider Schemas
# ------------------------------------------------------------------------------

class AIProviderConfigCreate(BaseModel):
    """Payload to add a new AI model provider config."""

    provider_name: str = Field(description="gemini, openai, groq, or anthropic")
    model_name: str = Field(description="gemini-1.5-flash, text-embedding-004, gpt-4o-mini")
    is_primary: bool = False
    is_active: bool = True
    timeout_seconds: int = 15
    max_retries: int = 3
    temperature: float = 0.2


class AIProviderConfigUpdate(BaseModel):
    """Payload to update an existing AI model provider config."""

    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = None
    max_retries: Optional[int] = None
    temperature: Optional[float] = None


class AIProviderConfigResponse(BaseModel):
    """AI Provider configuration serialization."""

    id: uuid.UUID
    provider_name: str
    model_name: str
    is_primary: bool
    is_active: bool
    timeout_seconds: int
    max_retries: int
    temperature: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AIProviderTestResponse(BaseModel):
    """Result of an AI model connectivity probe."""

    provider_name: str
    model_name: str
    status: str  # SUCCESS or FAILED
    latency_ms: int
    message: str
    timestamp: datetime


# ------------------------------------------------------------------------------
# 2. Security Audit Log Schemas
# ------------------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    """Security audit log serialization."""

    id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action_type: str
    target_entity: str
    target_id: uuid.UUID
    payload_diff: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ------------------------------------------------------------------------------
# 3. Telemetry & Analytics Schemas
# ------------------------------------------------------------------------------

class UsageAnalyticsResponse(BaseModel):
    """Aggregated token consumption and cost analytics."""

    total_queries: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    average_latency_ms: float
    fallback_rate_percent: float
    estimated_cost_usd: float
    top_colleges: List[Dict[str, Any]] = []


class JobOverviewResponse(BaseModel):
    """Crawler and Document job overview item."""

    id: uuid.UUID
    college_id: uuid.UUID
    college_name: str
    job_type: str  # CRAWLER or DOCUMENT_PROCESSING
    target_name: str  # URL or PDF filename
    status: str
    progress_percent: int
    error_message: Optional[str] = None
    created_at: datetime


class PlatformHealthResponse(BaseModel):
    """System-wide infrastructure telemetry."""

    status: str  # HEALTHY, DEGRADED, CRITICAL
    database: Dict[str, Any]
    redis_broker: Dict[str, Any]
    supabase_storage: Dict[str, Any]
    celery_workers: Dict[str, Any]
    timestamp: datetime


# ------------------------------------------------------------------------------
# 4. System Settings Schemas
# ------------------------------------------------------------------------------

class SystemSettingsResponse(BaseModel):
    """Global system configuration settings."""

    allow_college_registration: bool = True
    default_language: str = "en"
    max_pdf_upload_mb: int = 50
    rate_limit_per_minute: int = 60
    maintenance_mode: bool = False
    rag_similarity_threshold: float = 0.72


class SystemSettingsUpdate(BaseModel):
    """Payload to update global system configuration."""

    allow_college_registration: Optional[bool] = None
    default_language: Optional[str] = None
    max_pdf_upload_mb: Optional[int] = None
    rate_limit_per_minute: Optional[int] = None
    maintenance_mode: Optional[bool] = None
    rag_similarity_threshold: Optional[float] = None


# ------------------------------------------------------------------------------
# 5. Dashboard Aggregations
# ------------------------------------------------------------------------------

class DashboardStats(BaseModel):
    """The 10 key metrics displayed across Super Admin cards."""

    total_colleges: int
    active_colleges: int
    pending_approvals: int
    total_users: int
    total_college_admins: int
    total_queries: int
    total_documents: int
    ai_success_rate: float
    storage_used_mb: float
    monthly_jobs: int


class RecentCollegeItem(BaseModel):
    """Short summary of recently registered college."""

    id: uuid.UUID
    name: str
    slug: str
    official_domain: str
    status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardOverviewResponse(BaseModel):
    """Aggregated payload for super admin dashboard landing."""

    stats: DashboardStats
    recent_colleges: List[RecentCollegeItem]
    recent_audit_logs: List[AuditLogResponse]
    system_status: str


# ------------------------------------------------------------------------------
# 6. College Approvals & Registrations
# ------------------------------------------------------------------------------

class CollegeRegistrationResponse(BaseModel):
    """College pending review or rejected serialization."""

    id: uuid.UUID
    name: str
    slug: str
    official_domain: str
    contact_email: str
    contact_phone: Optional[str] = None
    status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RegistrationDecisionRequest(BaseModel):
    """Approval or Rejection payload with optional justification."""

    reason: Optional[str] = None


# ------------------------------------------------------------------------------
# 7. College Administrator Management
# ------------------------------------------------------------------------------

class CollegeAdminItem(BaseModel):
    """College admin mapping with user and college metadata."""

    membership_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    user_email: str
    college_id: uuid.UUID
    college_name: str
    role_in_college: str
    is_primary: bool
    is_active: bool
    created_at: datetime


class AssignCollegeAdminRequest(BaseModel):
    """Payload to link a user as admin to a college."""

    user_id: uuid.UUID
    college_id: uuid.UUID
    role_in_college: str = "ADMIN"
    is_primary: bool = True


# ------------------------------------------------------------------------------
# 8. Support Tickets
# ------------------------------------------------------------------------------

class SupportTicketSuperAdminResponse(BaseModel):
    """Platform-wide escalated support inquiry serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    college_name: str
    user_id: Optional[uuid.UUID] = None
    student_name: str
    student_email: str
    subject: str
    message: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketStatusUpdate(BaseModel):
    """Payload to transition ticket resolution lifecycle."""

    status: str = Field(description="OPEN, IN_PROGRESS, RESOLVED, or CLOSED")
