"""Schemas registry."""

from app.schemas.common import APIResponse, HealthResponse, ErrorResponse
from app.schemas.auth import RegisterRequest, LoginRequest, VerifyEmailRequest, TokenResponse
from app.schemas.user import UserResponse, UserUpdateRequest
from app.schemas.college import CollegeCreateRequest, CollegeUpdateRequest, CollegeResponse
from app.schemas.membership import MembershipCreateRequest, MembershipResponse
from app.schemas.chat import (
    CreateSessionRequest,
    RenameSessionRequest,
    SendMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    FeedbackRequest,
    FeedbackResponse,
    SourceCitation,
)

__all__ = [
    "APIResponse",
    "HealthResponse",
    "ErrorResponse",
    "RegisterRequest",
    "LoginRequest",
    "VerifyEmailRequest",
    "TokenResponse",
    "UserResponse",
    "UserUpdateRequest",
    "CollegeCreateRequest",
    "CollegeUpdateRequest",
    "CollegeResponse",
    "MembershipCreateRequest",
    "MembershipResponse",
    "CreateSessionRequest",
    "RenameSessionRequest",
    "SendMessageRequest",
    "ChatMessageResponse",
    "ChatSessionResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "SourceCitation",
]
