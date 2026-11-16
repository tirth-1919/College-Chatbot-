"""College Membership Schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class MembershipCreateRequest(BaseModel):
    """Payload for associating an administrator with a college tenant."""

    college_id: uuid.UUID
    user_id: uuid.UUID
    role_in_college: str = "ADMIN"


class MembershipResponse(BaseModel):
    """Membership serialization schema."""

    id: uuid.UUID
    college_id: uuid.UUID
    user_id: uuid.UUID
    role_in_college: str
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True

