"""Authentication and User Registration Schemas."""

import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for registering a new user account."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    full_name: str = Field(min_length=2, max_length=100)
    role: str = Field(default="STUDENT", description="Public registration supports STUDENT accounts only")
    college_id: Optional[uuid.UUID] = Field(default=None, description="College administrators must use an approved onboarding or invitation flow")


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    """Payload for verifying email address."""

    email: EmailStr
    token: str = Field(min_length=6, max_length=64)


class TokenResponse(BaseModel):
    """Returned payload upon successful authentication."""

    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    college_id: Optional[uuid.UUID] = None
    is_verified: bool
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an expired access token."""

    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Payload for requesting a password reset link."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload for resetting password with verification token."""

    email: EmailStr
    token: str = Field(min_length=6, max_length=64)
    new_password: str = Field(min_length=8, description="Minimum 8 characters")

