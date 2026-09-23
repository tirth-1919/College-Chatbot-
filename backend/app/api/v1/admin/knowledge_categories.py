"""
Admin API: Dynamic Knowledge Database — Categories & Records.

Reuses existing project patterns:
- RBAC via require_permission (backend.app.core.permissions)
- Audit logging via log_admin_audit
- Chatbot integration: when a record becomes ACTIVE + verified, it is
  mirrored into ait_entities (the existing retrieval store) with correct
  source attribution, so KnowledgeDatabase.query_entities picks it up
  WITHOUT changing the source hierarchy. Semantic cache is invalidated
  on every mutation, matching the existing knowledge endpoints.
"""
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from sqlalchemy import or_, cast, String as SAString

from backend.app.core.database import get_db
from backend.app.core.permissions import (
    get_current_admin_user, require_permission, log_admin_audit,
    PERM_KNOWLEDGE_CREATE, PERM_KNOWLEDGE_UPDATE, PERM_KNOWLEDGE_DELETE,
)
from backend.app.models.knowledge import AitEntity
from backend.app.models.knowledge_categories import KnowledgeCategory, KnowledgeRecord
from backend.app.models.user import User
from backend.app.knowledge.semantic_cache import semantic_cache

router = APIRouter(prefix="/knowledge-db", tags=["Admin Knowledge Categories"])

SAFE_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_SOURCE_TYPES = {"AIT_OFFICIAL", "GTU_OFFICIAL", "ADMIN_VERIFIED", "OTHER_VERIFIED"}
VALID_RECORD_STATUS = {"DRAFT", "ACTIVE", "INACTIVE", "ARCHIVED"}
VALID_CATEGORY_STATUS = {"ACTIVE", "INACTIVE"}

# Authority label per source type — an admin-entered record is NEVER
# labelled as official website data unless it truly is AIT_OFFICIAL.
SOURCE_AUTHORITY = {
    "AIT_OFFICIAL": "Official AIT Website",
    "GTU_OFFICIAL": "Official GTU",
    "ADMIN_VERIFIED": "Admin Verified Database",
    "OTHER_VERIFIED": "Verified Third-Party Source",
}


class CategoryCreateRequest(BaseModel):
    name: str
    key: str
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    status: str = "ACTIVE"

    @field_validator("key")
    @classmethod
    def key_safe(cls, v: str) -> str:
        v = v.strip().lower()
        if not SAFE_KEY_RE.match(v):
            raise ValueError("Key must be lowercase letters/numbers separated by hyphens (e.g. 'scholarships')")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_CATEGORY_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_CATEGORY_STATUS)}")
        return v


class CategoryUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        if v is None:
            return v
        v = v.upper()
        if v not in VALID_CATEGORY_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_CATEGORY_STATUS)}")
        return v


class RecordCreateRequest(BaseModel):
    title: str
    field_name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}
    course: Optional[str] = None
    academic_year: Optional[str] = None
    source_type: str = "ADMIN_VERIFIED"
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    verified: bool = False
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: str = "DRAFT"

    @field_validator("source_type")
    @classmethod
    def source_valid(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_SOURCE_TYPES:
            raise ValueError(f"Source type must be one of {sorted(VALID_SOURCE_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_RECORD_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_RECORD_STATUS)}")
        return v


class RecordUpdateRequest(BaseModel):
    title: Optional[str] = None
    field_name: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    course: Optional[str] = None
    academic_year: Optional[str] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    verified: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    status: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def source_valid(cls, v):
        if v is None:
            return v
        v = v.upper()
        if v not in VALID_SOURCE_TYPES:
            raise ValueError(f"Source type must be one of {sorted(VALID_SOURCE_TYPES)}")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        if v is None:
            return v
        v = v.upper()
        if v not in VALID_RECORD_STATUS:
            raise ValueError(f"Status must be one of {sorted(VALID_RECORD_STATUS)}")
        return v


# ---------------------------------------------------------------- helpers

def _mirror_to_retrieval(db: Session, rec: KnowledgeRecord, cat: KnowledgeCategory):
    """
    Keep the existing chatbot retrieval working: ACTIVE + verified records
    are mirrored into ait_entities (the store KnowledgeDatabase.query_entities
    searches), with honest source attribution. Inactive/archived/draft
    records are not published to retrieval.
    """
    mirrored = db.query(AitEntity).filter(
        AitEntity.source_page == f"knowledge-record:{rec.id}"
    ).first()
    if rec.status != "ACTIVE":
        if mirrored:
            db.delete(mirrored)
        return

    details = dict(rec.metadata_json or {})
    if rec.field_name:
        details[rec.field_name] = rec.value
        # Fee-domain alias so the existing KnowledgeDatabase fee boost and
        # synonym expansion (annual_fees/sem_fees) can match this record.
        fn_l = (rec.field_name or "").lower()
        tl_l = (rec.title or "").lower()
        fee_label = f"{fn_l} {tl_l}"
        if "semester" in fee_label or "sem" in fn_l:
            details.setdefault("sem_fees", rec.value)
        elif "annual" in fee_label or "yearly" in fee_label:
            details.setdefault("annual_fees", rec.value)
    if rec.value and not rec.field_name:
        details.setdefault("summary", rec.value)
        if "fee" in (rec.title or "").lower():
            details.setdefault("fees", rec.value)
    if rec.description:
        details["description"] = rec.description
    if rec.course:
        details["course"] = rec.course
    if rec.academic_year:
        details["academic_year"] = rec.academic_year
    details["source_type"] = rec.source_type

    if mirrored:
        mirrored.name = rec.title
        mirrored.category = cat.key
        mirrored.code = rec.course
        mirrored.details = details
        mirrored.academic_year = rec.academic_year
        mirrored.source_url = rec.source_url or "admin://knowledge-db"
        mirrored.authority = SOURCE_AUTHORITY.get(rec.source_type, "Admin Verified Database")
        mirrored.is_verified = rec.verified
        mirrored.content_hash = str(hash(str(details)))
        mirrored.updated_at = datetime.now(timezone.utc)
    else:
        db.add(AitEntity(
            category=cat.key,
            name=rec.title,
            code=rec.course,  # real course code ('BCA'), not a free-text field
            details=details,
            academic_year=rec.academic_year,
            source_url=rec.source_url or "admin://knowledge-db",
            source_page=f"knowledge-record:{rec.id}",
            authority=SOURCE_AUTHORITY.get(rec.source_type, "Admin Verified Database"),
            is_verified=rec.verified,
            content_hash=str(hash(str(details))),
        ))


# ---------------------------------------------------------------- categories

@router.get("/categories")
def list_categories(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    from sqlalchemy import func as sa_func
    query = db.query(KnowledgeCategory)
    if search:
        s = f"%{search}%"
        query = query.filter(or_(KnowledgeCategory.name.ilike(s), KnowledgeCategory.key.ilike(s)))
    cats = query.order_by(KnowledgeCategory.display_order.asc(), KnowledgeCategory.name.asc()).all()
    counts = dict(db.query(KnowledgeRecord.category_id, sa_func.count(KnowledgeRecord.id))
                  .group_by(KnowledgeRecord.category_id).all())
    return {
        "total": len(cats),
        "items": [
            {
                "id": c.id, "name": c.name, "key": c.key,
                "description": c.description, "icon": c.icon,
                "display_order": c.display_order, "status": c.status,
                "record_count": counts.get(c.id, 0),
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            } for c in cats
        ],
    }


@router.post("/categories")
def create_category(
    req: CategoryCreateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_CREATE)),
    db: Session = Depends(get_db),
):
    dup = db.query(KnowledgeCategory).filter(
        or_(KnowledgeCategory.key == req.key, KnowledgeCategory.name == req.name)
    ).first()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"A category with this {'key' if dup.key == req.key else 'name'} already exists")
    cat = KnowledgeCategory(
        name=req.name.strip(), key=req.key, description=req.description,
        icon=req.icon, display_order=req.display_order, status=req.status,
        created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_admin_audit(db, current_user, "CREATE_KNOWLEDGE_CATEGORY", "KNOWLEDGE_CATEGORY",
                    {"id": cat.id, "name": cat.name, "key": cat.key})
    return {"message": "Category created successfully", "id": cat.id}


@router.get("/categories/{category_id}")
def get_category(
    category_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    cat = db.query(KnowledgeCategory).filter(KnowledgeCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return {
        "id": cat.id, "name": cat.name, "key": cat.key,
        "description": cat.description, "icon": cat.icon,
        "display_order": cat.display_order, "status": cat.status,
        "record_count": db.query(KnowledgeRecord).filter(KnowledgeRecord.category_id == cat.id).count(),
        "created_at": cat.created_at.isoformat() if cat.created_at else None,
        "updated_at": cat.updated_at.isoformat() if cat.updated_at else None,
    }


@router.patch("/categories/{category_id}")
def update_category(
    category_id: str,
    req: CategoryUpdateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_UPDATE)),
    db: Session = Depends(get_db),
):
    cat = db.query(KnowledgeCategory).filter(KnowledgeCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if req.name is not None:
        dup = db.query(KnowledgeCategory).filter(
            KnowledgeCategory.name == req.name.strip(), KnowledgeCategory.id != category_id).first()
        if dup:
            raise HTTPException(status_code=409, detail="A category with this name already exists")
        cat.name = req.name.strip()
    if req.description is not None:
        cat.description = req.description
    if req.icon is not None:
        cat.icon = req.icon
    if req.display_order is not None:
        cat.display_order = req.display_order
    if req.status is not None:
        cat.status = req.status
    cat.updated_by = current_user.id
    db.commit()
    db.refresh(cat)
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "UPDATE_KNOWLEDGE_CATEGORY", "KNOWLEDGE_CATEGORY", {"id": cat.id})
    return {"message": "Category updated successfully"}


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: str,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_DELETE)),
    db: Session = Depends(get_db),
):
    cat = db.query(KnowledgeCategory).filter(KnowledgeCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    count = db.query(KnowledgeRecord).filter(KnowledgeRecord.category_id == category_id).count()
    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This category contains {count} record(s). Move or delete the records before deleting this category."
        )
    db.delete(cat)
    db.commit()
    log_admin_audit(db, current_user, "DELETE_KNOWLEDGE_CATEGORY", "KNOWLEDGE_CATEGORY", {"id": category_id})
    return {"message": "Category deleted successfully"}


# ---------------------------------------------------------------- records

@router.get("/categories/{category_id}/records")
def list_records(
    category_id: str,
    search: Optional[str] = None,
    course: Optional[str] = None,
    academic_year: Optional[str] = None,
    source_type: Optional[str] = None,
    record_status: Optional[str] = None,
    verified: Optional[bool] = None,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    cat = db.query(KnowledgeCategory).filter(KnowledgeCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    q = db.query(KnowledgeRecord).filter(KnowledgeRecord.category_id == category_id)
    if search:
        s = f"%{search}%"
        q = q.filter(or_(
            KnowledgeRecord.title.ilike(s),
            KnowledgeRecord.value.ilike(s),
            KnowledgeRecord.description.ilike(s),
            cast(KnowledgeRecord.metadata_json, SAString).ilike(s),
        ))
    if course:
        q = q.filter(KnowledgeRecord.course == course)
    if academic_year:
        q = q.filter(KnowledgeRecord.academic_year == academic_year)
    if source_type:
        q = q.filter(KnowledgeRecord.source_type == source_type.upper())
    if record_status:
        q = q.filter(KnowledgeRecord.status == record_status.upper())
    if verified is not None:
        q = q.filter(KnowledgeRecord.verified == verified)

    sort_col = {
        "updated_at": KnowledgeRecord.updated_at,
        "title": KnowledgeRecord.title,
        "academic_year": KnowledgeRecord.academic_year,
        "course": KnowledgeRecord.course,
    }.get(sort_by, KnowledgeRecord.updated_at)
    q = q.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    total = q.count()
    records = q.offset(skip).limit(limit).all()

    # Distinct filter option values (for dropdowns)
    all_rows = db.query(KnowledgeRecord.course, KnowledgeRecord.academic_year).filter(
        KnowledgeRecord.category_id == category_id).all()
    courses = sorted({c for c, _ in all_rows if c})
    years = sorted({y for _, y in all_rows if y}, reverse=True)

    return {
        "total": total,
        "items": [r.to_dict() for r in records],
        "category": {"id": cat.id, "name": cat.name, "key": cat.key, "icon": cat.icon, "description": cat.description},
        "filter_options": {"courses": courses, "academic_years": years},
    }


@router.post("/categories/{category_id}/records")
def create_record(
    category_id: str,
    req: RecordCreateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_CREATE)),
    db: Session = Depends(get_db),
):
    cat = db.query(KnowledgeCategory).filter(KnowledgeCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Cannot add records to an inactive category")
    rec = KnowledgeRecord(
        category_id=category_id,
        title=req.title.strip(),
        field_name=req.field_name, value=req.value, description=req.description,
        metadata_json=req.metadata, course=req.course, academic_year=req.academic_year,
        source_type=req.source_type, source_url=req.source_url, source_title=req.source_title,
        verified=req.verified,
        verified_by=current_user.id if req.verified else None,
        verified_at=datetime.now(timezone.utc) if req.verified else None,
        valid_from=req.valid_from, valid_until=req.valid_until,
        status=req.status, created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(rec)
    db.flush()
    _mirror_to_retrieval(db, rec, cat)
    db.commit()
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "CREATE_KNOWLEDGE_RECORD", "KNOWLEDGE_RECORD",
                    {"id": rec.id, "category": cat.key, "title": rec.title})
    return {"message": "Record created successfully", "id": rec.id}


@router.get("/records/{record_id}")
def get_record(
    record_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    data = rec.to_dict()
    data["category"] = {"id": rec.category.id, "name": rec.category.name, "key": rec.category.key} if rec.category else None
    return data


@router.patch("/records/{record_id}")
def update_record(
    record_id: str,
    req: RecordUpdateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_UPDATE)),
    db: Session = Depends(get_db),
):
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    data = req.model_dump(exclude_unset=True)
    if "verified" in data and data["verified"] and not rec.verified:
        data["verified_by"] = current_user.id
        data["verified_at"] = datetime.now(timezone.utc)
    for k, v in data.items():
        if k == "metadata":
            rec.metadata_json = v
        else:
            setattr(rec, k, v)
    rec.updated_by = current_user.id
    db.flush()
    _mirror_to_retrieval(db, rec, rec.category)
    db.commit()
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "UPDATE_KNOWLEDGE_RECORD", "KNOWLEDGE_RECORD",
                    {"id": rec.id, "fields": list(data.keys())})
    return {"message": "Updated successfully"}


@router.delete("/records/{record_id}")
def delete_record(
    record_id: str,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_DELETE)),
    db: Session = Depends(get_db),
):
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    cat_key = rec.category.key if rec.category else None
    if rec.verified and (current_user.role or "").upper() != "SUPER_ADMIN":
        raise HTTPException(status_code=403,
                            detail="Verified records can only be deleted by a Super Administrator. Disable or archive instead.")
    mirrored = db.query(AitEntity).filter(AitEntity.source_page == f"knowledge-record:{rec.id}").first()
    if mirrored:
        db.delete(mirrored)
    db.delete(rec)
    db.commit()
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "DELETE_KNOWLEDGE_RECORD", "KNOWLEDGE_RECORD",
                    {"id": record_id, "category": cat_key})
    return {"message": "Record deleted successfully"}


def _record_action(record_id: str, current_user, db, action: str, new_status: str = None,
                   verify: bool = None):
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    if new_status is not None:
        rec.status = new_status
    if verify is not None:
        rec.verified = verify
        if verify:
            rec.verified_by = current_user.id
            rec.verified_at = datetime.now(timezone.utc)
    rec.updated_by = current_user.id
    db.flush()
    _mirror_to_retrieval(db, rec, rec.category)
    db.commit()
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, f"{action}_KNOWLEDGE_RECORD", "KNOWLEDGE_RECORD", {"id": rec.id})
    return {"message": f"Record {action.lower()} successful"}


@router.post("/records/{record_id}/duplicate")
def duplicate_record(
    record_id: str,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_CREATE)),
    db: Session = Depends(get_db),
):
    rec = db.query(KnowledgeRecord).filter(KnowledgeRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    clone = KnowledgeRecord(
        category_id=rec.category_id, course=rec.course, academic_year=rec.academic_year,
        title=f"{rec.title} (Copy)", field_name=rec.field_name, value=rec.value,
        description=rec.description, metadata_json=rec.metadata_json,
        source_type=rec.source_type, source_url=rec.source_url, source_title=rec.source_title,
        verified=False,  # duplicates start as Draft/unverified
        valid_from=rec.valid_from, valid_until=rec.valid_until,
        status="DRAFT", created_by=current_user.id, updated_by=current_user.id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    log_admin_audit(db, current_user, "DUPLICATE_KNOWLEDGE_RECORD", "KNOWLEDGE_RECORD",
                    {"id": clone.id, "duplicated_from": rec.id})
    return {"message": "Record duplicated successfully. The new record is currently Draft.", "id": clone.id}


@router.post("/records/{record_id}/verify")
def verify_record(record_id: str, current_user=Depends(require_permission(PERM_KNOWLEDGE_UPDATE)), db=Depends(get_db)):
    return _record_action(record_id, current_user, db, "VERIFY", verify=True)


@router.post("/records/{record_id}/enable")
def enable_record(record_id: str, current_user=Depends(require_permission(PERM_KNOWLEDGE_UPDATE)), db=Depends(get_db)):
    return _record_action(record_id, current_user, db, "ENABLE", new_status="ACTIVE")


@router.post("/records/{record_id}/disable")
def disable_record(record_id: str, current_user=Depends(require_permission(PERM_KNOWLEDGE_UPDATE)), db=Depends(get_db)):
    return _record_action(record_id, current_user, db, "DISABLE", new_status="INACTIVE")


@router.get("/export")
def export_records(
    category_id: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeRecord)
    if category_id:
        q = q.filter(KnowledgeRecord.category_id == category_id)
    return {"total": q.count(), "items": [r.to_dict() for r in q.order_by(KnowledgeRecord.updated_at.desc()).all()]}
