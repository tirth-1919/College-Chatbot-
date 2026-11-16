"""Admin AI Provider Monitoring & Runtime Configuration Endpoints.

Provides read-only visibility into provider/model health and usage, and allows
in-memory runtime configuration updates (no DB writes needed for in-memory state).

API Keys are NEVER returned or accepted by any endpoint in this router.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.core.config import settings
from app.dependencies.auth import require_college_admin
from app.models.user import User
from app.services.provider_health import provider_health_tracker

router = APIRouter(prefix="/admin/ai-providers", tags=["Admin - AI Providers"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class ModelHealthResponse(BaseModel):
    provider: str
    model: str
    status: str
    consecutive_failures: int
    total_failures: int
    total_successes: int
    total_retries: int
    fallback_events: int
    average_latency_ms: float
    request_count: int
    last_error_category: Optional[str] = None
    is_cooling_down: bool


class ProviderStatusResponse(BaseModel):
    models: List[ModelHealthResponse]
    total_models_tracked: int


class ModelUsageResponse(BaseModel):
    provider: str
    model: str
    request_count: int
    avg_latency_ms: float
    total_successes: int
    total_failures: int


class UsageSummaryResponse(BaseModel):
    models: List[ModelUsageResponse]
    active_gemini_models: List[str]
    active_openai_models: List[str]
    active_xkiro_models: List[str]
    general_answering_enabled: bool


class ConfigUpdateRequest(BaseModel):
    gemini_model_priority: Optional[str] = None
    openai_model_priority: Optional[str] = None
    xkiro_model_priority: Optional[str] = None
    ai_max_retries: Optional[int] = None
    ai_timeout_seconds: Optional[int] = None
    ai_cooldown_seconds: Optional[int] = None
    ai_general_answering_enabled: Optional[bool] = None


class ConfigSummaryResponse(BaseModel):
    gemini_model_priority: str
    openai_model_priority: str
    xkiro_model_priority: str
    ai_max_retries: int
    ai_timeout_seconds: int
    ai_cooldown_seconds: int
    ai_circuit_breaker_threshold: int
    ai_general_answering_enabled: bool
    # API keys deliberately omitted


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    response_model=ProviderStatusResponse,
    summary="Per-model provider health status",
)
async def get_provider_status(
    current_user: User = Depends(require_college_admin),
) -> ProviderStatusResponse:
    """Returns circuit-breaker state and health metrics for every tracked model.

    API keys are never included in this response.
    """
    all_health = await provider_health_tracker.get_all_health()
    model_responses = [
        ModelHealthResponse(
            provider=h.provider,
            model=h.model,
            status=h.status(),
            consecutive_failures=h.consecutive_failures,
            total_failures=h.total_failures,
            total_successes=h.total_successes,
            total_retries=h.total_retries,
            fallback_events=h.fallback_events,
            average_latency_ms=round(h.average_latency_ms(), 1),
            request_count=h.request_count,
            last_error_category=h.last_error_category,
            is_cooling_down=h.is_cooling_down,
        )
        for h in all_health.values()
    ]
    return ProviderStatusResponse(
        models=model_responses,
        total_models_tracked=len(model_responses),
    )


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    summary="Per-model usage statistics",
)
async def get_provider_usage(
    current_user: User = Depends(require_college_admin),
) -> UsageSummaryResponse:
    """Returns per-model request counts, average latency, and success/failure totals.

    API keys are never included in this response.
    """
    all_health = await provider_health_tracker.get_all_health()
    usage_rows = [
        ModelUsageResponse(
            provider=h.provider,
            model=h.model,
            request_count=h.request_count,
            avg_latency_ms=round(h.average_latency_ms(), 1),
            total_successes=h.total_successes,
            total_failures=h.total_failures,
        )
        for h in all_health.values()
    ]
    return UsageSummaryResponse(
        models=usage_rows,
        active_gemini_models=settings.gemini_model_list,
        active_openai_models=settings.openai_model_list,
        active_xkiro_models=settings.xkiro_model_list,
        general_answering_enabled=settings.AI_GENERAL_ANSWERING_ENABLED,
    )


@router.put(
    "/config",
    response_model=ConfigSummaryResponse,
    summary="Update AI provider runtime configuration",
)
async def update_provider_config(
    body: ConfigUpdateRequest,
    current_user: User = Depends(require_college_admin),
) -> ConfigSummaryResponse:
    """Applies in-memory runtime configuration changes to the settings singleton.

    Changes take effect immediately but are NOT persisted across process restarts.
    Set the corresponding environment variables for permanent changes.

    API keys are never accepted or returned by this endpoint.
    """
    if body.gemini_model_priority is not None:
        settings.GEMINI_MODEL_PRIORITY = body.gemini_model_priority

    if body.openai_model_priority is not None:
        settings.OPENAI_MODEL_PRIORITY = body.openai_model_priority

    if body.xkiro_model_priority is not None:
        settings.XKIRO_MODEL_PRIORITY = body.xkiro_model_priority

    if body.ai_max_retries is not None:
        settings.AI_MAX_RETRIES = body.ai_max_retries

    if body.ai_timeout_seconds is not None:
        settings.AI_TIMEOUT_SECONDS = body.ai_timeout_seconds

    if body.ai_cooldown_seconds is not None:
        settings.AI_COOLDOWN_SECONDS = body.ai_cooldown_seconds

    if body.ai_general_answering_enabled is not None:
        settings.AI_GENERAL_ANSWERING_ENABLED = body.ai_general_answering_enabled

    return ConfigSummaryResponse(
        gemini_model_priority=settings.GEMINI_MODEL_PRIORITY,
        openai_model_priority=settings.OPENAI_MODEL_PRIORITY,
        xkiro_model_priority=settings.XKIRO_MODEL_PRIORITY,
        ai_max_retries=settings.AI_MAX_RETRIES,
        ai_timeout_seconds=settings.AI_TIMEOUT_SECONDS,
        ai_cooldown_seconds=settings.AI_COOLDOWN_SECONDS,
        ai_circuit_breaker_threshold=settings.AI_CIRCUIT_BREAKER_THRESHOLD,
        ai_general_answering_enabled=settings.AI_GENERAL_ANSWERING_ENABLED,
    )
