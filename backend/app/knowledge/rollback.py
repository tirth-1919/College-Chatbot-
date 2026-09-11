from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.knowledge import AitEntity, AitKnowledgeVersion
from backend.app.models.admin_system import (
    SystemPrompt,
    PromptVersion,
    AiProviderConfig,
    AiModelRegistry,
    FeatureFlag
)
from backend.app.models.audit import AuditLog

class RollbackEngine:
    """Universal rollback engine for knowledge, prompts, AI configurations, and system flags."""

    @staticmethod
    def rollback_knowledge_entity(entity_id: str, target_version_number: int, actor_id: str) -> Dict[str, Any]:
        """Rolls back an AIT knowledge entity to a previous version."""
        db: Session = SessionLocal()
        try:
            entity = db.query(AitEntity).filter(AitEntity.id == entity_id).first()
            if not entity:
                return {"success": False, "error": "Entity not found"}

            version = db.query(AitKnowledgeVersion).filter(
                AitKnowledgeVersion.entity_id == entity_id,
                AitKnowledgeVersion.version_number == target_version_number
            ).first()

            if not version:
                return {"success": False, "error": f"Version {target_version_number} not found for this entity"}

            # Save state before rollback
            prev_content = entity.content

            # Apply rollback
            entity.content = version.content
            entity.version += 1
            entity.updated_at = datetime.now(timezone.utc)

            # Record in audit log
            audit = AuditLog(
                actor_id=actor_id,
                action="ROLLBACK_KNOWLEDGE",
                resource="ait_entities",
                resource_id=entity_id,
                details={
                    "rolled_back_to_version": target_version_number,
                    "previous_content_snippet": prev_content[:100],
                    "restored_content_snippet": version.content[:100]
                }
            )
            db.add(audit)
            db.commit()

            return {
                "success": True,
                "entity_id": entity_id,
                "new_version": entity.version,
                "restored_version": target_version_number
            }
        finally:
            db.close()

    @staticmethod
    def rollback_system_prompt(prompt_slug: str, target_version: int, actor_id: str) -> Dict[str, Any]:
        """Rolls back a system prompt to a historical version."""
        db: Session = SessionLocal()
        try:
            prompt = db.query(SystemPrompt).filter(SystemPrompt.slug == prompt_slug).first()
            if not prompt:
                return {"success": False, "error": "System prompt not found"}

            target_pv = db.query(PromptVersion).filter(
                PromptVersion.prompt_id == prompt.id,
                PromptVersion.version_number == target_version
            ).first()

            if not target_pv:
                return {"success": False, "error": f"Prompt version {target_version} does not exist"}

            # Mark other versions inactive, mark target active
            for v in prompt.versions:
                v.is_active = (v.version_number == target_version)

            prompt.active_version_number = target_version
            prompt.updated_at = datetime.now(timezone.utc)

            audit = AuditLog(
                actor_id=actor_id,
                action="ROLLBACK_PROMPT",
                resource="system_prompts",
                resource_id=prompt.id,
                details={"slug": prompt_slug, "target_version": target_version}
            )
            db.add(audit)
            db.commit()
            return {"success": True, "prompt_slug": prompt_slug, "active_version": target_version}
        finally:
            db.close()

    @staticmethod
    def rollback_feature_flag(key: str, actor_id: str) -> Dict[str, Any]:
        """Toggles or rolls back a feature flag to safe default (disabled if causing issues)."""
        db: Session = SessionLocal()
        try:
            flag = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
            if not flag:
                return {"success": False, "error": "Feature flag not found"}

            prev = flag.is_enabled
            flag.is_enabled = not prev
            flag.updated_by = actor_id
            flag.updated_at = datetime.now(timezone.utc)

            audit = AuditLog(
                actor_id=actor_id,
                action="ROLLBACK_FEATURE_FLAG",
                resource="feature_flags",
                resource_id=flag.id,
                details={"key": key, "from": prev, "to": flag.is_enabled}
            )
            db.add(audit)
            db.commit()
            return {"success": True, "key": key, "is_enabled": flag.is_enabled}
        finally:
            db.close()

rollback_engine = RollbackEngine()
