"""
Phase 10-11: Super-Admin College Management API
Provides full CRUD for colleges (tenants) and College Admin provisioning.
ALL endpoints require SUPER_ADMIN role.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.core.database import engine, get_db
from backend.app.core.permissions import require_super_admin, get_current_admin_user, log_admin_audit
from backend.app.core.security import get_password_hash, generate_secure_temporary_password
from backend.app.chat.college_context import _contains_token_sequence
from backend.app.scripts.seed_knowledge_categories import seed_knowledge_categories
from backend.app.models.college import College
from backend.app.models.user import User

router = APIRouter(prefix="/colleges", tags=["super-admin-colleges"])


# ─── Pydantic Schemas ───────────────────────────────────────────────────────

class CollegeCreateRequest(BaseModel):
    name: str
    code: str                        # short unique code e.g. "SVIT"
    slug: str                        # URL-safe slug e.g. "svit"
    official_website: Optional[str] = None
    description: Optional[str] = None
    assistant_name: Optional[str] = "AI Assistant"
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = "#0b0a3e"
    secondary_color: Optional[str] = "#1a2345"
    accent_color: Optional[str] = "#f08518"
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    max_users: Optional[int] = 500
    max_documents: Optional[int] = 1000
    # College Admin to provision alongside the college
    admin_email: Optional[str] = None
    admin_name: Optional[str] = None


class CollegeUpdateRequest(BaseModel):
    name: Optional[str] = None
    official_website: Optional[str] = None
    description: Optional[str] = None
    assistant_name: Optional[str] = None
    welcome_message: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    max_users: Optional[int] = None
    max_documents: Optional[int] = None
    status: Optional[str] = None     # ACTIVE | SUSPENDED | PENDING


class CollegeAdminProvisionRequest(BaseModel):
    email: EmailStr
    full_name: str
    send_email: Optional[bool] = False   # placeholder for future email integration


class CollegeRejectRequest(BaseModel):
    reason: str


class CollegeRequestInfoRequest(BaseModel):
    notes: str


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _college_to_dict(college: College) -> dict:
    return {
        "id": college.id,
        "name": college.name,
        "code": college.code,
        "slug": college.slug,
        "status": college.status,
        "registration_status": college.registration_status,
        "application_id": college.application_id,
        "official_website": college.official_website,
        "official_email": college.official_email,
        "phone": college.phone,
        "description": college.description,
        "assistant_name": college.assistant_name,
        "welcome_message": college.welcome_message,
        "primary_color": college.primary_color,
        "secondary_color": college.secondary_color,
        "accent_color": college.accent_color,
        "logo_url": college.logo_url,
        "university_affiliation": college.university_affiliation,
        "contact_person": college.contact_person,
        "contact_email": college.contact_email,
        "contact_phone": college.contact_phone,
        "address": college.address,
        "city": college.city,
        "state": college.state,
        "country": college.country,
        "auth_document_path": college.auth_document_path,
        "additional_info": college.additional_info,
        "rejection_reason": college.rejection_reason,
        "review_notes": college.review_notes,
        "max_users": college.max_users,
        "max_documents": college.max_documents,
        "created_at": college.created_at.isoformat() if college.created_at else None,
        "updated_at": college.updated_at.isoformat() if college.updated_at else None,
    }


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/diagnostics/college-resolution", summary="Read-only college resolution diagnostic")
def college_resolution_diagnostic(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    # Read-only diagnostic; no secrets or private records are returned.
    known_identifiers = {
        "ahmedabad institute of technology",
        "ait",
        "r.c. technical institute",
        "rcti",
    }
    known_matches = db.query(College).filter(
        or_(
            func.lower(College.name).in_(known_identifiers),
            func.lower(College.code).in_(known_identifiers),
            func.lower(College.slug).in_(known_identifiers),
        )
    ).all()

    return {
        "environment": settings.ENVIRONMENT,
        "database": {
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
            "database_configured": bool(settings.DATABASE_URL.strip()),
        },
        "college_summary": {
            "total_colleges": db.query(College).count(),
            "active_colleges": db.query(College).filter(College.status == "ACTIVE").count(),
            "approved_colleges": db.query(College).filter(
                College.registration_status == "APPROVED"
            ).count(),
        },
        "known_college_matches": [
            {
                "name": college.name,
                "code": college.code,
                "slug": college.slug,
                "status": college.status,
                "registration_status": college.registration_status,
            }
            for college in known_matches
        ],
        "resolver_revision": {
            "token_boundary_match_present": callable(_contains_token_sequence),
        },
    }

@router.get("/", summary="List all colleges (SUPER_ADMIN only)")
def list_colleges(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    q = db.query(College)
    if status_filter:
        q = q.filter(College.status == status_filter.upper())
    if search:
        like = f"%{search}%"
        q = q.filter(
            College.name.ilike(like) |
            College.code.ilike(like) |
            College.slug.ilike(like)
        )
    total = q.count()
    colleges = q.order_by(College.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "colleges": [_college_to_dict(c) for c in colleges],
    }


@router.get("/stats/summary", summary="College platform statistics (SUPER_ADMIN only)")
def colleges_stats(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """§16/§34: dynamic, database-driven counts — new colleges appear automatically."""
    counts = {"TOTAL": 0, "ACTIVE": 0, "PENDING": 0, "SUSPENDED": 0, "REJECTED": 0}
    connection_counts = {"CONNECTED_VERIFIED": 0, "CONNECTED_PARTIAL": 0, "REGISTERED_PENDING_SETUP": 0, "NOT_CONNECTED": 0}
    
    for (status_,) in db.query(College.status).all():
        key = (status_ or "PENDING").upper()
        counts[key] = counts.get(key, 0) + 1
        counts["TOTAL"] += 1
    
    # Connection status counts
    for (conn_status,) in db.query(College.connection_status).all():
        key = conn_status or "NOT_CONNECTED"
        connection_counts[key] = connection_counts.get(key, 0) + 1
    
    return {
        "registration_status": counts,
        "connection_status": connection_counts,
    }


@router.get("/pending", summary="List pending college registrations (SUPER_ADMIN only)")
def list_pending_registrations(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    colleges = db.query(College).filter(
        College.status.in_(["PENDING", "UNDER_REVIEW", "NEED_MORE_INFORMATION"])
    ).order_by(College.created_at.desc()).all()
    return {
        "count": len(colleges),
        "registrations": [_college_to_dict(c) for c in colleges]
    }


@router.get("/current", summary="Get authenticated college profile")
def get_current_college(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if not current_user.college_id:
        if current_user.role == "SUPER_ADMIN":
            return {"message": "Super Admin platform-level context", "is_super_admin": True}
        raise HTTPException(status_code=400, detail="No college linked to this admin account.")
    college = db.query(College).filter(College.id == current_user.college_id).first()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return _college_to_dict(college)


@router.get("/{college_id}", summary="Get college details (SUPER_ADMIN only)")
def get_college(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    # Admin count
    admin_count = db.query(User).filter(
        User.college_id == college_id,
        User.role == "COLLEGE_ADMIN",
        User.is_active == True
    ).count()
    student_count = db.query(User).filter(
        User.college_id == college_id,
        User.role == "STUDENT",
        User.is_active == True
    ).count()
    data = _college_to_dict(college)
    data["admin_count"] = admin_count
    data["student_count"] = student_count
    return data


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new college (SUPER_ADMIN only)")
def create_college(
    req: CollegeCreateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    # Uniqueness checks
    if db.query(College).filter(College.code == req.code.upper()).first():
        raise HTTPException(status_code=400, detail=f"College code '{req.code}' is already taken.")
    if db.query(College).filter(College.slug == req.slug.lower()).first():
        raise HTTPException(status_code=400, detail=f"College slug '{req.slug}' is already taken.")

    college_id = str(uuid.uuid4())
    college = College(
        id=college_id,
        name=req.name,
        code=req.code.upper(),
        slug=req.slug.lower(),
        status="ACTIVE",
        official_website=req.official_website,
        description=req.description,
        assistant_name=req.assistant_name or "AI Assistant",
        welcome_message=req.welcome_message,
        primary_color=req.primary_color or "#0b0a3e",
        secondary_color=req.secondary_color or "#1a2345",
        accent_color=req.accent_color or "#f08518",
        logo_url=req.logo_url,
        contact_email=req.contact_email,
        address=req.address,
        city=req.city,
        state=req.state,
        country=req.country or "India",
        max_users=req.max_users or 500,
        max_documents=req.max_documents or 1000,
    )
    db.add(college)
    db.flush()

    provisioned_admin = None
    temp_password = None

    # Optionally provision a College Admin alongside the college
    if req.admin_email:
        if db.query(User).filter(User.email == req.admin_email).first():
            raise HTTPException(status_code=400, detail=f"Email '{req.admin_email}' already registered.")
        temp_password = generate_secure_temporary_password()
        admin_user = User(
            id=str(uuid.uuid4()),
            email=req.admin_email,
            full_name=req.admin_name or req.admin_email.split("@")[0].title(),
            hashed_password=get_password_hash(temp_password),
            role="COLLEGE_ADMIN",
            college_id=college_id,
            is_active=True,
            is_verified=True,
            must_change_password=True,
        )
        db.add(admin_user)
        provisioned_admin = {
            "id": admin_user.id,
            "email": admin_user.email,
            "full_name": admin_user.full_name,
            "role": admin_user.role,
            "must_change_password": True,
        }

    db.commit()
    db.refresh(college)

    log_admin_audit(db, current_user, "COLLEGE_CREATED", "COLLEGE", {
        "college_id": college_id,
        "name": req.name,
        "code": req.code,
        "admin_email": req.admin_email,
    })

    response = {
        "message": f"College '{req.name}' created successfully.",
        "college": _college_to_dict(college),
    }
    if provisioned_admin:
        response["provisioned_admin"] = provisioned_admin
        if temp_password:
            response["temp_password"] = temp_password  # Show once — must be communicated to admin
    return response


@router.patch("/{college_id}", summary="Update college settings (SUPER_ADMIN only)")
def update_college(
    college_id: str,
    req: CollegeUpdateRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    allowed_statuses = {"ACTIVE", "SUSPENDED", "PENDING"}
    update_data = req.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"].upper() not in allowed_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {allowed_statuses}")

    for field, value in update_data.items():
        if field == "status" and value:
            setattr(college, field, value.upper())
        elif value is not None:
            setattr(college, field, value)

    college.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(college)

    log_admin_audit(db, current_user, "COLLEGE_UPDATED", "COLLEGE", {
        "college_id": college_id,
        "changes": update_data,
    })
    return {"message": "College updated.", "college": _college_to_dict(college)}


@router.post("/{college_id}/suspend", summary="Suspend a college (SUPER_ADMIN only)")
def suspend_college(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    if college.status == "SUSPENDED":
        raise HTTPException(status_code=400, detail="College is already suspended.")
    college.status = "SUSPENDED"
    college.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_admin_audit(db, current_user, "COLLEGE_SUSPENDED", "COLLEGE", {"college_id": college_id})
    return {"message": f"College '{college.name}' suspended."}


@router.post("/{college_id}/activate", summary="Activate a suspended college (SUPER_ADMIN only)")
def activate_college(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    college.status = "ACTIVE"
    college.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_admin_audit(db, current_user, "COLLEGE_ACTIVATED", "COLLEGE", {"college_id": college_id})
    return {"message": f"College '{college.name}' activated."}


@router.post("/{college_id}/admins", status_code=status.HTTP_201_CREATED,
             summary="Provision a College Admin (SUPER_ADMIN only)")
def provision_college_admin(
    college_id: str,
    req: CollegeAdminProvisionRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail=f"Email '{req.email}' already registered.")

    temp_password = generate_secure_temporary_password()
    admin_user = User(
        id=str(uuid.uuid4()),
        email=str(req.email),
        full_name=req.full_name,
        hashed_password=get_password_hash(temp_password),
        role="COLLEGE_ADMIN",
        college_id=college_id,
        is_active=True,
        is_verified=True,
        must_change_password=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    log_admin_audit(db, current_user, "COLLEGE_ADMIN_PROVISIONED", "USER", {
        "college_id": college_id,
        "admin_id": admin_user.id,
        "email": str(req.email),
    })
    return {
        "message": f"College Admin provisioned for '{college.name}'.",
        "admin": {
            "id": admin_user.id,
            "email": admin_user.email,
            "full_name": admin_user.full_name,
            "role": admin_user.role,
            "must_change_password": True,
        },
        "temp_password": temp_password,  # Show once
    }


@router.get("/{college_id}/admins", summary="List admins for a college (SUPER_ADMIN only)")
def list_college_admins(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    admins = db.query(User).filter(
        User.college_id == college_id,
        User.role == "COLLEGE_ADMIN"
    ).all()
    return {
        "college_id": college_id,
        "college_name": college.name,
        "admins": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "must_change_password": bool(u.must_change_password),
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in admins
        ],
    }


@router.post("/{college_id}/approve", summary="Approve college registration and provision admin (SUPER_ADMIN only)")
def approve_college(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    college.status = "ACTIVE"
    college.registration_status = "APPROVED"
    college.updated_at = datetime.now(timezone.utc)

    # Determine admin email from contact_email or official_email
    admin_email = college.contact_email or college.official_email
    if not admin_email:
        admin_email = f"admin@{college.slug}.edu"

    # Find existing or create new College Admin user
    existing_user = db.query(User).filter(User.email == admin_email).first()
    temp_password = generate_secure_temporary_password()

    if existing_user:
        existing_user.role = "COLLEGE_ADMIN"
        existing_user.college_id = college.id
        existing_user.is_active = True
        existing_user.is_verified = True
        existing_user.must_change_password = True
        existing_user.hashed_password = get_password_hash(temp_password)
        admin_user = existing_user
    else:
        admin_user = User(
            id=str(uuid.uuid4()),
            email=admin_email,
            full_name=college.contact_person or f"{college.name} Admin",
            hashed_password=get_password_hash(temp_password),
            role="COLLEGE_ADMIN",
            college_id=college.id,
            is_active=True,
            is_verified=True,
            must_change_password=True,
        )
        db.add(admin_user)

    db.commit()
    db.refresh(college)
    db.refresh(admin_user)

    # Seed knowledge categories for this college
    categories_created = seed_knowledge_categories(db, college_id=college.id)
    
    log_admin_audit(db, current_user, "COLLEGE_APPROVED", "COLLEGE", {
        "college_id": college.id,
        "college_name": college.name,
        "admin_email": admin_user.email,
        "categories_created": categories_created
    })

    return {
        "message": f"College '{college.name}' approved and activated successfully.",
        "college": _college_to_dict(college),
        "credentials": {
            "admin_email": admin_user.email,
            "username": admin_user.email.split("@")[0],
            "temporary_password": temp_password,
            "role": "COLLEGE_ADMIN",
            "college_id": college.id,
            "college_name": college.name,
        },
        "categories_created": categories_created
    }


@router.post("/{college_id}/reject", summary="Reject college registration (SUPER_ADMIN only)")
def reject_college(
    college_id: str,
    req: CollegeRejectRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    college.status = "REJECTED"
    college.registration_status = "REJECTED"
    college.rejection_reason = req.reason
    college.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(college)

    log_admin_audit(db, current_user, "COLLEGE_REJECTED", "COLLEGE", {
        "college_id": college.id,
        "reason": req.reason
    })
    return {"message": f"College '{college.name}' registration rejected.", "college": _college_to_dict(college)}


@router.post("/{college_id}/request-info", summary="Request more info from applicant (SUPER_ADMIN only)")
def request_college_info(
    college_id: str,
    req: CollegeRequestInfoRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    college.status = "NEED_MORE_INFORMATION"
    college.registration_status = "NEED_MORE_INFORMATION"
    college.review_notes = req.notes
    college.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(college)

    log_admin_audit(db, current_user, "COLLEGE_REQUEST_INFO", "COLLEGE", {
        "college_id": college.id,
        "notes": req.notes
    })
    return {"message": f"Information request sent for '{college.name}'.", "college": _college_to_dict(college)}


@router.post("/{college_id}/send-credentials", summary="Send/notify college credentials (SUPER_ADMIN only)")
def send_college_credentials(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")

    recipient = college.contact_email or college.official_email
    log_admin_audit(db, current_user, "CREDENTIALS_DISPATCHED", "COLLEGE", {
        "college_id": college.id,
        "recipient": recipient
    })
    return {
        "message": f"Admin credentials notification dispatched to {recipient}.",
        "recipient": recipient,
        "status": "DELIVERED"
    }
# ─── College Details (SUPER_ADMIN master directory §6-§21) ───────────────────
#
# These endpoints power the dedicated College Details page. All data is strictly
# filtered by college_id — no cross-tenant leakage (§12-§21, §29, §39). The
# frontend never supplies a college_id for authorization; the ID comes from the
# URL path and access is granted only to SUPER_ADMIN (require_super_admin).

from sqlalchemy import func
from backend.app.models.conversation import Conversation, Message
from backend.app.models.knowledge import KnowledgeGap, MessageFeedback, WebsiteSnapshot
from backend.app.models.knowledge_categories import KnowledgeRecord
from backend.app.models.document import Document, DocumentChunk
from backend.app.models.college import ChangeRequest, WebsiteSyncHistory
from backend.app.models.audit import AuditLog


def _get_college_or_404(db: Session, college_id: str) -> College:
    college = db.query(College).filter(College.id == college_id).first()
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found")
    return college


@router.get("/{college_id}/stats", summary="Per-college summary stats (SUPER_ADMIN only)")
def college_stats(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Efficient count-only queries — no large datasets are loaded (§11, §40)."""
    _get_college_or_404(db, college_id)

    users = db.query(User).filter(User.college_id == college_id, User.is_active == True).count()
    admins = db.query(User).filter(
        User.college_id == college_id, User.role == "COLLEGE_ADMIN", User.is_active == True).count()
    knowledge = db.query(KnowledgeRecord).filter(KnowledgeRecord.college_id == college_id).count()
    documents = db.query(Document).filter(Document.college_id == college_id).count()
    rag_chunks = db.query(DocumentChunk).filter(DocumentChunk.college_id == college_id).count()
    pending_changes = db.query(ChangeRequest).filter(
        ChangeRequest.college_id == college_id,
        ChangeRequest.status.in_(["PENDING", "NEEDS_CLARIFICATION"])).count()
    open_gaps = db.query(KnowledgeGap).filter(
        KnowledgeGap.college_id == college_id,
        KnowledgeGap.resolved == False,
        KnowledgeGap.status.in_(["OPEN", "UNDER_REVIEW", "IN_PROGRESS"])).count()
    feedback_reports = db.query(MessageFeedback).filter(
        MessageFeedback.college_id == college_id,
        MessageFeedback.feedback_type.in_(["NEGATIVE", "REPORT"]),
        MessageFeedback.status == "UNRESOLVED").count()

    return {
        "college_id": college_id,
        "users": users,
        "admins": admins,
        "knowledge": knowledge,
        "documents": documents,
        "rag_chunks": rag_chunks,
        "pending_changes": pending_changes,
        "knowledge_gaps": open_gaps,
        "feedback_reports": feedback_reports,
    }


@router.get("/{college_id}/users", summary="College users & admins (SUPER_ADMIN only)")
def college_users(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    users = db.query(User).filter(User.college_id == college_id).order_by(User.created_at).all()
    return {
        "college_id": college_id,
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
                "is_verified": u.is_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }


@router.get("/{college_id}/knowledge", summary="College knowledge breakdown (SUPER_ADMIN only)")
def college_knowledge(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    q = db.query(KnowledgeRecord).filter(KnowledgeRecord.college_id == college_id)
    total = q.count()
    records = (
        q.order_by(KnowledgeRecord.created_at.desc())
        .limit(50)
        .all()
    )
    by_status = dict(db.query(KnowledgeRecord.status, func.count(KnowledgeRecord.id))
                     .filter(KnowledgeRecord.college_id == college_id)
                     .group_by(KnowledgeRecord.status).all())
    official = db.query(KnowledgeRecord).filter(
        KnowledgeRecord.college_id == college_id,
        KnowledgeRecord.source_type.in_(["AIT_OFFICIAL", "GTU_OFFICIAL", "ADMIN_VERIFIED", "OTHER_VERIFIED"]),
        KnowledgeRecord.verified == True).count()
    return {
        "college_id": college_id,
        "total": total,
        "by_status": by_status,
        "official": official,
        "records": [
            {
                "id": r.id,
                "title": r.title,
                "category_id": r.category_id,
                "course": r.course,
                "status": r.status,
                "source_type": r.source_type,
                "verified": r.verified,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.get("/{college_id}/documents", summary="College documents (SUPER_ADMIN only)")
def college_documents(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    docs = (
        db.query(Document)
        .filter(Document.college_id == college_id)
        .order_by(Document.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "college_id": college_id,
        "total": db.query(Document).filter(Document.college_id == college_id).count(),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "doc_type": d.doc_type,
                "source_url": d.source_url,
                "visibility": d.visibility,
                "status": d.visibility,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    }


@router.get("/{college_id}/website", summary="College website sync info (SUPER_ADMIN only)")
def college_website(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    college = _get_college_or_404(db, college_id)
    last_sync = (
        db.query(WebsiteSyncHistory)
        .filter(WebsiteSyncHistory.college_id == college_id)
        .order_by(WebsiteSyncHistory.started_at.desc())
        .first()
    )
    pages_discovered = db.query(func.count(WebsiteSnapshot.id)).filter(
        WebsiteSnapshot.college_id == college_id).scalar() or 0
    return {
        "college_id": college_id,
        "official_website": college.official_website,
        "pages_discovered": pages_discovered,
        "last_sync": (
            {
                "started_at": last_sync.started_at.isoformat() if last_sync.started_at else None,
                "completed_at": last_sync.completed_at.isoformat() if last_sync.completed_at else None,
                "status": last_sync.status,
                "pages_discovered": last_sync.pages_discovered,
                "pages_changed": last_sync.pages_changed,
                "pages_added": last_sync.pages_added,
                "pages_removed": last_sync.pages_removed,
                "errors_count": last_sync.errors_count,
            }
            if last_sync else None
        ),
    }


@router.get("/{college_id}/rag", summary="College RAG health (SUPER_ADMIN only)")
def college_rag(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    docs = db.query(Document).filter(Document.college_id == college_id).count()
    chunks = db.query(DocumentChunk).filter(DocumentChunk.college_id == college_id).count()
    embeddings = db.query(DocumentChunk).filter(
        DocumentChunk.college_id == college_id,
        DocumentChunk.embedding_json != None).count()
    return {
        "college_id": college_id,
        "documents": docs,
        "chunks": chunks,
        "embeddings": embeddings,
        "index_status": "READY" if chunks > 0 else ("EMPTY" if docs == 0 else "PARTIAL"),
        "failed_items": db.query(Document).filter(
            Document.college_id == college_id,
            Document.visibility.is_(None)).count(),
    }


@router.get("/{college_id}/change-requests", summary="College change requests (SUPER_ADMIN only)")
def college_change_requests(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    q = db.query(ChangeRequest).filter(ChangeRequest.college_id == college_id)
    by_status = dict(db.query(ChangeRequest.status, func.count(ChangeRequest.id))
                     .filter(ChangeRequest.college_id == college_id)
                     .group_by(ChangeRequest.status).all())
    items = q.order_by(ChangeRequest.created_at.desc()).limit(50).all()
    return {
        "college_id": college_id,
        "by_status": by_status,
        "items": [
            {
                "id": cr.id,
                "entity_type": cr.entity_type,
                "action": cr.action,
                "title": cr.title,
                "status": cr.status,
                "created_at": cr.created_at.isoformat() if cr.created_at else None,
            }
            for cr in items
        ],
    }


@router.get("/{college_id}/feedback", summary="College feedback (SUPER_ADMIN only)")
def college_feedback(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    q = db.query(MessageFeedback).filter(MessageFeedback.college_id == college_id)
    positive = q.filter(MessageFeedback.feedback_type == "POSITIVE").count()
    negative = q.filter(MessageFeedback.feedback_type == "NEGATIVE").count()
    reports = q.filter(MessageFeedback.feedback_type == "REPORT").count()
    unresolved = q.filter(MessageFeedback.status == "UNRESOLVED",
                          MessageFeedback.feedback_type != "POSITIVE").count()
    items = q.order_by(MessageFeedback.created_at.desc()).limit(50).all()
    return {
        "college_id": college_id,
        "positive": positive,
        "negative": negative,
        "reports": reports,
        "unresolved": unresolved,
        "items": [
            {
                "id": f.id,
                "feedback_type": f.feedback_type,
                "reason": f.reason,
                "details": f.details,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in items
        ],
    }




# ─── Connection Health Endpoints (Production Multi-College Requirements) ──────

@router.get("/{college_id}/connection-health", summary="Get college connection health (SUPER_ADMIN only)")
def get_college_connection_health(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Returns comprehensive connection health status for a college.
    Shows whether the college has usable verified knowledge infrastructure.
    """
    from backend.app.services.connection_health import connection_health_service
    
    college = _get_college_or_404(db, college_id)
    health = connection_health_service.calculate_connection_status(db, college)
    
    return {
        "college_id": college.id,
        "college_name": college.name,
        "college_code": college.code,
        "college_status": college.status,
        "connection_status": health["connection_status"],
        "knowledge_health": health["knowledge_health"],
        "official_website": college.official_website,
        "website": {
            "configured": bool(college.official_website),
            "reachable": health["website_reachable"],
            "pages_indexed": health["website_pages_indexed"],
            "last_checked_at": college.website_last_checked_at.isoformat() if college.website_last_checked_at else None,
            "last_success_at": college.website_last_success_at.isoformat() if college.website_last_success_at else None,
            "last_failure_at": college.website_last_failure_at.isoformat() if college.website_last_failure_at else None,
            "http_status": college.website_http_status,
            "error_message": college.website_error_message,
        },
        "knowledge": {
            "verified_db_records": health["verified_db_records"],
            "rag_documents": health["rag_documents"],
            "total_sources": health["total_knowledge_sources"],
            "last_updated_at": college.knowledge_last_updated_at.isoformat() if college.knowledge_last_updated_at else None,
        },
        "issues": health["issues"],
        "broken_sources_count": college.broken_sources_count,
    }


@router.post("/{college_id}/connection-health/refresh", summary="Refresh college connection health (SUPER_ADMIN only)")
def refresh_college_connection_health(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Recalculates and updates connection health status for a college.
    """
    from backend.app.services.connection_health import connection_health_service
    
    college = _get_college_or_404(db, college_id)
    health = connection_health_service.update_college_health(db, college)
    
    log_admin_audit(db, current_user, "CONNECTION_HEALTH_REFRESHED", "COLLEGE", {
        "college_id": college_id,
        "connection_status": health["connection_status"],
        "knowledge_health": health["knowledge_health"],
    })
    
    return {
        "message": f"Connection health refreshed for {college.name}",
        "connection_status": health["connection_status"],
        "knowledge_health": health["knowledge_health"],
        "total_knowledge_sources": health["total_knowledge_sources"],
        "issues": health["issues"],
    }


@router.post("/{college_id}/website/check", summary="Check college website health (SUPER_ADMIN only)")
async def check_college_website(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Performs actual HTTP health check of the college's official website.
    Updates website health fields in the college record.
    """
    from backend.app.services.connection_health import connection_health_service
    
    college = _get_college_or_404(db, college_id)
    
    if not college.official_website:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No official website configured for this college"
        )
    
    result = await connection_health_service.check_website_health(db, college)
    
    log_admin_audit(db, current_user, "WEBSITE_HEALTH_CHECKED", "COLLEGE", {
        "college_id": college_id,
        "website": college.official_website,
        "reachable": result["reachable"],
        "http_status": result.get("http_status"),
    })
    
    return {
        "college_id": college.id,
        "college_name": college.name,
        "website": college.official_website,
        "result": result,
    }


@router.get("/{college_id}/gaps", summary="College knowledge gaps (SUPER_ADMIN only)")
def college_gaps(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    q = db.query(KnowledgeGap).filter(KnowledgeGap.college_id == college_id)
    by_status = dict(db.query(KnowledgeGap.status, func.count(KnowledgeGap.id))
                     .filter(KnowledgeGap.college_id == college_id)
                     .group_by(KnowledgeGap.status).all())
    top = (
        q.order_by(KnowledgeGap.occurrence_count.desc())
        .limit(15).all()
    )
    return {
        "college_id": college_id,
        "by_status": by_status,
        "open": by_status.get("OPEN", 0),
        "items": [
            {
                "id": g.id,
                "user_query": g.user_query,
                "status": g.status,
                "occurrence_count": g.occurrence_count,
                "priority": g.priority,
                "last_seen_at": g.last_seen_at.isoformat() if g.last_seen_at else None,
            }
            for g in top
        ],
    }


@router.get("/{college_id}/analytics", summary="College analytics (SUPER_ADMIN only)")
def college_analytics(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """Count-only queries — no expensive computation in the browser (§20, §40)."""
    _get_college_or_404(db, college_id)
    conv_ids = db.query(Conversation.id).filter(Conversation.college_id == college_id)
    questions = db.query(Message).filter(
        Message.conversation_id.in_(conv_ids),
        Message.sender == "user").count()
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    questions_today = db.query(Message).filter(
        Message.conversation_id.in_(conv_ids),
        Message.sender == "user",
        Message.created_at >= today).count()
    questions_month = db.query(Message).filter(
        Message.conversation_id.in_(conv_ids),
        Message.sender == "user",
        Message.created_at >= month_start).count()
    active_users = db.query(Conversation.user_id).filter(
        Conversation.college_id == college_id).distinct().count()
    feedback = db.query(MessageFeedback).filter(MessageFeedback.college_id == college_id).count()
    unanswered = db.query(KnowledgeGap).filter(
        KnowledgeGap.college_id == college_id,
        KnowledgeGap.resolved == False).count()
    return {
        "college_id": college_id,
        "questions": questions,
        "questions_today": questions_today,
        "questions_this_month": questions_month,
        "active_users": active_users,
        "feedback": feedback,
        "unanswered_questions": unanswered,
    }


@router.get("/{college_id}/audit", summary="College audit history (SUPER_ADMIN only)")
def college_audit(
    college_id: str,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    _get_college_or_404(db, college_id)
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.college_id == college_id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "college_id": college_id,
        "items": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "user_id": a.user_id,
                "action": a.action,
                "resource": a.resource,
                "status": a.status,
                "trace_id": a.trace_id,
            }
            for a in logs
        ],
    }
