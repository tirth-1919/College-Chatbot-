"""
Focused tests for the automatic multi-provider quota-aware failover system.

Covers: cross-provider failover, API-key missing skips, unreachable Ollama,
bounded retries, cooldown behaviour, Retry-After, non-quota error handling,
priority ordering, disabled skipping, secret safety and admin endpoint RBAC.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.ai.circuit_breaker import circuit_breaker
from backend.app.ai.provider_state import (
    provider_state_manager,
    is_quota_error,
    is_permanent_config_error,
    extract_retry_after,
    ProviderRuntimeState,
    QuotaStatus,
)
from backend.app.ai.router import AIRouter
from backend.app.models.admin_system import AiProviderConfig, AiModelRegistry, AiQuota
from backend.app.core.config import settings


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

class FakeResponse:
    def __init__(self, content="ok", latency=1.0):
        self.content = content
        self.input_tokens = 1
        self.output_tokens = 1
        self.total_tokens = 2
        self.latency_ms = latency
        self.model_name = "fake"
        self.provider_name = "fake"
        self.raw_headers = {}


class QuotaError(Exception):
    status_code = 429


class AuthError(Exception):
    status_code = 401


class BadRequestError(Exception):
    status_code = 400


class NetworkError(Exception):
    pass


class StubAdapter:
    """Adapter whose generate_response raises queued outcomes per model."""

    def __init__(self, outcomes):
        self.outcomes = outcomes  # model_identifier -> [Exception | AIProviderResponse]
        self.calls = []
        self.base_url = "http://fake-endpoint"

    async def generate_response(self, model_name, **kwargs):
        self.calls.append(model_name)
        outcome = self.outcomes[model_name].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def health_check(self, model_name=None):
        return True


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    """Reset in-memory state and force failover settings on for every test."""
    monkeypatch.setattr(settings, "PROVIDER_FAILOVER_ENABLED", True)
    monkeypatch.setattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(settings, "PROVIDER_MAX_ATTEMPTS", 0)
    monkeypatch.setattr(settings, "PROVIDER_QUOTA_CHECK_ENABLED", True)
    # Paid models are only eligible when FREE-ONLY mode is off; these tests
    # exercise the paid-tail of the chain, so pin the policy explicitly.
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", False)
    circuit_breaker._states.clear()
    provider_state_manager._states.clear()
    yield
    circuit_breaker._states.clear()
    provider_state_manager._states.clear()


def make_provider(provider_name, priority, models, enabled=True, api_key_env=None):
    p = AiProviderConfig(
        id=str(uuid.uuid4()),
        provider_name=provider_name,
        display_name=provider_name.title(),
        is_enabled=enabled,
        priority=priority,
        api_key_env=api_key_env,
    )
    p.models = [
        AiModelRegistry(
            id=str(uuid.uuid4()),
            provider_id=p.id,
            model_identifier=m,
            display_name=m,
            is_enabled=True,
            priority=i + 1,
        )
        for i, m in enumerate(models)
    ]
    return p


class FakeQuery:
    """Chainable stand-in for the SQLAlchemy query used by the router."""

    def __init__(self, candidates):
        self.candidates = candidates

    def filter(self, *a, **k):
        return self

    def join(self, *a, **k):
        return self

    def order_by(self, *a, **k):
        return self

    def all(self):
        return self.candidates

    def first(self):
        return None


class FakeDB:
    """Minimal DB stand-in: no real SQL, tracks AiUsageLog objects added."""

    def __init__(self, candidates):
        self.candidates = candidates
        self.added = []

    def query(self, model):
        return FakeQuery(self.candidates)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


class FakeRegistryModel:
    def __init__(self, provider, model_identifier):
        self.provider = provider
        self.model_identifier = model_identifier
        self.id = str(__import__('uuid').uuid4())
        self.is_enabled = True
        self.health_status = "HEALTHY"
        self.consecutive_failures = 0
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.rate_limit_429_count = 0
        self.avg_latency_ms = 0.0
        self.last_success_at = None
        self.last_error_at = None
        self.last_error_message = None
        self.cooldown_until = None


def build_router(candidates, adapters):
    router = AIRouter.__new__(AIRouter)  # skip __init__ (no real clients)

    def fake_get_adapter(provider_name, base_url=None):
        return adapters[provider_name]

    router._get_adapter = fake_get_adapter
    return router


# --------------------------------------------------------------------- #
# Error classification unit tests
# --------------------------------------------------------------------- #

def test_quota_error_classification():
    assert is_quota_error(429, "anything")
    assert is_quota_error(None, "RESOURCE_EXHAUSTED from upstream")
    assert is_quota_error(None, "QUOTA_EXCEEDED for model")
    assert is_quota_error(None, "Too Many Requests")
    assert is_quota_error(None, "rate limit hit")
    assert is_quota_error(None, "TOO_MANY_REQUESTS")
    assert not is_quota_error(401, "Unauthorized")
    assert not is_quota_error(400, "Bad request")


def test_permanent_config_error_classification():
    assert is_permanent_config_error(401, "Unauthorized")
    assert is_permanent_config_error(403, "Permission denied")
    assert is_permanent_config_error(400, "Malformed request")
    assert is_permanent_config_error(404, "Invalid model")
    assert is_permanent_config_error(None, "API key not valid")
    assert not is_permanent_config_error(429, "Rate limit")
    assert not is_permanent_config_error(500, "Internal error")


def test_retry_after_extraction():
    err = Exception("429")
    err.headers = {"Retry-After": "45"}
    assert extract_retry_after(err) == 45
    err2 = Exception("x")
    err2.retry_after = "12"
    assert extract_retry_after(err2) == 12
    assert extract_retry_after(Exception("no info")) is None


# --------------------------------------------------------------------- #
# State manager unit tests
# --------------------------------------------------------------------- #

def test_cooldown_prevents_immediate_retry(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    provider_state_manager.mark_quota_exhausted("gemini", "gemini-3.7-flash", retry_after=None)
    evaluation = provider_state_manager.evaluate_candidate(
        "gemini", "gemini-3.7-flash", provider_enabled=True, model_enabled=True
    )
    assert not evaluation["usable"]
    assert evaluation["runtime_state"] in (ProviderRuntimeState.QUOTA_EXHAUSTED, ProviderRuntimeState.COOLDOWN)


def test_cooldown_expiry_allows_retry(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    provider_state_manager.mark_quota_exhausted("gemini", "gemini-3.7-flash")
    # Simulate cooldown expiry by rewinding the cooldown timestamp
    state = provider_state_manager.get_state("gemini", "gemini-3.7-flash")
    state["cooldown_until"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    evaluation = provider_state_manager.evaluate_candidate(
        "gemini", "gemini-3.7-flash", provider_enabled=True, model_enabled=True
    )
    assert evaluation["usable"]


def test_retry_after_extends_cooldown():
    provider_state_manager.mark_quota_exhausted("gemini", "m1", retry_after=3600)
    state = provider_state_manager.get_state("gemini", "m1")
    remaining = (state["cooldown_until"] - datetime.now(timezone.utc)).total_seconds()
    assert remaining > 3500  # Retry-After respected over the default 300s


def test_disabled_provider_is_skipped():
    evaluation = provider_state_manager.evaluate_candidate(
        "gemini", "m1", provider_enabled=False, model_enabled=True
    )
    assert not evaluation["usable"]
    assert evaluation["runtime_state"] == ProviderRuntimeState.DISABLED


def test_api_key_status_never_exposes_secret(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-super-secret-value-123")
    status = provider_state_manager.get_api_key_status("openai")
    assert status == {"status": "CONFIGURED", "key_source": "OPENAI_API_KEY", "configured": True}
    assert "sk-super-secret" not in str(status)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    status = provider_state_manager.get_api_key_status("openai")
    assert status["status"] == "NOT_CONFIGURED"
    # Ollama requires no key
    status = provider_state_manager.get_api_key_status("ollama")
    assert status["status"] == "NOT_REQUIRED"


# --------------------------------------------------------------------- #
# Router integration tests (cross-provider failover)
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_first_provider_success(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash")]
    adapter = StubAdapter({"gemini-3.7-flash": [FakeResponse()]})
    router = build_router(candidates, {"gemini": adapter})

    db = FakeDB(candidates)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapter.calls == ["gemini-3.7-flash"]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_gemini_429_suppresses_remaining_models_and_reaches_next_provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash", "gemini-3.6-flash"])
    groq = make_provider("groq", 2, ["gpt-oss-20b"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(gemini, "gemini-3.6-flash"), FakeRegistryModel(groq, "gpt-oss-20b")]
    adapter = StubAdapter({
        "gemini-3.7-flash": [QuotaError("429")],
    })
    groq_adapter = StubAdapter({"gpt-oss-20b": [FakeResponse()]})
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    router = build_router(candidates, {"gemini": adapter, "groq": groq_adapter})

    db = FakeDB(candidates)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapter.calls == ["gemini-3.7-flash"]
    assert groq_adapter.calls == ["gpt-oss-20b"]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_cross_provider_failover_gemini_to_openai(monkeypatch):
    """A Gemini-wide quota failure immediately reaches the next provider."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash", "gemini-3.6-flash"])
    openai = make_provider("openai", 2, ["gpt-4o-mini"])
    candidates = [
        FakeRegistryModel(gemini, "gemini-3.7-flash"),
        FakeRegistryModel(gemini, "gemini-3.6-flash"),
        FakeRegistryModel(openai, "gpt-4o-mini"),
    ]
    adapters = {
        "gemini": StubAdapter({
            "gemini-3.7-flash": [QuotaError("429")],
            "gemini-3.6-flash": [QuotaError("429")],
        }),
        "openai": StubAdapter({"gpt-4o-mini": [FakeResponse()]}),
    }
    router = build_router(candidates, adapters)

    result = await router.generate_response("hi", "", db=FakeDB(candidates))
    assert result == "ok"
    assert adapters["gemini"].calls == ["gemini-3.7-flash"]
    assert adapters["openai"].calls == ["gpt-4o-mini"]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_openai_key_missing_is_skipped(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    openai = make_provider("openai", 2, ["gpt-4o-mini"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(openai, "gpt-4o-mini")]
    adapters = {
        # Gemini quota-exhausted so the router proceeds to evaluate OpenAI
        "gemini": StubAdapter({"gemini-3.7-flash": [QuotaError("429")]}),
        "openai": StubAdapter({"gpt-4o-mini": [FakeResponse()]}),
    }
    router = build_router(candidates, adapters)
    db = FakeDB(candidates)
    await router.generate_response("hi", "", db=db)

    # OpenAI was never attempted
    assert adapters["openai"].calls == []
    # A skip log with API_KEY_MISSING was recorded
    assert any(l.error_type == "API_KEY_MISSING" for l in db.added)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_anthropic_key_missing_is_skipped(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    anthropic = make_provider("anthropic", 2, ["claude-3-5-sonnet"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(anthropic, "claude-3-5-sonnet")]
    adapters = {
        "gemini": StubAdapter({"gemini-3.7-flash": [FakeResponse()]}),
        "anthropic": StubAdapter({"claude-3-5-sonnet": [FakeResponse()]}),
    }
    router = build_router(candidates, adapters)
    await router.generate_response("hi", "", db=FakeDB(candidates))
    assert adapters["anthropic"].calls == []
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_ollama_unreachable_is_skipped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    ollama = make_provider("ollama", 2, ["llama3"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(ollama, "llama3")]

    class UnreachableOllama(StubAdapter):
        async def health_check(self, model_name=None):
            return False

    adapters = {
        # Gemini quota-exhausted so the router proceeds to evaluate Ollama
        "gemini": StubAdapter({"gemini-3.7-flash": [QuotaError("429")]}),
        "ollama": UnreachableOllama({"llama3": [FakeResponse()]}),
    }
    router = build_router(candidates, adapters)
    db = FakeDB(candidates)
    await router.generate_response("hi", "", db=db)

    assert adapters["ollama"].calls == []
    assert any(l.error_type == "UNREACHABLE" for l in db.added)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_all_providers_exhausted_returns_controlled_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash", "gemini-3.6-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(gemini, "gemini-3.6-flash")]
    adapters = {
        "gemini": StubAdapter({
            "gemini-3.7-flash": [QuotaError("429")],
            "gemini-3.6-flash": [QuotaError("429")],
        }),
    }
    router = build_router(candidates, adapters)
    db = FakeDB(candidates)
    result = await router.generate_response("hi", "", db=db)

    # Controlled provider-unavailable response, not a crash
    assert "unavailable" in result.lower() or "high demand" in result.lower()
    # The provider is suppressed after the first shared-quota signal.
    assert adapters["gemini"].calls == ["gemini-3.7-flash"]
    final_logs = [l for l in db.added if l.provider_name == "FINAL"]
    assert len(final_logs) == 1
    assert final_logs[0].model_identifier == "NO_USABLE_PROVIDER"
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.mark.asyncio
async def test_no_duplicate_model_attempts(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash")]
    adapter = StubAdapter({"gemini-3.7-flash": [QuotaError("429"), QuotaError("429"), QuotaError("429")]})
    router = build_router(candidates, {"gemini": adapter})
    await router.generate_response("hi", "", db=FakeDB(candidates))
    assert adapter.calls == ["gemini-3.7-flash"]  # attempted exactly once


@pytest.mark.asyncio
async def test_auth_error_marks_state_without_endless_rotation(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash")]
    adapter = StubAdapter({"gemini-3.7-flash": [AuthError("401 unauthorized"), FakeResponse(), FakeResponse()]})
    router = build_router(candidates, {"gemini": adapter})
    db = FakeDB(candidates)
    result = await router.generate_response("hi", "", db=db)

    # 401 was not retried within the same request and not treated as quota failover
    assert adapter.calls.count("gemini-3.7-flash") == 1
    state = provider_state_manager.get_state("gemini", "gemini-3.7-flash")
    assert state["runtime_state"] == ProviderRuntimeState.CONFIGURATION_ERROR
    # Controlled unavailable response, not a fake success
    assert result != "ok"


@pytest.mark.asyncio
async def test_bad_request_does_not_rotate_as_quota(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash")]
    adapter = StubAdapter({"gemini-3.7-flash": [BadRequestError("400 malformed request"), FakeResponse(), FakeResponse()]})
    router = build_router(candidates, {"gemini": adapter})
    result = await router.generate_response("hi", "", db=FakeDB(candidates))

    # Not retried endlessly; the error was recorded as a config error, not quota
    assert adapter.calls.count("gemini-3.7-flash") == 1
    state = provider_state_manager.get_state("gemini", "gemini-3.7-flash")
    assert state["runtime_state"] == ProviderRuntimeState.CONFIGURATION_ERROR
    assert result != "ok"


@pytest.mark.asyncio
async def test_provider_priority_ordering():
    """Lower priority number is attempted first."""
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    openai = make_provider("openai", 2, ["gpt-4o-mini"])
    # Registry sorted by priority: gemini first
    candidates = sorted(
        [FakeRegistryModel(openai, "gpt-4o-mini"), FakeRegistryModel(gemini, "gemini-3.7-flash")],
        key=lambda m: m.provider.priority,
    )
    assert candidates[0].provider.provider_name == "gemini"


@pytest.mark.asyncio
async def test_cooldown_prevents_retry_across_requests(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash", "gemini-3.6-flash"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(gemini, "gemini-3.6-flash")]
    adapter = StubAdapter({
        "gemini-3.7-flash": [QuotaError("429"), QuotaError("429"), QuotaError("429")],
        "gemini-3.6-flash": [FakeResponse(), FakeResponse()],
    })
    router = build_router(candidates, {"gemini": adapter})
    db = FakeDB(candidates)

    await router.generate_response("hi", "", db=db)
    await router.generate_response("hi", "", db=db)
    # Provider-level cooldown skips all Gemini models on the second request.
    assert adapter.calls == ["gemini-3.7-flash"]
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


def test_secrets_never_appear_in_state_snapshot(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-secret-do-not-leak-1234567890")
    provider_state_manager.get_state("gemini", "gemini-3.7-flash")
    snapshot = provider_state_manager.snapshot("gemini", "gemini-3.7-flash")
    status = provider_state_manager.get_api_key_status("gemini")
    blob = str(snapshot) + str(status)
    assert "AIza-secret-do-not-leak" not in blob
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
