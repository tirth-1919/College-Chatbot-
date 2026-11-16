"""College Tenant Schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CollegeCreateRequest(BaseModel):
    """Payload for registering a new college institution."""

    name: str = Field(min_length=3, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    official_domain: str = Field(min_length=3, max_length=255)
    logo_url: Optional[str] = None
    contact_email: EmailStr
    contact_phone: Optional[str] = None


class CollegeUpdateRequest(BaseModel):
    """Payload for updating college institutional details."""

    name: Optional[str] = None
    official_domain: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class CollegeResponse(BaseModel):
    """College serialization schema."""

    id: uuid.UUID
    name: str
    slug: str
    official_domain: str
    logo_url: Optional[str] = None
    contact_email: str
    contact_phone: Optional[str] = None
    status: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeOnboardingRequest(BaseModel):
    """Institutional onboarding application payload."""

    name: str = Field(min_length=3, max_length=255, description="Full formal name of college or university")
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$", description="Unique URL slug (e.g. ait-ahmedabad)")
    official_domain: str = Field(min_length=3, max_length=255, description="Official campus domain (e.g. aitindia.in)")
    contact_email: EmailStr = Field(description="Institutional official contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Institutional contact telephone number")
    address: Optional[str] = Field(None, max_length=500, description="Campus physical address")
    city: Optional[str] = Field(None, max_length=100, description="Campus city")
    state: Optional[str] = Field(None, max_length=100, description="Campus state/province")
    country: Optional[str] = Field("India", max_length=100, description="Campus country")
    accreditation_details: Optional[str] = Field(None, max_length=500, description="Accreditation details (NAAC, NBA, AICTE, NIRF)")
    website_url: Optional[str] = Field(None, max_length=255, description="Primary homepage URL")
    logo_url: Optional[str] = Field(None, max_length=500, description="Institution crest or logo URL")

    # The administrator account is created only after approval and invitation acceptance.
    admin_name: str = Field(min_length=2, max_length=255, description="Full name of designated college administrator")
    admin_email: EmailStr = Field(description="Work email address for designated administrator")
    admin_designation: Optional[str] = Field("College Administrator", max_length=100)


class CollegeOnboardingResponse(BaseModel):
    """Response returned upon submission of an onboarding application."""

    success: bool = True
    message: str
    college_id: uuid.UUID
    college_name: str
    college_slug: str
    official_domain: str
    admin_email: str
    status: str = "PENDING"
    tracking_code: str
    submitted_at: datetime


class CollegeRegistrationStatusResponse(BaseModel):
    """Institutional review and verification status payload."""

    college_id: uuid.UUID
    college_name: str
    slug: str
    official_domain: str
    contact_email: str
    contact_phone: Optional[str] = None
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None
    status: str  # PENDING, APPROVED, REJECTED, SUSPENDED
    is_active: bool
    review_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

