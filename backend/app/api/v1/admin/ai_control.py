from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.app.core.database import get_db
from backend.app.core.permissions import get_current_admin_user, require_permission, log_admin_audit, PERM_AI_CONFIGURE, PERM_AI_FAILOVER
from backend.app.models.admin_system import (
    AiProviderConfig,
    AiModelRegistry,
    AiQuota,
    AiUsageLog
)
from backend.app.models.user import User
from backend.app.ai.circuit_breaker import circuit_breaker
from backend.app.ai.quota_tracker import quota_tracker

router = APIRouter(prefix="/ai", tags=["Admin AI Providers & Failover"])

class PriorityUpdateRequest(BaseModel):
    priority: int

class ModelToggleRequest(BaseModel):
    is_enabled: bool

@router.get("/providers")
def list_providers_and_models(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    providers = db.query(AiProviderConfig).order_by(AiProviderConfig.priority.asc()).all()
    results = []

    for p in providers:
        models = []
        for m in p.models:
            cb_info = circuit_breaker.get_state(m.model_identifier)
            models.append({
                "id": m.id,
                "model_identifier": m.model_identifier,
                "display_name": m.display_name,
                "is_enabled": m.is_enabled,
                "priority": m.priority,
                "capabilities": {
                    "text": m.supports_text,
                    "vision": m.supports_vision,
                    "documents": m.supports_documents,
                    "streaming": m.supports_streaming,
                    "structured_output": m.supports_structured_output,
                    "tool_calling": m.supports_tool_calling,
                    "context_limit": m.context_limit,
                    "supported_languages": m.supported_languages
                },
                "health_status": cb_info.get("state", m.health_status),
                "consecutive_failures": cb_info.get("consecutive_failures", m.consecutive_failures),
                "cooldown_until": cb_info.get("cooldown_until").isoformat() if cb_info.get("cooldown_until") else None,
                "requests_total": m.requests_total,
                "requests_success": m.requests_success,
                "requests_failed": m.requests_failed,
                "rate_limit_429_count": m.rate_limit_429_count,
                "avg_latency_ms": m.avg_latency_ms,
                "last_error_message": m.last_error_message
            })

        results.append({
            "id": p.id,
            "provider_name": p.provider_name,
            "display_name": p.display_name,
            "is_enabled": p.is_enabled,
            "priority": p.priority,
            "is_allowed_for_private_data": p.is_allowed_for_private_data,
            "models": models
        })

    return results

@router.post("/models/{model_id}/toggle")
def toggle_model_status(
    model_id: str,
    req: ModelToggleRequest,
    current_user: User = Depends(require_permission(PERM_AI_CONFIGURE)),
    db: Session = Depends(get_db)
):
    model = db.query(AiModelRegistry).filter(AiModelRegistry.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    model.is_enabled = req.is_enabled
    db.commit()

    log_admin_audit(db, current_user, "TOGGLE_AI_MODEL", "AI_MODEL", {
        "id": model.id,
        "model": model.model_identifier,
        "is_enabled": model.is_enabled
    })

    return {"message": f"Model status updated to {'enabled' if model.is_enabled else 'disabled'}"}

@router.post("/models/{model_id}/priority")
def update_model_priority(
    model_id: str,
    req: PriorityUpdateRequest,
    current_user: User = Depends(require_permission(PERM_AI_CONFIGURE)),
    db: Session = Depends(get_db)
):
    model = db.query(AiModelRegistry).filter(AiModelRegistry.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    model.priority = req.priority
    db.commit()

    log_admin_audit(db, current_user, "UPDATE_AI_MODEL_PRIORITY", "AI_MODEL", {
        "id": model.id,
        "model": model.model_identifier,
        "priority": req.priority
    })

    return {"message": "Priority ranking updated", "priority": model.priority}

@router.post("/models/{model_id}/circuit-breaker/reset")
def reset_circuit_breaker(
    model_id: str,
    current_user: User = Depends(require_permission(PERM_AI_FAILOVER)),
    db: Session = Depends(get_db)
):
    model = db.query(AiModelRegistry).filter(AiModelRegistry.id == model_id).first()
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    circuit_breaker.record_success(model.model_identifier)
    model.health_status = "HEALTHY"
    model.consecutive_failures = 0
    model.cooldown_until = None
    model.last_error_message = None
    db.commit()

    log_admin_audit(db, current_user, "RESET_CIRCUIT_BREAKER", "CIRCUIT_BREAKER", {
        "model": model.model_identifier
    })

    return {"message": f"Circuit breaker reset to HEALTHY for {model.model_identifier}"}

@router.get("/quotas")
def get_quotas(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    return quota_tracker.get_quota_summary(db)

@router.get("/usage")
def get_usage_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    logs = (
        db.query(AiUsageLog)
        .order_by(AiUsageLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "provider_name": l.provider_name,
            "model_identifier": l.model_identifier,
            "input_tokens": l.input_tokens,
            "output_tokens": l.output_tokens,
            "total_tokens": l.total_tokens,
            "latency_ms": l.latency_ms,
            "http_status": l.http_status,
            "success": l.success,
            "error_type": l.error_type,
            "failover_occurred": l.failover_occurred,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        }
        for l in logs
    ]
