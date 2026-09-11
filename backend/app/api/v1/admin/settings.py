import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_SYSTEM_CONFIGURE, PERM_BACKUP_MANAGE
from backend.app.models.admin_system import (
    SystemPrompt,
    PromptVersion,
    FeatureFlag,
    SystemBackup
)
from backend.app.models.user import User

router = APIRouter(prefix="/settings", tags=["Admin Settings & System Control"])

class NewPromptVersionRequest(BaseModel):
    content: str
    change_reason: Optional[str] = "Admin update"
    activate_now: bool = True

class FeatureFlagToggleRequest(BaseModel):
    is_enabled: bool

@router.get("/prompts")
def list_prompts(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    prompts = db.query(SystemPrompt).all()
    results = []
    for p in prompts:
        versions = (
            db.query(PromptVersion)
            .filter(PromptVersion.prompt_id == p.id)
            .order_by(PromptVersion.version_number.desc())
            .all()
        )
        results.append({
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "active_version_number": p.active_version_number,
            "versions": [
                {
                    "id": v.id,
                    "version_number": v.version_number,
                    "content": v.content,
                    "change_reason": v.change_reason,
                    "is_active": v.is_active,
                    "created_by": v.created_by,
                    "created_at": v.created_at.isoformat() if v.created_at else None
                }
                for v in versions
            ]
        })
    return results

@router.post("/prompts/{slug}/version")
def add_prompt_version(
    slug: str,
    req: NewPromptVersionRequest,
    current_user: User = Depends(require_permission(PERM_SYSTEM_CONFIGURE)),
    db: Session = Depends(get_db)
):
    prompt = db.query(SystemPrompt).filter(SystemPrompt.slug == slug).first()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    latest_v = (
        db.query(PromptVersion.version_number)
        .filter(PromptVersion.prompt_id == prompt.id)
        .order_by(PromptVersion.version_number.desc())
        .first()
    )
    next_v_num = (latest_v[0] + 1) if latest_v else 1

    if req.activate_now:
        # Deactivate older active version
        db.query(PromptVersion).filter(PromptVersion.prompt_id == prompt.id).update({"is_active": False})
        prompt.active_version_number = next_v_num

    new_v = PromptVersion(
        prompt_id=prompt.id,
        version_number=next_v_num,
        content=req.content,
        change_reason=req.change_reason,
        is_active=req.activate_now,
        created_by=current_user.email
    )
    db.add(new_v)
    db.commit()

    log_admin_audit(db, current_user, "CREATE_PROMPT_VERSION", "PROMPT", {
        "slug": slug,
        "version": next_v_num,
        "activated": req.activate_now
    })

    return {"message": f"Prompt version {next_v_num} created successfully", "active": req.activate_now}

@router.get("/feature-flags")
def list_feature_flags(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    flags = db.query(FeatureFlag).order_by(FeatureFlag.key.asc()).all()
    return [
        {
            "id": f.id,
            "key": f.key,
            "name": f.name,
            "description": f.description,
            "is_enabled": f.is_enabled,
            "updated_by": f.updated_by,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None
        }
        for f in flags
    ]

@router.post("/feature-flags/{key}/toggle")
def toggle_feature_flag(
    key: str,
    req: FeatureFlagToggleRequest,
    current_user: User = Depends(require_permission(PERM_SYSTEM_CONFIGURE)),
    db: Session = Depends(get_db)
):
    flag = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature flag not found")

    flag.is_enabled = req.is_enabled
    flag.updated_by = current_user.email
    flag.updated_at = datetime.now(timezone.utc)
    db.commit()

    log_admin_audit(db, current_user, "TOGGLE_FEATURE_FLAG", "FEATURE_FLAG", {
        "key": key,
        "is_enabled": flag.is_enabled
    })

    return {"message": f"Feature flag '{key}' updated to {flag.is_enabled}"}

@router.post("/backup")
def create_system_backup(
    current_user: User = Depends(require_permission(PERM_BACKUP_MANAGE)),
    db: Session = Depends(get_db)
):
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"ait_assistant_backup_{timestamp_str}.db"
    backup_dir = os.path.join(settings.UPLOAD_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    target_path = os.path.join(backup_dir, backup_filename)

    # If SQLite file exists, copy it
    source_db = settings.DATABASE_URL.replace("sqlite:///", "")
    size = 0
    if os.path.exists(source_db):
        shutil.copy2(source_db, target_path)
        size = os.path.getsize(target_path)

    backup_record = SystemBackup(
        filename=backup_filename,
        backup_type="FULL",
        file_size_bytes=size,
        storage_path=target_path,
        status="COMPLETED",
        created_by=current_user.email
    )
    db.add(backup_record)
    db.commit()

    log_admin_audit(db, current_user, "CREATE_SYSTEM_BACKUP", "BACKUP", {
        "filename": backup_filename,
        "size_bytes": size
    })

    return {
        "message": "System backup created successfully",
        "filename": backup_filename,
        "size_bytes": size
    }

@router.get("/backups")
def list_system_backups(
    current_user: User = Depends(require_permission(PERM_BACKUP_MANAGE)),
    db: Session = Depends(get_db)
):
    backups = db.query(SystemBackup).order_by(SystemBackup.created_at.desc()).all()
    return [
        {
            "id": b.id,
            "filename": b.filename,
            "backup_type": b.backup_type,
            "file_size_bytes": b.file_size_bytes,
            "status": b.status,
            "created_by": b.created_by,
            "created_at": b.created_at.isoformat() if b.created_at else None
        }
        for b in backups
    ]
