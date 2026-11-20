"""User Profile and Account Schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    """User profile data serialization schema."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: str
    is_verified: bool
    is_active: bool
    # Legacy account rows may predate the database timestamp default.
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Payload for updating user profile information."""

    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

