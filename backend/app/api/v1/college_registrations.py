"""Public College Registration & Application Tracking API Router.

Enables educational institutions to submit onboarding applications, check review status,
and supply additional compliance information requested by Super Admins.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.repositories.registration_repository import RegistrationRepository
from app.middleware.rate_limit import rate_limit
from app.schemas.registration import (
    CollegeRegistrationCreateRequest,
    CollegeRegistrationResponse,
    PublicRegistrationStatusResponse,
    AdditionalInfoSubmissionRequest,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/college-registrations", tags=["College Onboarding & Registrations"])

GENERIC_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "protonmail.com", "aol.com", "mail.com", "zoho.com", "yandex.com"
}


@router.post(
    "",
    response_model=APIResponse[CollegeRegistrationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit college onboarding registration application",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=3600))],
)
async def submit_college_registration(
    req: CollegeRegistrationCreateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Allows an institutional representative to submit a registration application.

    Validates institutional domain, checks for duplicate slug/domain, and queues
    the application in PENDING status for Super Admin verification.
    """
    reg_repo = RegistrationRepository(session)
    domain = req.official_domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]

    if domain in GENERIC_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official college domain must be an educational or institutional domain, not a public email provider.",
        )

    try:
        reg = await reg_repo.create_registration(
            college_name=req.college_name,
            slug=req.slug,
            official_domain=domain,
            official_email=req.official_email,
            contact_person_name=req.contact_person_name,
            contact_person_email=req.contact_person_email,
            college_code=req.college_code,
            contact_phone=req.contact_phone,
            address=req.address,
            city=req.city,
            state=req.state,
            country=req.country,
            description=req.description,
            accreditation_details=req.accreditation_details,
            website_url=req.website_url,
            logo_url=req.logo_url,
            supporting_documents=req.supporting_documents,
            initial_admin_name=req.initial_admin_name,
            initial_admin_email=req.initial_admin_email,
            initial_admin_designation=req.initial_admin_designation or "College Administrator",
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An institution with that slug or official domain is already registered.",
        ) from exc

    return APIResponse(
        success=True,
        message=f"Application submitted successfully. Your tracking code is {reg.tracking_code}",
        data=CollegeRegistrationResponse.model_validate(reg),
    )


@router.get(
    "/my-status",
    response_model=APIResponse[PublicRegistrationStatusResponse],
    summary="Check application status using its private tracking code",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def check_registration_status(
    query: str = Query(..., min_length=12, max_length=80, description="Private registration tracking code"),
    session: AsyncSession = Depends(get_db),
):
    """Returns a minimal status view only to callers holding the tracking code."""
    reg_repo = RegistrationRepository(session)
    reg = await reg_repo.get_by_tracking_code(query)

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


@router.post(
    "/submit-information",
    response_model=APIResponse[PublicRegistrationStatusResponse],
    summary="Submit requested additional information for pending review",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
async def submit_additional_information(
    req: AdditionalInfoSubmissionRequest,
    session: AsyncSession = Depends(get_db),
):
    """Allows applicant to respond when status is ADDITIONAL_INFORMATION_REQUIRED."""
    reg_repo = RegistrationRepository(session)
    reg = await reg_repo.submit_additional_information(
        tracking_code=req.tracking_code,
        response_text=req.additional_information,
        additional_docs=req.additional_documents,
    )

    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registration application found for tracking code '{req.tracking_code}'.",
        )

    return APIResponse(
        success=True,
        message="Additional information submitted successfully. Your application is now Under Review.",
        data=PublicRegistrationStatusResponse.model_validate(reg),
    )


@router.get(
    "/check-slug",
    response_model=APIResponse[Dict[str, Any]],
    summary="Check availability of a college slug",
)
async def check_slug_availability(
    slug: str = Query(..., min_length=2),
    session: AsyncSession = Depends(get_db),
):
    """Validates slug formatting and checks if already registered or reserved."""
    clean_slug = slug.strip().lower()
    result = await session.execute(
        text(
            "SELECT public.check_public_registration_availability(:slug, NULL)"
        ),
        {"slug": clean_slug},
    )
    available = bool(result.scalar_one())

    return APIResponse(
        success=True,
        message="Slug availability checked",
        data={"slug": clean_slug, "available": available},
    )

