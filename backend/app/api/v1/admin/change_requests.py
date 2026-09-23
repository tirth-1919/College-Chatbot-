"""
Change Request Workflow API (Multi-tenant).

COLLEGE_ADMIN creates change requests for protected data (fees, faculty, courses...).
SUPER_ADMIN approves / rejects / requests clarification. Only on approval is the
production data changed — transactionally, with audit logging and notifications.

college_id is ALWAYS derived from the authenticated user's session — never from
the client (query params, body, or path are ignored for tenancy).
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, log_admin_audit
from backend.app.models.college import ChangeRequest, Notification
from backend.app.models.knowledge import AitEntity
from backend.app.models.user import User

router = APIRouter(prefix="/change-requests", tags=["Change Requests"])

VALID_ENTITY_TYPES = {"FEES", "FACULTY", "COURSES", "DEPARTMENT", "CALENDAR", "EVENT", "KNOWLEDGE"}
VALID_ACTIONS = {"CREATE", "UPDATE", "DELETE"}
ACTIONABLE_STATUSES = {"PENDING", "NEEDS_CLARIFICATION"}


class ChangeRequestCreate(BaseModel):
    entity_type: str
    entity_id: Optional[str] = None
    action: str
    title: Optional[str] = None
    reason: Optional[str] = None
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None

    @field_validator("entity_type")
    @classmethod
    def _vt(cls, v):
        v = (v or "").upper()
        if v not in VALID_ENTITY_TYPES:
            raise ValueError(f"entity_type must be one of {sorted(VALID_ENTITY_TYPES)}")
        return v

    @field_validator("action")
    @classmethod
    def _va(cls, v):
        v = (v or "").upper()
        if v not in VALID_ACTIONS:
            raise ValueError("action must be CREATE, UPDATE or DELETE")
        return v


class ReviewRequest(BaseModel):
    notes: Optional[str] = None


class ClarificationRespondRequest(BaseModel):
    response: str


# ── helpers ──────────────

def _notify(db: Session, college_id: Optional[str], user_id: Optional[str],
            title: str, message: str, ntype: str = "INFO"):
    db.add(Notification(college_id=college_id, user_id=user_id,
                        title=title, message=message, type=ntype))


def _notify_super_admins(db: Session, title: str, message: str, college_id: Optional[str] = None):
    supers = db.query(User).filter(User.role == "SUPER_ADMIN", User.is_active == True).all()
    for s in supers:
        _notify(db, college_id, s.id, title, message, "WARNING")


def _current_value(entity, key: str):
    """Read a field from the entity — model column first, then the JSON details blob."""
    if hasattr(entity, key):
        return getattr(entity, key, None)
    return (entity.details or {}).get(key) if getattr(entity, "details", None) else None


def _check_stale(cr: ChangeRequest, entity) -> Optional[str]:
    """Detect whether the record changed after the request was created."""
    if not entity or not cr.old_value:
        return None
    for k, v in cr.old_value.items():
        current = _current_value(entity, k)
        if current is not None and str(current) != str(v):
            return (f"This request is based on an outdated value. The record has changed "
                    f"since the request was created (field '{k}' is now '{current}', "
                    f"requested against '{v}'). Please review the current record and "
                    f"submit a fresh change request if still needed.")
    return None


def _apply_change(db: Session, cr: ChangeRequest) -> ChangeRequest:
    """Transactional apply. Rolls back and marks FAILED on error."""
    try:
        entity = None
        if cr.entity_id:
            entity = db.query(AitEntity).filter(
                AitEntity.id == cr.entity_id, AitEntity.college_id == cr.college_id
            ).first()

        if cr.action == "UPDATE":
            if not entity:
                raise ValueError("Target record no longer exists")
            stale = _check_stale(cr, entity)
            if stale:
                raise ValueError(stale)
            if not cr.new_value:
                raise ValueError("No new value provided in request")
            for k, v in cr.new_value.items():
                if k in ("id", "college_id"):
                    continue  # never allow tenant/identity overwrite
                if hasattr(entity, k) and k != "details":
                    setattr(entity, k, v)
                else:
                    # JSON payload fields (fee, title, ...) live in entity.details.
                    # Reassign the dict (and flag it) — in-place mutation is not tracked
                    # by SQLAlchemy and the change would silently never persist.
                    merged = dict(entity.details) if isinstance(entity.details, dict) else {}
                    merged[k] = v
                    entity.details = merged
                    flag_modified(entity, "details")
        elif cr.action == "DELETE":
            if not entity:
                raise ValueError("Target record no longer exists")
            stale = _check_stale(cr, entity)
            if stale:
                raise ValueError(stale)
            # Soft-delete where supported, physical delete otherwise
            if hasattr(entity, "is_active"):
                entity.is_active = False
            elif hasattr(entity, "verified"):
                entity.verified = False
            else:
                db.delete(entity)
        # CREATE: proposed new_value is stored for SUPER_ADMIN materialisation; marked APPLIED.

        cr.status = "APPLIED"
        db.commit()
        db.refresh(cr)
        return cr
    except ValueError as ve:
        db.rollback()
        cr.status = "FAILED"
        cr.review_notes = str(ve)
        db.commit()
        db.refresh(cr)
        log_admin_audit(db, None, "CHANGE_REQUEST_FAILED", "CHANGE_REQUEST",
                        {"change_request_id": cr.id, "reason": str(ve)},
                        college_id=cr.college_id)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))
    except Exception:
        db.rollback()
        cr.status = "FAILED"
        db.commit()
        db.refresh(cr)
        log_admin_audit(db, None, "CHANGE_REQUEST_FAILED", "CHANGE_REQUEST",
                        {"change_request_id": cr.id, "reason": "internal error"},
                        college_id=cr.college_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="The change could not be applied due to an internal error. "
                                   "The request has been marked FAILED. Please contact the platform administrator.")


def _get_request_scoped(request_id: str, current_user: User, db: Session) -> ChangeRequest:
    """Load a change request with server-side tenancy enforcement."""
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if not is_super:
        if not current_user.college_id or cr.college_id != current_user.college_id:
            # Do not reveal existence of other colleges' requests
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    return cr


# ── endpoints (College Admin + Super Admin shared) ─────────────

@router.get("/", summary="List change requests (tenant-scoped, paginated)")
def list_change_requests(
    status_filter: Optional[str] = Query(None, alias="status_filter"),
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import or_
    q = db.query(ChangeRequest)
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"

    # Tenant filtering derived from authenticated user only
    if not is_super:
        if not current_user.college_id:
            return {"items": [], "total": 0, "page": page, "per_page": per_page}
        q = q.filter(ChangeRequest.college_id == current_user.college_id)

    if status_filter and status_filter.upper() != "ALL":
        q = q.filter(ChangeRequest.status == status_filter.upper())
    if entity_type:
        q = q.filter(ChangeRequest.entity_type == entity_type.upper())
    if action:
        q = q.filter(ChangeRequest.action == action.upper())
    if search:
        like = f"%{search.lower()}%"
        q = q.filter(or_(
            ChangeRequest.title.ilike(like),
            ChangeRequest.reason.ilike(like),
            ChangeRequest.entity_type.ilike(like),
        ))

    total = q.count()
    rows = (q.order_by(ChangeRequest.created_at.desc())
             .offset((page - 1) * per_page).limit(per_page).all())
    return {"items": [r.to_dict() for r in rows], "total": total, "page": page, "per_page": per_page}


@router.get("/{request_id}", summary="Get change request detail (tenant-scoped)")
def get_change_request(
    request_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return _get_request_scoped(request_id, current_user, db).to_dict()


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a change request (College Admin)")
def create_change_request(
    req: ChangeRequestCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    role = (current_user.role or "").upper()
    if role not in ("COLLEGE_ADMIN", "SUPER_ADMIN"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only College Admins can submit this request.")
    if not current_user.college_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Account is not linked to a college tenant.")

    # Verify target entity belongs to this college
    if req.entity_id:
        entity = db.query(AitEntity).filter(
            AitEntity.id == req.entity_id, AitEntity.college_id == current_user.college_id
        ).first()
        if not entity:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="This record does not belong to your college.")

    cr = ChangeRequest(
        college_id=current_user.college_id,
        requested_by=current_user.id,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        action=req.action,
        title=req.title or f"{req.action.capitalize()} {req.entity_type.capitalize()}",
        old_value=req.old_value,
        new_value=req.new_value,
        reason=req.reason,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)

    log_admin_audit(db, current_user, "CHANGE_REQUEST_CREATED", "CHANGE_REQUEST", {
        "change_request_id": cr.id, "entity_type": req.entity_type,
        "action": req.action,
    }, college_id=current_user.college_id)
    _notify_super_admins(db, "New change request submitted",
                         f"{current_user.full_name or current_user.email} submitted a "
                         f"{req.action} request for {req.entity_type}.",
                         college_id=current_user.college_id)
    db.commit()

    return cr.to_dict()


@router.patch("/{request_id}/cancel", summary="Cancel own pending request")
def cancel_change_request(
    request_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    cr = _get_request_scoped(request_id, current_user, db)
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if cr.status not in ACTIONABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This request has already been processed.")
    if not is_super and cr.requested_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only your own pending requests can be cancelled.")

    cr.status = "CANCELLED"
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.updated_at = cr.reviewed_at
    db.commit()
    db.refresh(cr)

    log_admin_audit(db, current_user, "CHANGE_REQUEST_CANCELLED", "CHANGE_REQUEST",
                    {"change_request_id": cr.id, "college_id": cr.college_id})
    return cr.to_dict()


@router.post("/{request_id}/respond", summary="Respond to a clarification request (College Admin)")
def respond_clarification(
    request_id: str,
    req: ClarificationRespondRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    cr = _get_request_scoped(request_id, current_user, db)
    is_super = (current_user.role or "").upper() == "SUPER_ADMIN"
    if cr.status != "NEEDS_CLARIFICATION":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Clarification is not being requested for this item.")
    if not is_super and cr.requested_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only the requesting admin can respond to clarification.")

    cr.clarification_response = req.response
    cr.status = "PENDING"  # returns to PENDING after clarification
    cr.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cr)

    log_admin_audit(db, current_user, "CHANGE_REQUEST_CLARIFICATION_RESPONDED", "CHANGE_REQUEST",
                    {"change_request_id": cr.id, "college_id": cr.college_id})
    _notify_super_admins(db, "Change request clarification answered",
                         f"A college admin responded to clarification on '{cr.title or cr.id}'.",
                         college_id=cr.college_id)
    db.commit()
    return cr.to_dict()


# ── SUPER_ADMIN actions ────────────────

def _require_super(current_user: User) -> None:
    if (current_user.role or "").upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have permission to approve changes.")


@router.post("/{request_id}/approve", summary="Approve change request and apply to production (SUPER_ADMIN only)")
def approve_change_request(
    request_id: str,
    req: ReviewRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    _require_super(current_user)
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    if cr.status not in ACTIONABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This request has already been processed.")

    cr.review_notes = req.notes or cr.review_notes
    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.updated_at = cr.reviewed_at
    db.commit()

    # Transactional apply; raises HTTPException (and marks FAILED) on stale/missing targets.
    cr = _apply_change(db, cr)

    log_admin_audit(db, current_user, "CHANGE_REQUEST_APPROVED", "CHANGE_REQUEST", {
        "change_request_id": cr.id, "entity_type": cr.entity_type,
        "entity_id": cr.entity_id,
    }, college_id=cr.college_id)
    _notify(db, cr.college_id, cr.requested_by, "Change request approved",
            f"Your change request '{cr.title or cr.id}' was approved and applied.", "SUCCESS")
    db.commit()
    return cr.to_dict()


@router.post("/{request_id}/reject", summary="Reject change request (SUPER_ADMIN only)")
def reject_change_request(
    request_id: str,
    req: ReviewRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    _require_super(current_user)
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    if cr.status not in ACTIONABLE_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This request has already been processed.")

    cr.status = "REJECTED"
    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.review_notes = req.notes
    cr.updated_at = cr.reviewed_at
    db.commit()
    db.refresh(cr)

    # Production data untouched on rejection
    log_admin_audit(db, current_user, "CHANGE_REQUEST_REJECTED", "CHANGE_REQUEST",
                    {"change_request_id": cr.id}, college_id=cr.college_id)
    _notify(db, cr.college_id, cr.requested_by, "Change request rejected",
            f"Your change request '{cr.title or cr.id}' was rejected. Reason: {req.notes or 'Not specified.'}",
            "ERROR")
    db.commit()
    return cr.to_dict()


@router.post("/{request_id}/clarification", summary="Request clarification (SUPER_ADMIN only)")
def request_clarification(
    request_id: str,
    req: ReviewRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    _require_super(current_user)
    cr = db.query(ChangeRequest).filter(ChangeRequest.id == request_id).first()
    if not cr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change request not found")
    if cr.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="This request has already been processed.")

    cr.status = "NEEDS_CLARIFICATION"
    cr.reviewed_by = current_user.id
    cr.reviewed_at = datetime.now(timezone.utc)
    cr.review_notes = req.notes
    cr.updated_at = cr.reviewed_at
    db.commit()
    db.refresh(cr)

    log_admin_audit(db, current_user, "CHANGE_REQUEST_CLARIFICATION_REQUESTED", "CHANGE_REQUEST",
                    {"change_request_id": cr.id}, college_id=cr.college_id)
    _notify(db, cr.college_id, cr.requested_by, "Clarification requested",
            f"Additional information is required for '{cr.title or cr.id}': {req.notes or ''}",
            "WARNING")
    db.commit()
    return cr.to_dict()
