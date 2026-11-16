"""College Registration, Onboarding Progress, and Admin Invitation Schemas."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# ------------------------------------------------------------------------------
# 1. College Registration Schemas
# ------------------------------------------------------------------------------

class SupportingDocumentItem(BaseModel):
    """Uploaded institutional accreditation or authorization document."""

    title: str
    file_url: str
    document_type: str = "AFFILIATION_LETTER"  # AICTE, NAAC, UNIVERSITY_AFFILIATION, BROCHURE
    file_size_bytes: Optional[int] = None


class CollegeRegistrationCreateRequest(BaseModel):
    """Payload for submitting a new college registration application."""

    college_name: str = Field(min_length=3, max_length=255, description="Full formal college name")
    college_code: Optional[str] = Field(None, max_length=50, description="State / University institutional code")
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$", description="URL-safe slug")
    official_domain: str = Field(min_length=3, max_length=255, description="Campus official domain")
    official_email: EmailStr = Field(description="Institutional contact email")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Campus telephone number")
    contact_person_name: str = Field(min_length=2, max_length=255, description="Representative / Registrar full name")
    contact_person_email: EmailStr = Field(description="Representative direct email")
    address: Optional[str] = Field(None, max_length=500, description="Campus address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=100, description="State / Province")
    country: str = Field("India", max_length=100, description="Country")
    description: Optional[str] = Field(None, max_length=2000, description="Brief description of the college")
    accreditation_details: Optional[str] = Field(None, max_length=500, description="Accreditation details (e.g. AICTE, NAAC A+)")
    website_url: Optional[str] = Field(None, max_length=255, description="Official homepage URL")
    logo_url: Optional[str] = Field(None, max_length=500, description="College crest / emblem URL")
    supporting_documents: List[Dict[str, Any]] = Field(default_factory=list, description="List of verification documents")

    # Initial Designated College Administrator
    initial_admin_name: str = Field(min_length=2, max_length=255)
    initial_admin_email: EmailStr
    initial_admin_designation: Optional[str] = Field("College Administrator", max_length=100)


class RegistrationReviewHistoryItem(BaseModel):
    """Review trail entry for a registration application."""

    id: uuid.UUID
    reviewer_user_id: Optional[uuid.UUID] = None
    previous_status: str
    new_status: str
    comments: Optional[str] = None
    action_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class CollegeRegistrationResponse(BaseModel):
    """Summary of institutional registration."""

    id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    college_name: str
    college_code: Optional[str] = None
    slug: str
    official_domain: str
    contact_email: str
    contact_phone: Optional[str] = None
    contact_person_name: str
    contact_person_email: str
    status: str
    tracking_code: str
    website_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollegeRegistrationDetailResponse(CollegeRegistrationResponse):
    """Detailed institutional registration view with review metadata."""

    address: Optional[str] = None
    description: Optional[str] = None
    accreditation_details: Optional[str] = None
    logo_url: Optional[str] = None
    supporting_documents: List[Dict[str, Any]] = []
    initial_admin_name: Optional[str] = None
    initial_admin_email: Optional[str] = None
    initial_admin_designation: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None
    additional_info_requested: Optional[str] = None
    additional_info_submitted: Optional[str] = None
    review_history: List[RegistrationReviewHistoryItem] = []


class PublicRegistrationStatusResponse(BaseModel):
    """Public status fields returned only to a holder of the tracking code."""

    id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    college_name: str
    slug: str
    official_domain: str
    status: str
    tracking_code: str
    created_at: datetime
    updated_at: datetime
    additional_info_requested: Optional[str] = None


class RegistrationReviewDecisionRequest(BaseModel):
    """Super Admin decision action payload."""

    action: str = Field(description="'APPROVE', 'REJECT', or 'REQUEST_INFO'")
    comments: Optional[str] = Field(None, max_length=2000, description="Remarks / reason for decision")
    additional_info_prompt: Optional[str] = Field(None, max_length=2000, description="Details requested from applicant")


class AdditionalInfoSubmissionRequest(BaseModel):
    """Applicant response to additional information request."""

    tracking_code: str = Field(description="Tracking code of the application")
    additional_information: str = Field(min_length=10, max_length=3000, description="Requested response")
    additional_documents: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


# ------------------------------------------------------------------------------
# 2. College Admin Invitation Schemas
# ------------------------------------------------------------------------------

class CollegeAdminInviteRequest(BaseModel):
    """Super Admin invitation payload to add an institutional administrator."""

    email: EmailStr = Field(description="Institutional email address of the invitee")
    full_name: str = Field(min_length=2, max_length=255, description="Full formal name of administrator")
    role_in_college: Literal["ADMIN", "EDITOR", "VIEWER"] = Field(
        "ADMIN", description="ADMIN, EDITOR, or VIEWER"
    )


class CollegeAdminInvitationResponse(BaseModel):
    """Invitation record serialization."""

    id: uuid.UUID
    college_id: uuid.UUID
    college_name: Optional[str] = None
    email: str
    full_name: str
    role_in_college: str
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AcceptInvitationRequest(BaseModel):
    """Invited administrator account setup payload."""

    invitation_token: str = Field(description="One-time invitation token")
    full_name: str = Field(min_length=2, max_length=255)
    password: Optional[str] = Field(
        None, min_length=8, max_length=128, description="Set a password for a new account"
    )


# ------------------------------------------------------------------------------
# 3. College Onboarding Progress Schemas
# ------------------------------------------------------------------------------

class CollegeOnboardingProgressResponse(BaseModel):
    """Multi-step onboarding progression state."""

    id: uuid.UUID
    college_id: uuid.UUID
    college_name: Optional[str] = None
    college_slug: Optional[str] = None
    current_step: int  # 1 to 6
    is_approved: bool
    admin_assigned: bool
    profile_completed: bool
    website_configured: bool
    documents_uploaded: bool
    knowledge_ready: bool
    is_completed: bool
    step_data: Dict[str, Any] = {}
    completed_at: Optional[datetime] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class CollegeOnboardingProgressUpdate(BaseModel):
    """Payload to update current onboarding progress step and state."""

    current_step: Optional[int] = Field(None, ge=1, le=6)
    profile_completed: Optional[bool] = None
    website_configured: Optional[bool] = None
    documents_uploaded: Optional[bool] = None
    knowledge_ready: Optional[bool] = None
    step_data: Optional[Dict[str, Any]] = None


# ------------------------------------------------------------------------------
# 4. Notification Audit Schemas
# ------------------------------------------------------------------------------

class NotificationLogResponse(BaseModel):
    """Notification audit record."""

    id: uuid.UUID
    college_id: Optional[uuid.UUID] = None
    recipient_email: str
    event_type: str
    subject: str
    delivery_status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

