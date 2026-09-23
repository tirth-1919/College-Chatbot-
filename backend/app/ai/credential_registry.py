"""
Database-backed multi-credential registry with live state, TTL cache and
secret encryption at rest.

Design notes
------------
* Credentials live in the `ai_credentials` table (encrypted api_key column).
* The router reads the LATEST state at request time: a short-TTL cache avoids
  a DB hit per request, and every admin mutation calls `invalidate()` so new /
  changed / deleted keys are visible to the very next request — NO restart.
* Raw keys are NEVER returned by any accessor. Only masked forms are exposed.
* Quota information is never fabricated: quota values are UNKNOWN unless the
  provider itself reports them. We only track what the provider told us via
  responses (429 / Retry-After) — cooldowns, not invented remaining counts.
"""
import base64
import hashlib
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.ai.provider_state import (
    ProviderRuntimeState,
    QuotaStatus,
    is_quota_error,
    is_permanent_config_error,
    extract_retry_after,
)

# --------------------------------------------------------------------------- #
# Secret encryption at rest (Fernet when available, stdlib fallback otherwise)
# --------------------------------------------------------------------------- #
try:
    from cryptography.fernet import Fernet

    def _get_cipher():
        digest = hashlib.sha256(
            (getattr(settings, "SECRET_KEY", "") + "|ait-credential-encryption").encode()
        ).digest()
        return Fernet(base64.urlsafe_b64encode(digest))

    def encrypt_secret(plain: str) -> str:
        if not plain:
            return ""
        return _get_cipher().encrypt(plain.encode()).decode()

    def decrypt_secret(token: str) -> str:
        if not token:
            return ""
        return _get_cipher().decrypt(token.encode()).decode()

except ImportError as exc:  # pragma: no cover - deployment dependency failure
    raise RuntimeError(
        "The cryptography package is required for encrypted AI credentials"
    ) from exc


def mask_key(plain: str) -> str:
    """Masked display form: last 4 chars only. Never the full secret."""
    if not plain:
        return ""
    return "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022" + plain[-4:]


# Classification boundaries for bounded exponential cooldowns (seconds)
MIN_COOLDOWN_SECONDS = 30
MAX_COOLDOWN_SECONDS = int(getattr(settings, "PROVIDER_MAX_COOLDOWN_SECONDS", 3600))


def classify_failure(status_code: Optional[int], message: str) -> str:
    """
    Centralized failure classification. Never lumps everything into 'quota'.
    """
    text = (message or "").upper()
    code = status_code or 0
    if code == 401 or "INVALID API KEY" in text or "API KEY NOT VALID" in text or "UNAUTHORIZED" in text:
        return "API_KEY_INVALID"
    if code == 403 or "FORBIDDEN" in text or "PERMISSION DENIED" in text:
        return "AUTHORIZATION_ERROR"
    if code == 404 or "NOT FOUND" in text or "INVALID MODEL" in text:
        return "MODEL_UNAVAILABLE"
    if code == 429 or "RATE_LIMIT" in text or "TOO_MANY_REQUESTS" in text:
        # Distinguish short rate-limit vs quota exhaustion on evidence
        if "QUOTA" in text or "RESOURCE_EXHAUSTED" in text:
            return "QUOTA_EXHAUSTED"
        return "RATE_LIMITED"
    if code >= 500:
        return "PROVIDER_ERROR"
    if code == 408 or "TIMEOUT" in text:
        return "TIMEOUT"
    if code == -1 or "CONNECT" in text or "UNREACHABLE" in text or "NETWORK" in text:
        return "UNREACHABLE"
    return "UNKNOWN_ERROR"


def cooldown_for_failure(failure_type: str, retry_after: Optional[int] = None,
                         attempt: int = 0) -> Optional[int]:
    """
    Bounded cooldown seconds for a failure type. Honors provider Retry-After.
    Returns None for non-cooldown failures (auth/404).
    """
    if failure_type in ("API_KEY_INVALID", "AUTHORIZATION_ERROR"):
        return None  # permanent — admin must fix, cooldowns would fake recovery
    if failure_type == "MODEL_UNAVAILABLE":
        return min(MAX_COOLDOWN_SECONDS, 120)
    if failure_type in ("QUOTA_EXHAUSTED", "RATE_LIMITED"):
        base = max(0, int(getattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)))
        if retry_after:
            return min(MAX_COOLDOWN_SECONDS, int(retry_after))
        # bounded exponential: 300, 600, 1200 ... capped
        return min(MAX_COOLDOWN_SECONDS, base * (2 ** min(attempt, 3)))
    if failure_type == "PROVIDER_ERROR":
        return min(300, 60 * (2 ** min(attempt, 2)))
    if failure_type in ("TIMEOUT", "UNREACHABLE"):
        return max(0, int(getattr(settings, "PROVIDER_HEALTH_CHECK_INTERVAL", 60)))
    return MIN_COOLDOWN_SECONDS


class CredentialRuntimeState:
    """
    In-memory live state per provider+credential(+model optional).
    Atomic under a process lock — shared by all concurrent requests so a
    stampede does not re-discover the same exhausted key repeatedly.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._states: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _key(provider: str, credential_id: str, model: Optional[str] = None) -> str:
        base = f"{(provider or '').lower()}|{credential_id}"
        return f"{base}|{model}" if model else base

    def get(self, provider: str, credential_id: str, model: Optional[str] = None) -> Dict[str, Any]:
        key = self._key(provider, credential_id, model)
        with self._lock:
            if key not in self._states:
                self._states[key] = {
                    "runtime_state": ProviderRuntimeState.UNKNOWN.value,
                    "cooldown_until": None,
                    "failure_type": None,
                    "last_error": None,
                    "attempt": 0,
                    "requests_total": 0,
                    "requests_success": 0,
                    "requests_failed": 0,
                    "rate_limit_429_count": 0,
                    "timeout_count": 0,
                    "server_error_count": 0,
                    "last_used_at": None,
                    "last_success_at": None,
                    "last_failure_at": None,
                }
            return self._states[key]

    def _set(self, provider: str, credential_id: str, model: Optional[str],
             updates: Dict[str, Any]) -> Dict[str, Any]:
        state = self.get(provider, credential_id, model)
        with self._lock:
            state.update(updates)
            return state

    def is_eligible(self, provider: str, credential_id: str, model: Optional[str] = None) -> bool:
        state = self.get(provider, credential_id, model)
        cd = state.get("cooldown_until")
        if cd:
            if isinstance(cd, str):
                try:
                    cd = datetime.fromisoformat(cd)
                except ValueError:
                    cd = None
            if cd and cd.tzinfo is None:
                cd = cd.replace(tzinfo=timezone.utc)
            if cd and datetime.now(timezone.utc) < cd:
                return False
        return state.get("runtime_state") not in (
            ProviderRuntimeState.API_KEY_MISSING.value,
            ProviderRuntimeState.DISABLED.value,
        ) and state.get("failure_type") not in ("API_KEY_INVALID",)

    def mark_success(self, provider: str, credential_id: str, model: Optional[str] = None):
        now = datetime.now(timezone.utc)
        self._set(provider, credential_id, model, {
            "runtime_state": ProviderRuntimeState.AVAILABLE.value,
            "cooldown_until": None,
            "failure_type": None,
            "last_error": None,
            "attempt": 0,
            "last_success_at": now,
            "last_used_at": now,
        })

    def mark_failure(self, provider: str, credential_id: str, model: Optional[str],
                     status_code: Optional[int], message: str) -> Dict[str, Any]:
        failure_type = classify_failure(status_code, message)
        retry_after = extract_retry_after(Exception(message))
        state = self.get(provider, credential_id, model)
        attempt = int(state.get("attempt", 0))
        seconds = cooldown_for_failure(failure_type, retry_after, attempt)
        now = datetime.now(timezone.utc)
        updates: Dict[str, Any] = {
            "failure_type": failure_type,
            "last_error": (message or "")[:500],
            "attempt": attempt + 1,
            "last_failure_at": now,
            "last_used_at": now,
            "runtime_state": failure_type,
        }
        if seconds is not None:
            updates["cooldown_until"] = now + timedelta(seconds=seconds)
        updates["requests_total"] = int(state.get("requests_total", 0)) + 1
        updates["requests_failed"] = int(state.get("requests_failed", 0)) + 1
        if failure_type in ("QUOTA_EXHAUSTED", "RATE_LIMITED"):
            updates["rate_limit_429_count"] = int(state.get("rate_limit_429_count", 0)) + 1
        if failure_type == "TIMEOUT":
            updates["timeout_count"] = int(state.get("timeout_count", 0)) + 1
        if failure_type == "PROVIDER_ERROR":
            updates["server_error_count"] = int(state.get("server_error_count", 0)) + 1
        return self._set(provider, credential_id, model, updates)

    def mark_test(self, provider: str, credential_id: str, result: str):
        mapping = {
            "VALID": ProviderRuntimeState.AVAILABLE.value,
            "INVALID": ProviderRuntimeState.API_KEY_INVALID.value,
            "RATE_LIMITED": ProviderRuntimeState.RATE_LIMITED.value,
            "UNAVAILABLE": ProviderRuntimeState.UNREACHABLE.value,
            "UNKNOWN": ProviderRuntimeState.UNKNOWN.value,
        }
        updates: Dict[str, Any] = {"runtime_state": mapping.get(result, ProviderRuntimeState.UNKNOWN.value)}
        if result == "VALID":
            updates.update({"cooldown_until": None, "failure_type": None, "attempt": 0})
        if result == "INVALID":
            updates["failure_type"] = "API_KEY_INVALID"
        self._set(provider, credential_id, None, updates)

    def recheck(self, provider: str, credential_id: str):
        """Automatic recovery probe marker: clear cooldown so next request retries."""
        with self._lock:
                for state_key, state in self._states.items():
                    if state_key.startswith(f"{provider.lower()}|{credential_id}"):
                        state["cooldown_until"] = None
                        state["attempt"] = 0
                        if state.get("runtime_state") in (
                            ProviderRuntimeState.RATE_LIMITED.value,
                            ProviderRuntimeState.QUOTA_EXHAUSTED.value,
                            ProviderRuntimeState.UNREACHABLE.value,
                        ):
                            state["runtime_state"] = ProviderRuntimeState.UNKNOWN.value

    def snapshot(self, provider: str, credential_id: str, model: Optional[str] = None) -> Dict[str, Any]:
        state = dict(self.get(provider, credential_id, model))
        cd = state.get("cooldown_until")
        now = datetime.now(timezone.utc)
        cooldown_active = bool(cd and now < cd)
        runtime = state.get("runtime_state") or ProviderRuntimeState.UNKNOWN.value
        if cooldown_active:
            # Active cooldown: show the recorded failure state (QUOTA_EXHAUSTED,
            # RATE_LIMITED, UNREACHABLE...) or generic COOLDOWN.
            if runtime in (ProviderRuntimeState.UNKNOWN.value, ProviderRuntimeState.AVAILABLE.value):
                runtime = ProviderRuntimeState.COOLDOWN.value
        else:
            # Cooldown expired → automatic re-evaluation: transient failures
            # become retryable (AVAILABLE on next attempt). Permanent failures
            # (invalid key) stay flagged until the admin fixes the credential.
            if state.get("failure_type") in ("API_KEY_INVALID", "AUTHORIZATION_ERROR"):
                runtime = state.get("runtime_state")
            else:
                runtime = ProviderRuntimeState.AVAILABLE.value if runtime != ProviderRuntimeState.DISABLED.value else runtime
        return {
            "runtime_state": runtime,
            "quota_status": (
                QuotaStatus.EXHAUSTED.value
                if state.get("runtime_state") == ProviderRuntimeState.QUOTA_EXHAUSTED.value and cooldown_active
                else QuotaStatus.UNKNOWN.value
            ),
            "quota_remaining": "UNKNOWN",
            "quota_reason": "Provider does not expose reliable quota metadata.",
            "cooldown_until": cd.isoformat() if isinstance(cd, datetime) else cd,
            "cooldown_active": cooldown_active,
            "failure_type": state.get("failure_type"),
            "last_error": state.get("last_error"),
            "requests_total": state.get("requests_total", 0),
            "requests_success": state.get("requests_success", 0),
            "requests_failed": state.get("requests_failed", 0),
            "rate_limit_429_count": state.get("rate_limit_429_count", 0),
            "timeout_count": state.get("timeout_count", 0),
            "server_error_count": state.get("server_error_count", 0),
            "last_used_at": state.get("last_used_at").isoformat() if isinstance(state.get("last_used_at"), datetime) else None,
            "last_success_at": state.get("last_success_at").isoformat() if isinstance(state.get("last_success_at"), datetime) else None,
            "last_failure_at": state.get("last_failure_at").isoformat() if isinstance(state.get("last_failure_at"), datetime) else None,
        }


# --------------------------------------------------------------------------- #
# DB-backed registry with TTL cache + explicit invalidation
# --------------------------------------------------------------------------- #
class CredentialRegistry:
    """Reads latest credentials from DB, cached for a very short TTL.

    Any admin mutation calls invalidate() → next request re-reads the DB.
    The cache is intentionally tiny (default 5s) — it exists to avoid a DB
    round-trip per request, never to keep stale eligibility.
    """

    def __init__(self, ttl_seconds: float = 5.0):
        self.ttl = ttl_seconds
        self._cache: Dict[str, List[Dict[str, Any]]] = {}  # provider -> rows
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def invalidate(self):
        with self._lock:
            self._cache.clear()
            self._loaded_at = 0.0

    def get_latest(self, db=None) -> List[Dict[str, Any]]:
        """All credential rows fresh from DB (TTL-bounded).

        Opens its OWN session when the caller's session is unavailable or
        unsuitable — the registry must always read the latest committed state
        regardless of the caller's transaction. Failure-safe: any DB problem
        yields an empty registry (legacy env-key behavior), never a broken
        request path.
        """
        with self._lock:
            if self._cache and (time.monotonic() - self._loaded_at) < self.ttl:
                return [r for rows_ in self._cache.values() for r in rows_]
            rows = self._load_from(db)
            if rows is None:
                from backend.app.core.database import SessionLocal
                session = SessionLocal()
                try:
                    rows = self._load_from(session) or []
                except Exception:
                    rows = []
                finally:
                    session.close()
            self._cache = {"all": rows}
            self._loaded_at = time.monotonic()
            return rows

    @staticmethod
    def _load_from(db):
        try:
            from backend.app.models.admin_system import AiCredential
            creds = db.query(AiCredential).all()
            rows = []
            for c in creds:
                if not isinstance(c, AiCredential):
                    continue
                rows.append(CredentialRegistry._row(c))
            return rows
        except Exception:
            return None

    @staticmethod
    def _row(c) -> Dict[str, Any]:
        return {
            "id": c.id,
            "provider_name": (c.provider_name or "").lower(),
            "label": c.label,
            "masked": c.masked_key,
            "priority": c.priority,
            "is_enabled": c.is_enabled,
            "free_tier_status": c.free_tier_status,
        }

    def get_for_provider(self, db, provider_name: str) -> List[Dict[str, Any]]:
        """Enabled credentials for a provider, priority order (1 = highest)."""
        name = (provider_name or "").lower()
        rows = [r for r in self.get_latest(db)
                if r["provider_name"] == name and r["is_enabled"]]
        rows.sort(key=lambda r: (r["priority"], r["id"]))
        return rows

    def get_decrypted(self, db, credential_id: str) -> Optional[str]:
        """Server-side only: decrypt one credential for provider call. NEVER logged."""
        from backend.app.core.database import SessionLocal
        from backend.app.models.admin_system import AiCredential
        session = SessionLocal()
        try:
            c = session.query(AiCredential).filter(AiCredential.id == credential_id).first()
            if not c:
                return None
            try:
                return decrypt_secret(c.api_key_encrypted)
            except Exception:
                return None
        finally:
            session.close()


credential_runtime = CredentialRuntimeState()
credential_registry = CredentialRegistry()
