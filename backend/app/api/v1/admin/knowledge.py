import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_KNOWLEDGE_CREATE, PERM_KNOWLEDGE_UPDATE, PERM_KNOWLEDGE_DELETE
from backend.app.models.knowledge import AitEntity, AitKnowledgeVersion
from backend.app.models.user import User
from backend.app.knowledge.semantic_cache import semantic_cache

router = APIRouter(prefix="/knowledge", tags=["Admin Knowledge Management"])

class EntityCreateRequest(BaseModel):
    category: str
    name: str
    code: Optional[str] = None
    details: Dict[str, Any]
    source_url: str = "https://www.aitindia.in"
    source_page: Optional[str] = None
    authority: str = "Official AIT Records"
    status: str = "PUBLISHED"

class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    source_url: Optional[str] = None

class RollbackRequest(BaseModel):
    target_version_number: int
    reason: Optional[str] = None

@router.get("")
def list_entities(
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    query = db.query(AitEntity)
    # Phase 9: SUPER_ADMIN can see all; COLLEGE_ADMIN scoped to own college
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        query = query.filter(AitEntity.college_id == current_user.college_id)
    if category and category != "all":
        query = query.filter(AitEntity.category == category)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (AitEntity.name.ilike(s)) |
            (AitEntity.code.ilike(s)) |
            (AitEntity.category.ilike(s))
        )
    total = query.count()
    entities = query.order_by(AitEntity.category.asc(), AitEntity.name.asc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "category": e.category,
                "name": e.name,
                "code": e.code,
                "details": e.details,
                "source_url": e.source_url,
                "authority": e.authority,
                "is_verified": e.is_verified,
                "content_hash": e.content_hash,
                "version_count": len(e.versions) if e.versions else 1,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None
            }
            for e in entities
        ]
    }

@router.get("/{entity_id}")
def get_entity_details(
    entity_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    q = db.query(AitEntity).filter(AitEntity.id == entity_id)
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(AitEntity.college_id == current_user.college_id)
    entity = q.first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    versions = (
        db.query(AitKnowledgeVersion)
        .filter(AitKnowledgeVersion.entity_id == entity_id)
        .order_by(AitKnowledgeVersion.version.desc())
        .all()
    )

    return {
        "id": entity.id,
        "category": entity.category,
        "name": entity.name,
        "code": entity.code,
        "details": entity.details,
        "source_url": entity.source_url,
        "source_page": entity.source_page,
        "authority": entity.authority,
        "is_verified": entity.is_verified,
        "content_hash": entity.content_hash,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "payload": v.payload,
                "status": v.status,
                "content_hash": v.content_hash,
                "created_at": v.created_at.isoformat() if v.created_at else None
            }
            for v in versions
        ]
    }

@router.post("")
def create_entity(
    req: EntityCreateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_CREATE)),
    db: Session = Depends(get_db)
):
    content_hash = hashlib.sha256(str(req.details).encode("utf-8")).hexdigest()
    new_entity = AitEntity(
        category=req.category,
        name=req.name,
        code=req.code,
        details=req.details,
        source_url=req.source_url,
        source_page=req.source_page or f"/{req.category}",
        authority=req.authority,
        is_verified=True,
        content_hash=content_hash,
        college_id=current_user.college_id  # Phase 9: stamp tenant
    )
    db.add(new_entity)
    db.flush()

    v1 = AitKnowledgeVersion(
        entity_id=new_entity.id,
        version=1,
        payload=req.details,
        status=req.status,
        content_hash=content_hash
    )
    db.add(v1)
    db.commit()
    db.refresh(new_entity)

    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "CREATE_KNOWLEDGE_ENTITY", "AIT_ENTITY", {"id": new_entity.id, "name": new_entity.name})

    return {"message": "Knowledge entity created successfully", "id": new_entity.id}

@router.put("/{entity_id}")
def update_entity(
    entity_id: str,
    req: EntityUpdateRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_UPDATE)),
    db: Session = Depends(get_db)
):
    q = db.query(AitEntity).filter(AitEntity.id == entity_id)
    if current_user.role != "SUPER_ADMIN" and current_user.college_id:
        q = q.filter(AitEntity.college_id == current_user.college_id)
    entity = q.first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    if req.name:
        entity.name = req.name
    if req.category:
        entity.category = req.category
    if req.code is not None:
        entity.code = req.code
    if req.source_url:
        entity.source_url = req.source_url

    if req.details is not None:
        entity.details = req.details
        new_hash = hashlib.sha256(str(req.details).encode("utf-8")).hexdigest()
        entity.content_hash = new_hash

        # Get latest version number
        latest_v = (
            db.query(AitKnowledgeVersion.version)
            .filter(AitKnowledgeVersion.entity_id == entity_id)
            .order_by(AitKnowledgeVersion.version.desc())
            .first()
        )
        next_version = (latest_v[0] + 1) if latest_v else 1

        new_v = AitKnowledgeVersion(
            entity_id=entity.id,
            version=next_version,
            payload=req.details,
            status=req.status or "PUBLISHED",
            content_hash=new_hash
        )
        db.add(new_v)

    entity.updated_at = datetime.now(timezone.utc)
    db.commit()

    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "UPDATE_KNOWLEDGE_ENTITY", "AIT_ENTITY", {"id": entity.id})

    return {"message": "Knowledge entity updated successfully"}

@router.post("/{entity_id}/rollback")
def rollback_entity_version(
    entity_id: str,
    req: RollbackRequest,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_UPDATE)),
    db: Session = Depends(get_db)
):
    """
    Rolls back entity to an authoritative prior version without destroying history.
    """
    entity = db.query(AitEntity).filter(AitEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    target_v = (
        db.query(AitKnowledgeVersion)
        .filter(AitKnowledgeVersion.entity_id == entity_id, AitKnowledgeVersion.version == req.target_version_number)
        .first()
    )
    if not target_v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Version {req.target_version_number} not found")

    # Increment and record the rollback as a new version
    latest_v = (
        db.query(AitKnowledgeVersion.version)
        .filter(AitKnowledgeVersion.entity_id == entity_id)
        .order_by(AitKnowledgeVersion.version.desc())
        .first()
    )
    next_version = (latest_v[0] + 1) if latest_v else 1

    entity.details = target_v.payload
    entity.content_hash = target_v.content_hash
    entity.updated_at = datetime.now(timezone.utc)

    rollback_record = AitKnowledgeVersion(
        entity_id=entity.id,
        version=next_version,
        payload=target_v.payload,
        status="PUBLISHED",
        content_hash=target_v.content_hash
    )
    db.add(rollback_record)
    db.commit()

    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "ROLLBACK_KNOWLEDGE_ENTITY", "AIT_ENTITY", {
        "id": entity.id,
        "restored_version": req.target_version_number,
        "new_version": next_version,
        "reason": req.reason
    })

    return {
        "message": f"Successfully restored entity to version {req.target_version_number}",
        "current_version": next_version
    }

@router.delete("/{entity_id}")
def delete_entity(
    entity_id: str,
    current_user: User = Depends(require_permission(PERM_KNOWLEDGE_DELETE)),
    db: Session = Depends(get_db)
):
    entity = db.query(AitEntity).filter(AitEntity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")

    db.delete(entity)
    db.commit()
    semantic_cache.invalidate_all()
    log_admin_audit(db, current_user, "DELETE_KNOWLEDGE_ENTITY", "AIT_ENTITY", {"id": entity_id})

    return {"message": "Knowledge entity deleted successfully"}
