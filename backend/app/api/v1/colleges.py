"""
Public College Registration and Status Tracking API
Provides public endpoints for colleges to register on the multi-college platform,
and for applicants to check their application review status.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.models.college import College

router = APIRouter(prefix="/colleges", tags=["Public Colleges"])


class CollegeRegistrationRequest(BaseModel):
    college_name: str
    college_code: Optional[str] = None
    official_website: str
    official_email: EmailStr
    contact_person: str
    contact_email: EmailStr
    contact_phone: str
    address: str
    city: str
    state: str
    country: Optional[str] = "India"
    university_affiliation: Optional[str] = None
    logo_url: Optional[str] = None
    description: Optional[str] = None
    auth_document_path: Optional[str] = None
    additional_info: Optional[str] = None

    @field_validator("college_name")
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("College name must be at least 3 characters long")
        return v

    @field_validator("official_website")
    def validate_website(cls, v):
        v = v.strip()
        if not re.match(r"^https?://[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]+$", v):
            raise ValueError("Official website must be a valid URL starting with http:// or https://")
        return v

    @field_validator("contact_phone")
    def validate_phone(cls, v):
        v = v.strip()
        clean = re.sub(r"[\s\-\(\)\+]", "", v)
        if len(clean) < 7 or len(clean) > 15:
            raise ValueError("Please provide a valid contact phone number")
        return v


def _generate_unique_application_id(db: Session) -> str:
    """Generates unique application ID formatted as COL-2026-XXXXX."""
    count = db.query(College).count() + 1
    for attempt in range(50):
        app_id = f"COL-2026-{count:05d}"
        if not db.query(College).filter(College.application_id == app_id).first():
            return app_id
        count += 1
    return f"COL-2026-{str(uuid.uuid4())[:6].upper()}"


def _generate_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", name).strip().lower()
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug[:80]


def _derive_code(name: str) -> str:
    words = [w for w in re.split(r"[^a-zA-Z0-9]", name) if w]
    if len(words) >= 2:
        return "".join(w[0] for w in words[:4]).upper()
    return name[:4].upper()


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="Submit College Registration")
def register_college(req: CollegeRegistrationRequest, db: Session = Depends(get_db)):
    """
    Public College Registration Endpoint.
    Validates required fields, checks for duplicate active/pending registrations,
    and creates a registration request with status PENDING.
    Does NOT create an active admin account at this stage.
    """
    college_name = req.college_name.strip()
    code = (req.college_code.strip().upper() if req.college_code else _derive_code(college_name))
    slug = _generate_slug(college_name)

    # 1. Duplicate detection: College Name
    existing_name = db.query(College).filter(
        func.lower(College.name) == college_name.lower(),
        College.status.in_(["ACTIVE", "PENDING", "UNDER_REVIEW"])
    ).first()
    if existing_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A registration for '{college_name}' is already {existing_name.status.lower()} (Application ID: {existing_name.application_id})."
        )

    # 2. Duplicate detection: College Code
    existing_code = db.query(College).filter(
        College.code == code,
        College.status.in_(["ACTIVE", "PENDING", "UNDER_REVIEW"])
    ).first()
    if existing_code:
        code = f"{code[:3]}{str(uuid.uuid4())[:3].upper()}"

    # Ensure slug uniqueness
    base_slug = slug
    counter = 1
    while db.query(College).filter(College.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    # 3. Duplicate detection: Official Email
    existing_email = db.query(College).filter(
        func.lower(College.official_email) == str(req.official_email).lower(),
        College.status.in_(["ACTIVE", "PENDING", "UNDER_REVIEW"])
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The official email '{req.official_email}' is already registered with application ID {existing_email.application_id}."
        )

    app_id = _generate_unique_application_id(db)

    new_college = College(
        id=str(uuid.uuid4()),
        name=college_name,
        code=code,
        slug=slug,
        official_email=str(req.official_email),
        official_website=req.official_website,
        phone=req.contact_phone,
        address=req.address,
        city=req.city,
        state=req.state,
        country=req.country or "India",
        university_affiliation=req.university_affiliation,
        contact_person=req.contact_person,
        contact_email=str(req.contact_email),
        contact_phone=req.contact_phone,
        logo_url=req.logo_url,
        description=req.description,
        auth_document_path=req.auth_document_path,
        additional_info=req.additional_info,
        status="PENDING",
        registration_status="PENDING",
        application_id=app_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.add(new_college)
    db.commit()
    db.refresh(new_college)

    return {
        "message": "Your college registration request has been submitted successfully.",
        "application_id": app_id,
        "status": "PENDING APPROVAL",
        "college_name": new_college.name,
        "submitted_at": new_college.created_at.isoformat(),
        "note": "The request will be reviewed by the Platform Super Admin."
    }


@router.get("/registration-status/{application_id}", summary="Check Application Status")
def get_registration_status(application_id: str, db: Session = Depends(get_db)):
    """
    Public Status Tracking Endpoint.
    Allows applicants to check the progress of their college registration.
    """
    app_id_clean = application_id.strip().upper()
    college = db.query(College).filter(
        func.upper(College.application_id) == app_id_clean
    ).first()

    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application ID '{application_id}' not found. Please verify the ID and try again."
        )

    display_status = college.status
    status_label = "PENDING SUPER ADMIN APPROVAL"
    if display_status == "ACTIVE":
        status_label = "APPROVED"
    elif display_status == "UNDER_REVIEW":
        status_label = "UNDER REVIEW"
    elif display_status == "REJECTED":
        status_label = "REJECTED"
    elif display_status == "NEED_MORE_INFORMATION":
        status_label = "NEED MORE INFORMATION"
    elif display_status == "SUSPENDED":
        status_label = "SUSPENDED"

    return {
        "application_id": college.application_id,
        "college_name": college.name,
        "college_code": college.code,
        "status": display_status,
        "status_label": status_label,
        "registration_status": college.registration_status,
        "submitted_at": college.created_at.isoformat() if college.created_at else None,
        "official_website": college.official_website,
        "contact_person": college.contact_person,
        "contact_email": college.contact_email,
        "rejection_reason": college.rejection_reason,
        "review_notes": college.review_notes,
    }


@router.get("/list-public", summary="List Active Colleges (Public)")
def list_active_colleges(db: Session = Depends(get_db)):
    """Returns all active colleges for public selector / directories."""
    colleges = db.query(College).filter(College.status == "ACTIVE").order_by(College.name.asc()).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "code": c.code,
            "slug": c.slug,
            "logo_url": c.logo_url,
            "official_website": c.official_website,
            "assistant_name": c.assistant_name or "AI Assistant",
        }
        for c in colleges
    ]


@router.get("/public/{slug_or_code}", summary="Get Public College Profile")
def get_public_college(slug_or_code: str, db: Session = Depends(get_db)):
    """Returns branding and public metadata for a college."""
    param = slug_or_code.strip()
    college = db.query(College).filter(
        (func.lower(College.slug) == param.lower()) |
        (func.upper(College.code) == param.upper())
    ).first()

    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    return {
        "id": college.id,
        "name": college.name,
        "code": college.code,
        "slug": college.slug,
        "status": college.status,
        "official_website": college.official_website,
        "logo_url": college.logo_url,
        "assistant_name": college.assistant_name or "AI Assistant",
        "welcome_message": college.welcome_message,
        "primary_color": college.primary_color or "#0b0a3e",
        "secondary_color": college.secondary_color or "#1a2345",
        "accent_color": college.accent_color or "#f08518",
        "supported_languages": college.supported_languages or ["en", "gu", "hi"],
    }
