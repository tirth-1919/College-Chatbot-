"""
Automatic multi-provider quota/rate-limit state management.

This module tracks runtime usability of every provider/model so the AIRouter
can skip candidates that are currently unusable before spending a network
attempt on them:

  - API key configured / missing (never exposes the secret itself)
  - quota / rate-limit cooldowns (honouring provider Retry-After)
  - circuit-breaker state (delegates to the existing circuit_breaker)
  - unreachable / configuration-error states

It deliberately does NOT fabricate provider quota numbers. Quota information
is one of: VERIFIED (provider reported), EXHAUSTED (provider returned 429),
UNKNOWN, or NOT_APPLICABLE (local-only providers such as Ollama).
"""
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

from backend.app.core.config import settings
from backend.app.ai.circuit_breaker import circuit_breaker, FailureType


class ProviderRuntimeState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DISABLED = "DISABLED"
    API_KEY_MISSING = "API_KEY_MISSING"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    RATE_LIMITED = "RATE_LIMITED"
    COOLDOWN = "COOLDOWN"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    UNREACHABLE = "UNREACHABLE"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    UNKNOWN = "UNKNOWN"


class QuotaStatus(str, Enum):
    VERIFIED = "VERIFIED"                # provider exposed authoritative quota
    EXHAUSTED = "EXHAUSTED"              # provider returned 429 / QUOTA_EXCEEDED
    UNKNOWN = "UNKNOWN"                  # no authoritative info available
    NOT_APPLICABLE = "NOT_APPLICABLE"    # provider does not use API quotas (e.g. Ollama)


# Provider-level API key env var defaults (never the values themselves).
DEFAULT_API_KEY_ENV = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    # Ollama requires no API key
}

KEY_NOT_REQUIRED_PROVIDERS = {"ollama"}


def is_quota_error(status_code: Optional[int], message: str) -> bool:
    """Failover-eligible quota / rate-limit classification."""
    text = (message or "").upper()
    if status_code == 429:
        return True
    return any(marker in text for marker in (
        "RATE_LIMIT", "RATE LIMIT", "RATE_LIMIT_429", "RESOURCE_EXHAUSTED",
        "QUOTA_EXCEEDED", "TOO_MANY_REQUESTS", "TOO MANY REQUESTS",
    ))


def is_permanent_config_error(status_code: Optional[int], message: str) -> bool:
    """Errors that should not trigger endless rotation (401/403/400/invalid model)."""
    if status_code in (400, 401, 403, 404):
        return True
    text = (message or "").lower()
    return any(marker in text for marker in (
        "unauthorized", "invalid api key", "api key not valid",
        "permission denied", "malformed", "invalid model",
        "not configured",
    ))


def extract_retry_after(error: Exception) -> Optional[int]:
    """Best-effort Retry-After extraction (seconds) from an exception."""
    for attr in ("retry_after", "retry_after_seconds"):
        value = getattr(error, attr, None)
        if value:
            try:
                return int(float(value))
            except (TypeError, ValueError):
                pass
    headers = getattr(error, "headers", None) or {}
    headers = {str(k).lower(): v for k, v in headers.items()}
    raw = headers.get("retry-after")
    if raw:
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            pass
    # httpx/httpcore style exception chains may carry a response object
    response = getattr(error, "response", None)
    if response is not None:
        try:
            raw = response.headers.get("retry-after")
            if raw:
                return int(float(raw))
        except Exception:
            pass
    return None


class ProviderStateManager:
    """In-memory runtime state registry for provider/model candidates."""

    def __init__(self):
        # key: f"{provider_name}/{model_identifier}"
        self._states: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _key(provider_name: str, model_identifier: str) -> str:
        return f"{(provider_name or '').lower()}/{model_identifier}"

    def get_state(self, provider_name: str, model_identifier: str) -> Dict[str, Any]:
        key = self._key(provider_name, model_identifier)
        if key not in self._states:
            self._states[key] = {
                "runtime_state": ProviderRuntimeState.UNKNOWN,
                "cooldown_until": None,
                "retry_after": None,
                "last_error": None,
                "last_error_type": None,
                "last_failure_at": None,
                "failover_count": 0,
            }
        return self._states[key]

    def get_provider_state(self, provider_name: str) -> Dict[str, Any]:
        """Provider/project state shared by all of its models in this worker."""
        return self.get_state(provider_name, "__provider__")

    def mark_provider_cooldown(self, provider_name: str, runtime_state: ProviderRuntimeState,
                               retry_after: Optional[int] = None, error: Optional[str] = None) -> None:
        state = self.get_provider_state(provider_name)
        base = max(0, int(getattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)))
        state.update({
            "runtime_state": runtime_state,
            "last_error_type": runtime_state.value,
            "last_error": error,
            "last_failure_at": datetime.now(timezone.utc),
            "retry_after": retry_after,
            "cooldown_until": datetime.now(timezone.utc) + timedelta(seconds=max(base, retry_after or 0)),
        })
        state["failover_count"] += 1

    # ------------------------------------------------------------------ #
    # API key status (status only, never values)
    # ------------------------------------------------------------------ #
    @staticmethod
    def get_api_key_status(provider_name: str, api_key_env: Optional[str] = None) -> Dict[str, Any]:
        """
        Configuration status only — never returns the secret value itself.
        Detects keys from the process environment and from .env via settings.
        """
        name = (provider_name or "").lower()
        if name in KEY_NOT_REQUIRED_PROVIDERS:
            return {"status": "NOT_REQUIRED", "key_source": "none", "configured": True}
        env_var = api_key_env or DEFAULT_API_KEY_ENV.get(name, "")
        # The key may come from the process environment OR from .env (loaded by
        # pydantic-settings into `settings`). Check both; return status only.
        configured = bool(os.getenv(env_var, "") or getattr(settings, env_var, "")) if env_var else False
        return {
            "status": "CONFIGURED" if configured else "NOT_CONFIGURED",
            "key_source": env_var or "unknown",
            "configured": configured,
        }

    # ------------------------------------------------------------------ #
    # Candidate evaluation
    # ------------------------------------------------------------------ #
    def evaluate_candidate(
        self,
        provider_name: str,
        model_identifier: str,
        provider_enabled: bool,
        model_enabled: bool,
        api_key_env: Optional[str] = None,
        require_api_key: bool = True,
    ) -> Dict[str, Any]:
        """
        Determine whether a candidate should be attempted.
        Returns dict with: usable, runtime_state, quota_status, cooldown_until, reason.
        """
        now = datetime.now(timezone.utc)
        state = self.get_state(provider_name, model_identifier)

        provider_state = self.get_provider_state(provider_name)

        if not provider_enabled or not model_enabled:
            return self._result(state, ProviderRuntimeState.DISABLED, QuotaStatus.UNKNOWN, None,
                                "Provider or model is disabled")

        api_key_status = self.get_api_key_status(provider_name, api_key_env)
        if require_api_key and not api_key_status["configured"]:
            return self._result(state, ProviderRuntimeState.API_KEY_MISSING, QuotaStatus.UNKNOWN, None,
                                f"API key not configured ({api_key_status['key_source']})")

        provider_cooldown = provider_state.get("cooldown_until")
        if provider_cooldown and now < provider_cooldown:
            runtime = provider_state.get("runtime_state") or ProviderRuntimeState.COOLDOWN
            return self._result(provider_state, runtime, self._quota_status(provider_state), provider_cooldown,
                                provider_state.get("last_error_type") or "PROVIDER_COOLDOWN")

        # Circuit breaker (existing shared instance)
        if not circuit_breaker.can_execute(model_identifier):
            cb = circuit_breaker.get_state(model_identifier)
            return self._result(state, ProviderRuntimeState.CIRCUIT_OPEN, self._quota_status(state),
                                cb.get("cooldown_until"), f"Circuit breaker {cb.get('state')}")

        # Quota / rate-limit cooldown
        cooldown_until = state.get("cooldown_until")
        if cooldown_until and now < cooldown_until:
            runtime = state.get("runtime_state") or ProviderRuntimeState.COOLDOWN
            if runtime not in (ProviderRuntimeState.QUOTA_EXHAUSTED, ProviderRuntimeState.RATE_LIMITED):
                runtime = ProviderRuntimeState.COOLDOWN
            return self._result(state, runtime, self._quota_status(state), cooldown_until,
                                state.get("last_error_type") or "COOLDOWN")

        return self._result(state, ProviderRuntimeState.AVAILABLE, self._quota_status(state), None, None)

    @staticmethod
    def _quota_status(state: Dict[str, Any]) -> QuotaStatus:
        runtime = state.get("runtime_state")
        if runtime in (ProviderRuntimeState.QUOTA_EXHAUSTED, ProviderRuntimeState.RATE_LIMITED):
            return QuotaStatus.EXHAUSTED
        return QuotaStatus.UNKNOWN

    @staticmethod
    def _result(state: Dict[str, Any], runtime: ProviderRuntimeState, quota: QuotaStatus,
                cooldown_until, reason) -> Dict[str, Any]:
        return {
            "usable": runtime == ProviderRuntimeState.AVAILABLE,
            "runtime_state": runtime,
            "quota_status": quota,
            "cooldown_until": cooldown_until,
            "reason": reason,
        }

    # ------------------------------------------------------------------ #
    # State recording
    # ------------------------------------------------------------------ #
    def mark_quota_exhausted(self, provider_name: str, model_identifier: str,
                             retry_after: Optional[int] = None) -> None:
        state = self.get_state(provider_name, model_identifier)
        state["runtime_state"] = ProviderRuntimeState.QUOTA_EXHAUSTED
        state["last_error_type"] = FailureType.RATE_LIMIT_429.value
        state["last_failure_at"] = datetime.now(timezone.utc)
        state["failover_count"] += 1
        state["retry_after"] = retry_after
        base = max(0, int(getattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)))
        cooldown = max(base, retry_after or 0)
        state["cooldown_until"] = datetime.now(timezone.utc) + timedelta(seconds=cooldown)

    def mark_success(self, provider_name: str, model_identifier: str) -> None:
        state = self.get_state(provider_name, model_identifier)
        state["runtime_state"] = ProviderRuntimeState.AVAILABLE
        state["cooldown_until"] = None
        state["retry_after"] = None
        state["last_error"] = None
        state["last_error_type"] = None

    def mark_unreachable(self, provider_name: str, model_identifier: str,
                         error: Optional[str] = None) -> None:
        state = self.get_state(provider_name, model_identifier)
        state["runtime_state"] = ProviderRuntimeState.UNREACHABLE
        state["last_error"] = error
        state["last_error_type"] = FailureType.NETWORK_ERROR.value
        state["last_failure_at"] = datetime.now(timezone.utc)
        base = max(0, int(getattr(settings, "PROVIDER_HEALTH_CHECK_INTERVAL", 60)))
        state["cooldown_until"] = datetime.now(timezone.utc) + timedelta(seconds=base)

    def mark_configuration_error(self, provider_name: str, model_identifier: str,
                                 error: Optional[str] = None) -> None:
        state = self.get_state(provider_name, model_identifier)
        state["runtime_state"] = ProviderRuntimeState.CONFIGURATION_ERROR
        state["last_error"] = error
        state["last_error_type"] = FailureType.AUTH_FAILURE.value
        state["last_failure_at"] = datetime.now(timezone.utc)

    def mark_error(self, provider_name: str, model_identifier: str,
                   error_type: str, error: Optional[str] = None) -> None:
        state = self.get_state(provider_name, model_identifier)
        state["runtime_state"] = ProviderRuntimeState.UNKNOWN
        state["last_error"] = error
        state["last_error_type"] = error_type
        state["last_failure_at"] = datetime.now(timezone.utc)

    def reset_state(self, provider_name: str, model_identifier: str) -> None:
        self._states.pop(self._key(provider_name, model_identifier), None)

    # ------------------------------------------------------------------ #
    # Snapshot for the admin API
    # ------------------------------------------------------------------ #
    def snapshot(self, provider_name: str, model_identifier: str) -> Dict[str, Any]:
        state = self.get_state(provider_name, model_identifier)
        runtime = state.get("runtime_state") or ProviderRuntimeState.UNKNOWN
        cooldown_until = state.get("cooldown_until")
        now = datetime.now(timezone.utc)
        # Cooldown expiry turns the state usable again for the next attempt
        if cooldown_until and now >= cooldown_until:
            runtime = ProviderRuntimeState.AVAILABLE
        return {
            "runtime_state": runtime.value,
            "quota_status": (
                QuotaStatus.EXHAUSTED.value
                if runtime in (ProviderRuntimeState.QUOTA_EXHAUSTED, ProviderRuntimeState.RATE_LIMITED)
                else QuotaStatus.UNKNOWN.value
            ),
            "cooldown_until": cooldown_until.isoformat() if cooldown_until else None,
            "cooldown_active": bool(cooldown_until and now < cooldown_until),
            "retry_after": state.get("retry_after"),
            "last_error": state.get("last_error"),
            "last_error_type": state.get("last_error_type"),
            "last_failure_at": state.get("last_failure_at").isoformat() if state.get("last_failure_at") else None,
            "failover_count": state.get("failover_count", 0),
        }


provider_state_manager = ProviderStateManager()
