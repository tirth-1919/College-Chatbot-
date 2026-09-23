from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

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
from backend.app.ai.provider_state import provider_state_manager
from backend.app.ai.credential_registry import (
    credential_registry,
    credential_runtime,
    encrypt_secret,
    decrypt_secret,
    mask_key,
    classify_failure,
)
from backend.app.models.admin_system import AiCredential

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
            runtime = provider_state_manager.snapshot(p.provider_name, m.model_identifier)
            api_key = provider_state_manager.get_api_key_status(p.provider_name, p.api_key_env)

            # Effective runtime state: configuration/runtime checks take precedence
            if not p.is_enabled or not m.is_enabled:
                effective_state = "DISABLED"
            elif runtime["runtime_state"] == "UNKNOWN" and not api_key["configured"] and p.provider_name.lower() != "ollama":
                effective_state = "API_KEY_MISSING"
            else:
                effective_state = runtime["runtime_state"]

            models.append({
                "id": m.id,
                "model_identifier": m.model_identifier,
                "display_name": m.display_name,
                "is_enabled": m.is_enabled,
                "priority": m.priority,
                "free_tier_status": getattr(m, "free_tier_status", "UNKNOWN"),
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
                # Configuration state
                "api_key_status": api_key["status"],
                "api_key_source": api_key["key_source"],
                # Runtime availability state (distinct from configuration)
                "health_status": cb_info.get("state", m.health_status),
                "runtime_state": effective_state,
                "quota_status": runtime["quota_status"],
                "cooldown_until": runtime["cooldown_until"] or (cb_info.get("cooldown_until").isoformat() if cb_info.get("cooldown_until") else None),
                "cooldown_active": runtime["cooldown_active"],
                "retry_after": runtime["retry_after"],
                "consecutive_failures": cb_info.get("consecutive_failures", m.consecutive_failures),
                "requests_total": m.requests_total,
                "requests_success": m.requests_success,
                "requests_failed": m.requests_failed,
                "rate_limit_429_count": m.rate_limit_429_count,
                "failover_count": runtime["failover_count"],
                "avg_latency_ms": m.avg_latency_ms,
                "last_success_at": m.last_success_at.isoformat() if m.last_success_at else None,
                "last_error_at": m.last_error_at.isoformat() if m.last_error_at else None,
                "last_error_message": m.last_error_message,
                "last_error_type": runtime["last_error_type"],
            })

        api_key = provider_state_manager.get_api_key_status(p.provider_name, p.api_key_env)
        results.append({
            "id": p.id,
            "provider_name": p.provider_name,
            "display_name": p.display_name,
            "is_enabled": p.is_enabled,
            "priority": p.priority,
            "is_allowed_for_private_data": p.is_allowed_for_private_data,
            # API key configuration status (NEVER the secret itself)
            "api_key_status": api_key["status"],
            "api_key_source": api_key["key_source"],
            "base_url": p.base_url,
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
    provider_state_manager.reset_state(model.provider.provider_name, model.model_identifier)
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

@router.get("/runtime-status")
def get_runtime_status(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Runtime availability state for every provider/model (no secrets)."""
    providers = db.query(AiProviderConfig).order_by(AiProviderConfig.priority.asc()).all()
    results = []
    for p in providers:
        api_key = provider_state_manager.get_api_key_status(p.provider_name, p.api_key_env)
        models = []
        for m in p.models:
            runtime = provider_state_manager.snapshot(p.provider_name, m.model_identifier)
            models.append({
                "model_identifier": m.model_identifier,
                "display_name": m.display_name,
                "is_enabled": m.is_enabled,
                "runtime_state": runtime["runtime_state"],
                "quota_status": runtime["quota_status"],
                "cooldown_active": runtime["cooldown_active"],
                "cooldown_until": runtime["cooldown_until"],
                "retry_after": runtime["retry_after"],
                "last_error_type": runtime["last_error_type"],
                "failover_count": runtime["failover_count"],
            })
        results.append({
            "provider_name": p.provider_name,
            "display_name": p.display_name,
            "priority": p.priority,
            "is_enabled": p.is_enabled,
            "api_key_status": api_key["status"],
            "api_key_source": api_key["key_source"],
            "base_url": p.base_url,
            "models": models,
        })
    return results

@router.get("/failover-events")
def get_failover_events(
    limit: int = 25,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Full automatic decision chains grouped by request_id."""
    recent_ids = [
        row[0] for row in (
            db.query(AiUsageLog.request_id)
            .order_by(AiUsageLog.timestamp.desc())
            .limit(limit * 10)
            .all()
        )
        if row[0]
    ]
    # de-duplicate preserving order
    seen = set()
    unique_ids = [rid for rid in recent_ids if not (rid in seen or seen.add(rid))][:limit]

    events = []
    for rid in unique_ids:
        logs = (
            db.query(AiUsageLog)
            .filter(AiUsageLog.request_id == rid)
            .order_by(AiUsageLog.timestamp.asc())
            .all()
        )
        if not logs:
            continue
        chain = [
            {
                "provider_name": l.provider_name,
                "model_identifier": l.model_identifier,
                "success": l.success,
                "error_type": l.error_type,
                "http_status": l.http_status,
                "fallback_from_model": l.fallback_from_model,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            }
            for l in logs
        ]
        final = next((l for l in reversed(logs) if l.success), None)
        events.append({
            "request_id": rid,
            "final_provider": final.provider_name if final else "NO_USABLE_PROVIDER",
            "final_model": final.model_identifier if final else "NO_USABLE_PROVIDER",
            "failover_count": len([l for l in logs if not l.success and l.provider_name != "FINAL"]),
            "chain": chain,
        })
    return events

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
            "fallback_from_model": l.fallback_from_model,
            "request_id": l.request_id,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        }
        for l in logs
    ]

# =========================================================================== #
# Multi-credential management (live, no-restart, never exposes raw secrets)
# =========================================================================== #

class CredentialCreateRequest(BaseModel):
    provider_name: str
    api_key: str
    label: Optional[str] = None
    priority: int = 1
    is_enabled: bool = True
    free_tier_status: str = "UNKNOWN"  # FREE_TIER_ELIGIBLE | PAID | UNKNOWN | NOT_APPLICABLE


class CredentialUpdateRequest(BaseModel):
    label: Optional[str] = None
    priority: Optional[int] = None
    is_enabled: Optional[bool] = None
    free_tier_status: Optional[str] = None
    api_key: Optional[str] = None  # optional key rotation by admin


def _credential_dto(c: AiCredential, include_runtime: bool = True) -> dict:
    snap = credential_runtime.snapshot(c.provider_name, c.id) if include_runtime else {}
    return {
        "id": c.id,
        "provider_name": c.provider_name,
        "label": c.label,
        # masked only — NEVER the raw key
        "masked_key": c.masked_key,
        "priority": c.priority,
        "is_enabled": c.is_enabled,
        "free_tier_status": c.free_tier_status,
        "is_valid": c.is_valid,
        "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "runtime": snap,
        # Quota is UNKNOWN unless the provider itself reports it — never fabricated
        "quota_remaining": "UNKNOWN",
        "quota_reason": "Provider does not expose reliable quota metadata.",
    }


@router.post("/credentials", status_code=status.HTTP_201_CREATED)
def create_credential(
    req: CredentialCreateRequest,
    current_user: User = Depends(require_permission(PERM_AI_CONFIGURE)),
    db: Session = Depends(get_db),
):
    """Add an API key. Immediately live — no restart required."""
    provider_name = (req.provider_name or "").strip().lower()
    if not provider_name:
        raise HTTPException(status_code=400, detail="provider_name is required")
    raw_key = (req.api_key or "").strip()
    if not raw_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    if req.free_tier_status not in ("FREE_TIER_ELIGIBLE", "PAID", "UNKNOWN", "NOT_APPLICABLE"):
        raise HTTPException(status_code=400, detail="Invalid free_tier_status")

    c = AiCredential(
        provider_name=provider_name,
        label=(req.label or "").strip() or None,
        api_key_encrypted=encrypt_secret(raw_key),
        masked_key=mask_key(raw_key),
        priority=max(1, int(req.priority)),
        is_enabled=req.is_enabled,
        free_tier_status=req.free_tier_status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    credential_registry.invalidate()  # next request sees the new key immediately

    log_admin_audit(db, current_user, "CREATE_AI_CREDENTIAL", "AI_CREDENTIAL", {
        "id": c.id, "provider": provider_name, "label": c.label,
        "masked_key": c.masked_key, "priority": c.priority,
        "free_tier_status": c.free_tier_status,
        # deliberately NOT the raw key
    })
    return _credential_dto(c)


@router.get("/credentials")
def list_credentials(
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    q = db.query(AiCredential)
    if provider:
        q = q.filter(AiCredential.provider_name == provider.lower())
    creds = q.order_by(AiCredential.provider_name.asc(), AiCredential.priority.asc()).all()
    return [_credential_dto(c) for c in creds]


@router.patch("/credentials/{credential_id}")
def update_credential(
    credential_id: str,
    req: CredentialUpdateRequest,
    current_user: User = Depends(require_permission(PERM_AI_CONFIGURE)),
    db: Session = Depends(get_db),
):
    c = db.query(AiCredential).filter(AiCredential.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")

    if req.label is not None:
        c.label = req.label.strip() or None
    if req.priority is not None:
        c.priority = max(1, int(req.priority))
    if req.is_enabled is not None:
        c.is_enabled = req.is_enabled
    if req.free_tier_status is not None:
        if req.free_tier_status not in ("FREE_TIER_ELIGIBLE", "PAID", "UNKNOWN", "NOT_APPLICABLE"):
            raise HTTPException(status_code=400, detail="Invalid free_tier_status")
        c.free_tier_status = req.free_tier_status
    if req.api_key:  # optional secret replacement (still never returned)
        raw = req.api_key.strip()
        c.api_key_encrypted = encrypt_secret(raw)
        c.masked_key = mask_key(raw)
        c.is_valid = True
        credential_runtime.recheck(c.provider_name, c.id)

    db.commit()
    credential_registry.invalidate()  # propagate without restart

    log_admin_audit(db, current_user, "UPDATE_AI_CREDENTIAL", "AI_CREDENTIAL", {
        "id": c.id, "provider": c.provider_name, "priority": c.priority,
        "is_enabled": c.is_enabled, "free_tier_status": c.free_tier_status,
        "key_replaced": bool(req.api_key),
    })
    return _credential_dto(c)


@router.delete("/credentials/{credential_id}")
def delete_credential(
    credential_id: str,
    current_user: User = Depends(require_permission(PERM_AI_FAILOVER)),
    db: Session = Depends(get_db),
):
    c = db.query(AiCredential).filter(AiCredential.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    db.delete(c)
    db.commit()
    credential_registry.invalidate()

    log_admin_audit(db, current_user, "DELETE_AI_CREDENTIAL", "AI_CREDENTIAL", {
        "id": credential_id, "provider": c.provider_name, "masked_key": c.masked_key,
    })
    return {"message": "Credential deleted", "id": credential_id}


@router.post("/credentials/{credential_id}/test")
async def test_credential(
    credential_id: str,
    current_user: User = Depends(require_permission(PERM_AI_CONFIGURE)),
    db: Session = Depends(get_db),
):
    """Smallest practical provider request. Returns VALID/INVALID/RATE_LIMITED/
    UNAVAILABLE/UNKNOWN only — never the raw key. Note: this test consumes a
    small amount of real provider quota."""
    from backend.app.ai.router import ai_router

    c = db.query(AiCredential).filter(AiCredential.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")

    result = "UNKNOWN"
    detail = ""
    try:
        raw = decrypt_secret(c.api_key_encrypted)
        adapter = ai_router._adapter_for(c.provider_name, None, raw)
        model = adapter.DEFAULT_MODEL if hasattr(adapter, "DEFAULT_MODEL") else None
        if c.provider_name == "ollama":
            ok = await adapter.health_check(model)
            result = "VALID" if ok else "UNAVAILABLE"
        else:
            r = await adapter.generate_response(
                model, "Reply with exactly: OK", "You are a test harness."
            )
            result = "VALID" if (r.content or "").strip() else "UNKNOWN"
    except Exception as e:
        code = getattr(e, "status_code", None) or getattr(e, "code", None)
        msg = str(e)
        if code == 429 or "RATE_LIMIT" in msg.upper() or "RESOURCE_EXHAUSTED" in msg.upper():
            result = "RATE_LIMITED"
        elif code in (401, 403) or "API KEY" in msg.upper() or "UNAUTHORIZED" in msg.upper():
            result = "INVALID"
        elif "CONNECT" in msg.upper() or "TIMEOUT" in msg.upper():
            result = "UNAVAILABLE"
        else:
            result = "UNKNOWN"
        detail = f"{type(e).__name__}: {msg[:200]}"

    c.is_valid = result == "VALID"
    c.last_tested_at = datetime.now(timezone.utc)
    credential_runtime.mark_test(c.provider_name, c.id, result)
    db.commit()

    log_admin_audit(db, current_user, "TEST_AI_CREDENTIAL", "AI_CREDENTIAL", {
        "id": c.id, "provider": c.provider_name, "result": result,
        # detail may contain a provider message; raw key never appears in it
    })
    return {"id": c.id, "result": result, "detail": detail, "consumes_quota": c.provider_name != "ollama"}


@router.post("/credentials/{credential_id}/recheck")
def recheck_credential(
    credential_id: str,
    current_user: User = Depends(require_permission(PERM_AI_FAILOVER)),
    db: Session = Depends(get_db),
):
    """Clear cooldown so the next real request re-probes the credential.
    Automatic recovery also happens at cooldown expiry — this is a manual
    accelerant, never a fake quota reset."""
    c = db.query(AiCredential).filter(AiCredential.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    credential_runtime.recheck(c.provider_name, c.id)
    credential_registry.invalidate()
    log_admin_audit(db, current_user, "RECHECK_AI_CREDENTIAL", "AI_CREDENTIAL", {"id": c.id})
    return {"id": c.id, "message": "Credential cleared for automatic recheck on next request"}


@router.post("/credentials/{credential_id}/rotate")
def rotate_credential(
    credential_id: str,
    current_user: User = Depends(require_permission(PERM_AI_FAILOVER)),
    db: Session = Depends(get_db),
):
    """Move this credential to lowest rotation priority so the next eligible
    credential of the same provider is preferred."""
    c = db.query(AiCredential).filter(AiCredential.id == credential_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Credential not found")
    max_prio = db.query(func.max(AiCredential.priority)).filter(
        AiCredential.provider_name == c.provider_name
    ).scalar() or 1
    c.priority = int(max_prio) + 1
    db.commit()
    credential_registry.invalidate()
    log_admin_audit(db, current_user, "ROTATE_AI_CREDENTIAL", "AI_CREDENTIAL", {
        "id": c.id, "new_priority": c.priority,
    })
    return {"id": c.id, "priority": c.priority, "message": "Credential moved to lowest priority"}
