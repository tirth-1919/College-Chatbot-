"""Colleges & Tenant Management API Router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.college import College
from app.models.user import User
from app.repositories.college_repository import CollegeRepository
from app.repositories.registration_repository import RegistrationRepository
from app.schemas.college import (
    CollegeCreateRequest,
    CollegeUpdateRequest,
    CollegeResponse,
    CollegeOnboardingRequest,
    CollegeOnboardingResponse,
)
from app.schemas.common import APIResponse
from app.dependencies.auth import get_current_user, get_optional_current_user, require_super_admin
from app.schemas.registration import PublicRegistrationStatusResponse
from app.middleware.rate_limit import rate_limit

router = APIRouter(prefix="/colleges", tags=["Colleges & Tenants"])

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "protonmail.com", "aol.com", "mail.com", "zoho.com", "yandex.com"
}


@router.post(
    "/onboarding/register",
    response_model=APIResponse[CollegeOnboardingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Public institutional registration submission",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=3600))],
)
async def submit_college_onboarding(
    req: CollegeOnboardingRequest,
    session: AsyncSession = Depends(get_db),
):
    """Stores a pending application; admin access is withheld until invitation acceptance."""
    domain = req.official_domain.lower().strip().removeprefix("www.")
    if domain in GENERIC_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official college domain must be an institutional domain, not a public email provider.",
        )

    reg = await RegistrationRepository(session).create_registration(
        college_name=req.name,
        slug=req.slug,
        official_domain=domain,
        official_email=req.contact_email,
        contact_person_name=req.admin_name,
        contact_person_email=req.admin_email,
        contact_phone=req.contact_phone,
        address=req.address,
        city=req.city,
        state=req.state,
        country=req.country or "India",
        accreditation_details=req.accreditation_details,
        website_url=req.website_url,
        logo_url=req.logo_url,
        initial_admin_name=req.admin_name,
        initial_admin_email=req.admin_email,
        initial_admin_designation=req.admin_designation or "College Administrator",
    )

    return APIResponse(
        success=True,
        message="Your college onboarding application has been submitted successfully and is queued for verification.",
        data=CollegeOnboardingResponse(
            success=True,
            message="Application submitted for Super Admin review",
            college_id=reg.college_id,
            college_name=reg.college_name,
            college_slug=reg.slug,
            official_domain=reg.official_domain,
            admin_email=reg.initial_admin_email,
            status=reg.status,
            tracking_code=reg.tracking_code,
            submitted_at=reg.created_at,
        ),
    )


@router.get(
    "/onboarding/status",
    response_model=APIResponse[PublicRegistrationStatusResponse],
    summary="Public registration status tracker using its private tracking code",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def check_onboarding_status(
    query: str = Query(..., min_length=12, max_length=80, description="Private registration tracking code"),
    session: AsyncSession = Depends(get_db),
):
    """Returns the minimal registration status only to a tracking-code holder."""
    reg = await RegistrationRepository(session).get_by_tracking_code(query)
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registration application found for that tracking code.",
        )
    return APIResponse(
        success=True,
        message=f"Registration status is {reg.status}",
        data=PublicRegistrationStatusResponse.model_validate(reg),
    )


@router.get(
    "",
    response_model=APIResponse[List[CollegeResponse]],
    summary="List approved colleges (Public directory)",
)
async def list_colleges(
    all_colleges: bool = Query(False, description="Set to true to see pending/suspended colleges (Super Admin only)"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Returns a list of approved colleges for students to select from."""
    college_repo = CollegeRepository(session)
    only_approved = True

    if all_colleges:
        if not current_user or current_user.role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Administrators can list unapproved colleges.",
            )
        only_approved = False

    colleges = await college_repo.list_colleges(only_approved=only_approved)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(colleges)} colleges",
        data=[CollegeResponse.model_validate(c) for c in colleges],
    )


@router.get(
    "/{college_id_or_slug}",
    response_model=APIResponse[CollegeResponse],
    summary="Get single college profile",
)
async def get_college_details(
    college_id_or_slug: str,
    session: AsyncSession = Depends(get_db),
):
    """Retrieves detailed profile information for a college by UUID or slug."""
    college_repo = CollegeRepository(session)

    try:
        college_uuid = uuid.UUID(college_id_or_slug)
        college = await college_repo.get_by_id(college_uuid)
    except ValueError:
        college = await college_repo.get_by_slug(college_id_or_slug)

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found.")

    return APIResponse(
        success=True,
        message="College profile retrieved",
        data=CollegeResponse.model_validate(college),
    )


@router.post(
    "",
    response_model=APIResponse[CollegeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new college tenant",
)
async def create_college(
    req: CollegeCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Creates a new college onboarding request (PENDING status unless created by Super Admin)."""
    college_repo = CollegeRepository(session)

    existing_slug = await college_repo.get_by_slug(req.slug)
    if existing_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A college with slug '{req.slug}' already exists.",
        )

    initial_status = "APPROVED" if current_user.role == "SUPER_ADMIN" else "PENDING"

    college = College(
        id=uuid.uuid4(),
        name=req.name.strip(),
        slug=req.slug.lower().strip(),
        official_domain=req.official_domain.lower().strip(),
        logo_url=req.logo_url,
        contact_email=req.contact_email.lower().strip(),
        contact_phone=req.contact_phone,
        status=initial_status,
        is_active=True,
    )

    created_college = await college_repo.create(college)
    return APIResponse(
        success=True,
        message="College tenant registered successfully",
        data=CollegeResponse.model_validate(created_college),
    )


@router.patch(
    "/{college_id}",
    response_model=APIResponse[CollegeResponse],
    summary="Update college institutional details (Super Admin or College Admin)",
)
async def update_college(
    college_id: uuid.UUID,
    req: CollegeUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Updates college institutional profile or operational status."""
    college_repo = CollegeRepository(session)
    college = await college_repo.get_by_id(college_id)
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found.")

    # Status approval changes require SUPER_ADMIN
    if req.status is not None and req.status != college.status:
        if current_user.role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Super Administrators can modify college status.",
            )
        college.status = req.status

    if req.name is not None:
        college.name = req.name
    if req.official_domain is not None:
        college.official_domain = req.official_domain
    if req.logo_url is not None:
        college.logo_url = req.logo_url
    if req.contact_email is not None:
        college.contact_email = req.contact_email
    if req.contact_phone is not None:
        college.contact_phone = req.contact_phone
    if req.is_active is not None and current_user.role == "SUPER_ADMIN":
        college.is_active = req.is_active

    updated = await college_repo.update(college)
    return APIResponse(
        success=True,
        message="College details updated",
        data=CollegeResponse.model_validate(updated),
    )

