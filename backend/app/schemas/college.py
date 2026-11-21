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

    # Institutional Metadata
    short_name: Optional[str] = None
    cover_image_url: Optional[str] = None
    institution_type: Optional[str] = None
    established_year: Optional[int] = None
    website_url: Optional[str] = None
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
    admission_email: Optional[str] = None
    examination_email: Optional[str] = None
    placement_email: Optional[str] = None
    admission_helpline: Optional[str] = None
    alternate_phone: Optional[str] = None
    working_hours: Optional[str] = None
    affiliated_university: Optional[str] = None
    recognized_by: Optional[str] = None
    aicte_approval: Optional[str] = None
    ugc_recognition: Optional[str] = None
    naac_grade: Optional[str] = None
    nba_accreditation: Optional[str] = None
    accreditation_validity: Optional[str] = None
    approval_document_url: Optional[str] = None
    short_description: Optional[str] = None
    about_text: Optional[str] = None
    vision: Optional[str] = None
    mission: Optional[str] = None
    leader_name: Optional[str] = None
    leader_designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    twitter_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_brand_color: Optional[str] = None
    secondary_brand_color: Optional[str] = None


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
    updated_at: Optional[datetime] = None

    # Public Institutional Metadata
    short_name: Optional[str] = None
    cover_image_url: Optional[str] = None
    institution_type: Optional[str] = None
    established_year: Optional[int] = None
    website_url: Optional[str] = None
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
    admission_email: Optional[str] = None
    examination_email: Optional[str] = None
    placement_email: Optional[str] = None
    admission_helpline: Optional[str] = None
    alternate_phone: Optional[str] = None
    working_hours: Optional[str] = None
    affiliated_university: Optional[str] = None
    recognized_by: Optional[str] = None
    aicte_approval: Optional[str] = None
    ugc_recognition: Optional[str] = None
    naac_grade: Optional[str] = None
    nba_accreditation: Optional[str] = None
    accreditation_validity: Optional[str] = None
    approval_document_url: Optional[str] = None
    short_description: Optional[str] = None
    about_text: Optional[str] = None
    vision: Optional[str] = None
    mission: Optional[str] = None
    leader_name: Optional[str] = None
    leader_designation: Optional[str] = None
    linkedin_url: Optional[str] = None
    instagram_url: Optional[str] = None
    facebook_url: Optional[str] = None
    youtube_url: Optional[str] = None
    twitter_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_brand_color: Optional[str] = "#10B981"
    secondary_brand_color: Optional[str] = "#6366F1"

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
    # college_id is NULL for PENDING registrations whose college record has not
    # yet been created (ON DELETE SET NULL foreign key). Make it Optional so the
    # schema can be constructed immediately after the registration row is inserted.
    college_id: Optional[uuid.UUID] = None
    college_name: str
    college_slug: str
    official_domain: str
    # admin_email is taken from initial_admin_email which is optional in the
    # registration form; callers should pass None when no email was supplied.
    admin_email: Optional[str] = None
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

