"""Shared tenant-isolation helpers for the multi-college platform.

Every college-owned object must be scoped by ``college_id``. College Admins
are hard-scoped to ``current_user.college_id``; Super Admins may cross
colleges but must explicitly select a target college for uploads.
"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.models.college import StagedUploadRecord
from backend.app.models.knowledge_categories import KnowledgeCategory

# Valid staged-upload statuses and allowed transitions (status machine).
STAGED_STATUSES = (
    "PENDING_REVIEW", "SUBMITTED_FOR_APPROVAL", "NEEDS_CHANGES",
    "APPROVED", "REJECTED", "FAILED",
)

ALLOWED_TRANSITIONS = {
    "PENDING_REVIEW": {"SUBMITTED_FOR_APPROVAL", "FAILED"},
    "SUBMITTED_FOR_APPROVAL": {"APPROVED", "NEEDS_CHANGES", "REJECTED", "FAILED"},
    "NEEDS_CHANGES": {"SUBMITTED_FOR_APPROVAL", "FAILED"},
    "APPROVED": set(),
    "REJECTED": set(),
    "FAILED": set(),
}


def normalize_status(s: str) -> str:
    """Normalize legacy/loose status strings to the canonical status machine."""
    if not s:
        return "PENDING_REVIEW"
    s = str(s).strip().upper()
    aliases = {
        "PENDING": "PENDING_REVIEW",
        "DRAFT": "PENDING_REVIEW",
        "SUBMITTED": "SUBMITTED_FOR_APPROVAL",
        "UNDER_REVIEW": "SUBMITTED_FOR_APPROVAL",
        "IN_REVIEW": "SUBMITTED_FOR_APPROVAL",
        "CHANGES_REQUESTED": "NEEDS_CHANGES",
        "CHANGE_REQUESTED": "NEEDS_CHANGES",
        "PUBLISHED": "APPROVED",
    }
    return aliases.get(s, s)


def assert_valid_transition(current: str, target: str) -> None:
    """Raise ValueError when a status transition is not allowed."""
    current = normalize_status(current)
    target = normalize_status(target)
    if current == target:
        return  # idempotent re-set of the same status
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Invalid status transition: {current} -> {target}. "
            f"Allowed: {sorted(allowed) or 'none (terminal status)'}"
        )


def resolve_target_college_id(user, college_id: Optional[str],
                              *, required: bool = False) -> Optional[str]:
    """Resolve the tenant a request operates on.

    - College Admin: the tenant is ALWAYS ``current_user.college_id``. Any
      ``college_id`` supplied in the request is ignored (never trusted).
    - Super Admin: the supplied ``college_id`` is authoritative and MUST be
      explicitly provided for uploads — there is no first-college fallback.
    """
    role = (user.role or "").upper()
    if role == "SUPER_ADMIN":
        if college_id:
            return str(college_id)
        if required:
            raise HTTPException(
                status_code=400,
                detail="College context is required for Super Admin uploads.",
            )
        return None
    # College Admin (and any other role): own tenant only.
    if not user.college_id:
        raise HTTPException(
            status_code=403,
            detail="Your account is not linked to a college.",
        )
    return str(user.college_id)


def ensure_same_college(user, record_college_id: Optional[str]) -> None:
    """404 without leaking existence when a College Admin touches another
    tenant's record. Super Admin passes through."""
    if not record_college_id:
        return  # global/unscoped record: nothing to enforce
    role = (user.role or "").upper()
    if role == "SUPER_ADMIN":
        return
    if str(record_college_id) != str(user.college_id):
        # Deliberately 404 (not 403) so we never reveal that another
        # tenant's record exists.
        raise HTTPException(status_code=404, detail="Not found")


def get_tenant_scoped_staged_record(db: Session, user,
                                    record_id: str) -> StagedUploadRecord:
    """Load a StagedUploadRecord enforcing tenant ownership server-side."""
    rec = db.query(StagedUploadRecord).filter(
        StagedUploadRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Staged record not found")
    ensure_same_college(user, rec.college_id)
    return rec


def get_tenant_category(db: Session, user, key: str,
                        college_id: Optional[str] = None) -> Optional[KnowledgeCategory]:
    """Category lookup scoped by college_id + key (never key alone)."""
    role = (user.role or "").upper()
    cid = user.college_id
    if role == "SUPER_ADMIN":
        cid = college_id  # Super Admin must pass the tenant explicitly
    if cid is not None:
        return (db.query(KnowledgeCategory)
                .filter(KnowledgeCategory.college_id == cid,
                        KnowledgeCategory.key == key)
                .first())
    return (db.query(KnowledgeCategory)
            .filter(KnowledgeCategory.college_id.is_(None),
                    KnowledgeCategory.key == key)
            .first())


def get_tenant_category_by_id(db: Session, user,
                              category_id: str) -> Optional[KnowledgeCategory]:
    """Load a category by id enforcing tenant ownership."""
    cat = (db.query(KnowledgeCategory)
           .filter(KnowledgeCategory.id == category_id).first())
    if not cat:
        return None
    ensure_same_college(user, cat.college_id)
    return cat


def provision_default_categories(db: Session, college_id: str) -> list:
    """Idempotently create the default category set for a college.

    Running multiple times never creates duplicates. Returns the list of
    KnowledgeCategory rows for the college (existing + newly created).
    """
    from backend.app.services.category_defaults import DEFAULT_CATEGORIES

    existing = {
        c.key: c
        for c in db.query(KnowledgeCategory)
        .filter(KnowledgeCategory.college_id == college_id).all()
    }
    result = []
    for spec in DEFAULT_CATEGORIES:
        key = spec["key"]
        cat = existing.get(key)
        if cat is None:
            cat = KnowledgeCategory(
                college_id=college_id, key=key, name=spec["name"],
                description=spec.get("description"),
            )
            db.add(cat)
            db.flush()
        elif not cat.name:
            cat.name = spec["name"]
        result.append(cat)
    db.flush()
    return result
