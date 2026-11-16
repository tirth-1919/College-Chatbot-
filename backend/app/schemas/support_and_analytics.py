"""Phase 11 & Phase 12 Pydantic Schemas.

Covers:
1. User Preferences (Multilingual settings, notifications, UI theme)
2. Support Tickets & Threaded Replies
3. In-App Notifications
4. Analytics (Platform, College, Question frequency, Unanswered, AI usage)
5. Feedback with detailed categories
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==============================================================================
# 1. USER PREFERENCES & MULTILINGUAL SETTINGS
# ==============================================================================

class UserPreferencesResponse(BaseModel):
    """User preferences response model."""

    user_id: uuid.UUID
    preferred_language: str = "en"
    theme: str = "dark"
    email_notifications: bool = True
    preferences: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """Payload to update user language and interface preferences."""

    preferred_language: Optional[str] = Field(None, description="'en', 'hi', or 'gu'")
    theme: Optional[str] = Field(None, description="'dark' or 'light'")
    email_notifications: Optional[bool] = None
    extra_preferences: Optional[Dict[str, Any]] = None


# ==============================================================================
# 2. SUPPORT TICKETS & THREADED REPLIES
# ==============================================================================

class SupportTicketCreate(BaseModel):
    """Payload to create a new student support ticket."""

    college_id: uuid.UUID
    subject: str = Field(..., min_length=3, max_length=255)
    message: str = Field(..., min_length=10)
    category: str = Field(default="OTHER", description="LOGIN, CHATBOT, INCORRECT_ANSWER, MISSING_INFO, DOCUMENT, TECHNICAL, OTHER")
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, URGENT")
    student_name: Optional[str] = None
    student_email: Optional[str] = None


class SupportTicketReplyCreate(BaseModel):
    """Payload for submitting a response to a support ticket."""

    message_text: str = Field(..., min_length=2)
    is_internal: bool = Field(default=False, description="Internal admin note hidden from student")


class SupportTicketReplyResponse(BaseModel):
    """Serialized reply turn in a ticket conversation thread."""

    id: uuid.UUID
    ticket_id: uuid.UUID
    sender_user_id: Optional[uuid.UUID] = None
    sender_name: str
    sender_role: str
    message_text: str
    is_internal: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SupportTicketResponse(BaseModel):
    """Serialized support ticket overview."""

    id: uuid.UUID
    college_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    student_name: str
    student_email: str
    subject: str
    message: str
    category: str
    priority: str
    status: str
    assigned_to_user_id: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    replies_count: int = 0

    class Config:
        from_attributes = True


class SupportTicketDetailResponse(SupportTicketResponse):
    """Full ticket detail including threaded messages."""

    replies: List[SupportTicketReplyResponse] = []


class SupportTicketStatusUpdate(BaseModel):
    """Payload to update status, priority, or assignment of a support ticket."""

    status: Optional[str] = Field(None, description="OPEN, IN_PROGRESS, WAITING_FOR_USER, RESOLVED, CLOSED")
    priority: Optional[str] = Field(None, description="LOW, MEDIUM, HIGH, URGENT")
    assigned_to_user_id: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None


# ==============================================================================
# 3. IN-APP NOTIFICATIONS
# ==============================================================================

class InAppNotificationResponse(BaseModel):
    """Serialized in-app alert item."""

    id: uuid.UUID
    user_id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    title: str
    message: str
    notification_type: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """List of notifications with unread counter."""

    unread_count: int
    items: List[InAppNotificationResponse]


# ==============================================================================
# 4. ENHANCED FEEDBACK
# ==============================================================================

class FeedbackCreateRequest(BaseModel):
    """Student feedback submission."""

    message_id: uuid.UUID
    rating: int = Field(..., description="1 for helpful, -1 for unhelpful")
    category: str = Field(default="ACCURACY", description="ACCURACY, MISSING_INFO, INCORRECT_INFO, TECHNICAL_ISSUE, GENERAL")
    comments: Optional[str] = None
    college_id: Optional[uuid.UUID] = None
    session_id: Optional[uuid.UUID] = None


class FeedbackItemResponse(BaseModel):
    """Serialized feedback entry."""

    id: uuid.UUID
    college_id: uuid.UUID
    message_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    rating: int
    category: str
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==============================================================================
# 5. ANALYTICS MODELS
# ==============================================================================

class QuestionFrequencyItem(BaseModel):
    """Aggregated frequently asked inquiry."""

    query: str
    count: int
    category: str = "OTHER"
    latest_asked_at: Optional[datetime] = None


class UnansweredQuestionItem(BaseModel):
    """Aggregated question with low retrieval confidence or zero evidence."""

    query: str
    category: str
    occurrence_count: int
    last_occurred_at: datetime
    negative_feedback_count: int = 0
    sample_session_id: Optional[uuid.UUID] = None


class AIUsageMetrics(BaseModel):
    """AI token and latency telemetry metrics."""

    total_requests: int
    primary_requests: int
    secondary_requests: int
    failed_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    average_latency_ms: float
    fallback_rate_percent: float
    estimated_cost_usd: float


class CollegeAnalyticsDetailResponse(BaseModel):
    """College-scoped analytics payload."""

    college_id: uuid.UUID
    time_range: str
    total_queries: int
    total_sessions: int
    active_students_count: int
    satisfaction_score: float
    positive_feedback_count: int
    negative_feedback_count: int
    knowledge_records_count: int
    published_chunks_count: int
    pending_reviews_count: int
    daily_query_trend: List[Dict[str, Any]] = []
    category_distribution: Dict[str, int] = {}
    source_distribution: Dict[str, int] = {}
    frequent_questions: List[QuestionFrequencyItem] = []
    unanswered_questions: List[UnansweredQuestionItem] = []


class PlatformAnalyticsResponse(BaseModel):
    """Global Super Admin platform-level telemetry."""

    time_range: str
    total_colleges: int
    approved_colleges: int
    pending_registrations: int
    total_users: int
    active_users: int
    total_chat_sessions: int
    total_questions_asked: int
    total_knowledge_chunks: int
    total_documents_processed: int
    total_crawled_pages: int
    open_support_tickets: int
    ai_metrics: AIUsageMetrics
    top_active_colleges: List[Dict[str, Any]] = []
    daily_volume_trend: List[Dict[str, Any]] = []

