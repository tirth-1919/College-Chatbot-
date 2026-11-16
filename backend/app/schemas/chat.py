"""Chat Conversation & Feedback Schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    """Payload to initiate a new conversational session."""

    college_id: uuid.UUID
    session_title: Optional[str] = "New Conversation"
    language: str = Field(default="en", description="en, hi, or gu")


class RenameSessionRequest(BaseModel):
    """Payload to rename an existing chat session title."""

    session_title: str = Field(min_length=1, max_length=255)


class SendMessageRequest(BaseModel):
    """Payload for submitting a user question to the chatbot."""

    message_text: str = Field(min_length=1)
    language: Optional[str] = "en"


class SourceCitation(BaseModel):
    """Structured citation metadata pointing to official sources."""

    title: str
    source_type: str = "OFFICIAL_WEBSITE"  # OFFICIAL_WEBSITE or PDF
    url: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None
    similarity_score: Optional[float] = None


class ChatMessageResponse(BaseModel):
    """Messageturn serialization schema."""

    id: uuid.UUID
    session_id: uuid.UUID
    sender_role: str
    message_text: str
    is_verified: bool
    answer_source_type: str
    source_citations: List[Dict[str, Any]] = []
    token_count: int
    model_used: Optional[str] = None
    created_at: datetime
    # Failover metadata — optional with defaults for backward compatibility
    answer_mode: Optional[str] = None
    actual_provider: Optional[str] = None
    actual_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    attempt_count: int = 0
    request_duration_ms: Optional[int] = None

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    """Chat session serialization schema."""

    id: uuid.UUID
    college_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    session_title: str
    language: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = None
    visitor_token: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def handle_unloaded_relations(cls, data: Any) -> Any:
        if hasattr(data, "__dict__"):
            state = getattr(data, "_sa_instance_state", None)
            if state and "messages" not in state.dict:
                return {
                    "id": getattr(data, "id"),
                    "college_id": getattr(data, "college_id"),
                    "user_id": getattr(data, "user_id", None),
                    "session_title": getattr(data, "session_title"),
                    "language": getattr(data, "language"),
                    "is_active": getattr(data, "is_active"),
                    "created_at": getattr(data, "created_at"),
                    "updated_at": getattr(data, "updated_at"),
                    "messages": None,
                }
        return data


class FeedbackRequest(BaseModel):
    """Payload for submitting student feedback on a response."""

    rating: int = Field(description="1 for thumbs up, -1 for thumbs down, or 1-5 rating")
    comments: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback confirmation schema."""

    id: uuid.UUID
    college_id: uuid.UUID
    message_id: uuid.UUID
    rating: int
    comments: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

