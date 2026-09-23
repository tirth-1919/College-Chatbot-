"""
Tests for the multi-provider automatic transition chain:
    Gemini -> Groq -> OpenRouter -> OpenAI -> Anthropic -> Ollama

Covers: Gemini->Groq fallback, Groq model-level rotation, Groq->OpenRouter,
OpenRouter free-model chain, missing OpenAI/Anthropic keys, unavailable
Ollama, 429/5xx/timeout/invalid-model, cooldown, duplicate-candidate
prevention, free-only mode, and API-key redaction.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.ai.circuit_breaker import circuit_breaker
from backend.app.ai.provider_state import (
    provider_state_manager,
    ProviderRuntimeState,
)
from backend.app.core.config import settings
from backend.app.models.admin_system import AiProviderConfig, AiModelRegistry
from backend.app.ai.router import AIRouter


# --------------------------------------------------------------------- #
# Fixtures & helpers (same pattern as test_provider_failover.py)
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


class ServerError(Exception):
    status_code = 503


class TimeoutError_(Exception):
    status_code = 504


class InvalidModelError(Exception):
    status_code = 404


class StubAdapter:
    def __init__(self, outcomes):
        self.outcomes = outcomes
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


class UnreachableAdapter(StubAdapter):
    async def health_check(self, model_name=None):
        return False


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setattr(settings, "PROVIDER_FAILOVER_ENABLED", True)
    monkeypatch.setattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(settings, "PROVIDER_MAX_ATTEMPTS", 0)
    monkeypatch.setattr(settings, "PROVIDER_QUOTA_CHECK_ENABLED", True)
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", False)
    # Clear real keys so tests control configuration explicitly
    for var in ("GROQ_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
        monkeypatch.setattr(settings, var, "", raising=False)
    circuit_breaker._states.clear()
    provider_state_manager._states.clear()
    yield
    circuit_breaker._states.clear()
    provider_state_manager._states.clear()


def make_provider(provider_name, priority, models, enabled=True):
    p = AiProviderConfig(
        id=str(uuid.uuid4()),
        provider_name=provider_name,
        display_name=provider_name.title(),
        is_enabled=enabled,
        priority=priority,
        api_key_env=None if provider_name == "ollama" else f"{provider_name.upper()}_API_KEY",
    )
    p.models = [
        AiModelRegistry(
            id=str(uuid.uuid4()),
            provider_id=p.id,
            model_identifier=m,
            display_name=m,
            is_enabled=True,
            priority=i + 1,
            free_tier_status="FREE_TIER_ELIGIBLE" if m.endswith(":free") or provider_name in ("gemini", "ollama") else "UNKNOWN",
        )
        for i, m in enumerate(models)
    ]
    return p


class FakeQuery:
    def __init__(self, candidates):
        self.candidates = candidates

    def filter(self, *a, **k): return self
    def join(self, *a, **k): return self
    def order_by(self, *a, **k): return self
    def all(self): return self.candidates
    def first(self): return None


class FakeDB:
    def __init__(self, candidates):
        self.candidates = candidates
        self.added = []

    def query(self, model): return FakeQuery(self.candidates)
    def add(self, obj): self.added.append(obj)
    def commit(self): pass


class FakeRegistryModel:
    def __init__(self, provider, model_identifier, free_tier_status="UNKNOWN"):
        self.provider = provider
        self.model_identifier = model_identifier
        self.id = str(uuid.uuid4())
        self.is_enabled = True
        self.free_tier_status = free_tier_status
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
    router = AIRouter.__new__(AIRouter)

    def fake_get_adapter(provider_name, base_url=None):
        return adapters[provider_name]

    router._get_adapter = fake_get_adapter
    return router


def chain_log(db):
    return [(l.provider_name, l.model_identifier, l.success) for l in db.added]


# --------------------------------------------------------------------- #
# 1. Gemini -> Groq fallback
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_gemini_to_groq_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    groq = make_provider("groq", 2, ["openai/gpt-oss-120b"])
    candidates = [FakeRegistryModel(gemini, "gemini-3.7-flash"), FakeRegistryModel(groq, "openai/gpt-oss-120b")]
    adapters = {
        "gemini": StubAdapter({"gemini-3.7-flash": [QuotaError("429")]}),
        "groq": StubAdapter({"openai/gpt-oss-120b": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapters["groq"].calls == ["openai/gpt-oss-120b"]
    assert ("gemini", "gemini-3.7-flash", False) in chain_log(db)


# --------------------------------------------------------------------- #
# 2. Groq -> next Groq model (model-level rotation inside Groq)
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_groq_model_level_rotation(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b", "openai/gpt-oss-20b"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b"), FakeRegistryModel(groq, "openai/gpt-oss-20b")]
    adapter = StubAdapter({
        "openai/gpt-oss-120b": [QuotaError("429")],
        "openai/gpt-oss-20b": [FakeResponse()],
    })
    db = FakeDB(candidates)
    router = build_router(candidates, {"groq": adapter})
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapter.calls == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


# --------------------------------------------------------------------- #
# 3. Groq -> OpenRouter fallback
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_groq_to_openrouter_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b"])
    openrouter = make_provider("openrouter", 2, ["google/gemma-4-31b-it:free"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b"), FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free")]
    adapters = {
        "groq": StubAdapter({"openai/gpt-oss-120b": [ServerError("503")]}),
        "openrouter": StubAdapter({"google/gemma-4-31b-it:free": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapters["openrouter"].calls == ["google/gemma-4-31b-it:free"]


# --------------------------------------------------------------------- #
# 4. OpenRouter -> next free model
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_openrouter_free_model_chain(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    openrouter = make_provider("openrouter", 1, ["google/gemma-4-31b-it:free", "inclusionai/ling-3.0-flash-vl:free"])
    candidates = [
        FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free"),
        FakeRegistryModel(openrouter, "inclusionai/ling-3.0-flash-vl:free"),
    ]
    adapter = StubAdapter({
        "google/gemma-4-31b-it:free": [InvalidModelError("404 model not found")],
        "inclusionai/ling-3.0-flash-vl:free": [FakeResponse()],
    })
    db = FakeDB(candidates)
    router = build_router(candidates, {"openrouter": adapter})
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapter.calls == ["google/gemma-4-31b-it:free", "inclusionai/ling-3.0-flash-vl:free"]


# --------------------------------------------------------------------- #
# 5. OpenRouter -> Ollama (unreachable)
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_openrouter_to_unreachable_ollama(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    openrouter = make_provider("openrouter", 1, ["google/gemma-4-31b-it:free"])
    ollama = make_provider("ollama", 2, ["llama3"])
    candidates = [FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free"), FakeRegistryModel(ollama, "llama3")]
    adapters = {
        "openrouter": StubAdapter({"google/gemma-4-31b-it:free": [QuotaError("429")]}),
        "ollama": UnreachableAdapter({"llama3": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    await router.generate_response("hi", "", db=db)
    # Ollama unreachable -> graceful evidence-based / error fallback, no crash
    assert adapters["ollama"].calls == []
    state = provider_state_manager.get_state("ollama", "llama3")
    assert state["runtime_state"] == ProviderRuntimeState.UNREACHABLE


# --------------------------------------------------------------------- #
# 6. Missing OpenAI / Anthropic keys -> skipped, no startup failure
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_missing_openai_and_anthropic_keys_skipped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    gemini = make_provider("gemini", 1, ["gemini-3.7-flash"])
    openai = make_provider("openai", 2, ["gpt-4o-mini"])
    anthropic = make_provider("anthropic", 3, ["claude-3-5-sonnet"])
    candidates = [
        FakeRegistryModel(gemini, "gemini-3.7-flash"),
        FakeRegistryModel(openai, "gpt-4o-mini"),
        FakeRegistryModel(anthropic, "claude-3-5-sonnet"),
    ]
    adapters = {
        "gemini": StubAdapter({"gemini-3.7-flash": [QuotaError("429")]}),
        "openai": StubAdapter({"gpt-4o-mini": [FakeResponse()]}),
        "anthropic": StubAdapter({"claude-3-5-sonnet": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    await router.generate_response("hi", "", db=db)
    # Neither paid provider was attempted (no keys); graceful fallback text.
    assert adapters["openai"].calls == []
    assert adapters["anthropic"].calls == []
    skipped = [(l.provider_name, l.error_type) for l in db.added if l.provider_name in ("openai", "anthropic")]
    assert skipped == [("openai", "API_KEY_MISSING"), ("anthropic", "API_KEY_MISSING")]


# --------------------------------------------------------------------- #
# 7. Timeout failover
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_timeout_failover(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b"])
    openrouter = make_provider("openrouter", 2, ["google/gemma-4-31b-it:free"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b"), FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free")]
    adapters = {
        "groq": StubAdapter({"openai/gpt-oss-120b": [TimeoutError_("timed out")]}),
        "openrouter": StubAdapter({"google/gemma-4-31b-it:free": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapters["openrouter"].calls == ["google/gemma-4-31b-it:free"]


# --------------------------------------------------------------------- #
# 8. Cooldown skip
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_cooldown_skips_cooled_candidate(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    provider_state_manager.mark_quota_exhausted("groq", "openai/gpt-oss-120b")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b", "openai/gpt-oss-20b"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b"), FakeRegistryModel(groq, "openai/gpt-oss-20b")]
    adapter = StubAdapter({"openai/gpt-oss-20b": [FakeResponse()]})
    db = FakeDB(candidates)
    router = build_router(candidates, {"groq": adapter})
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    # The cooled-down model was never attempted
    assert adapter.calls == ["openai/gpt-oss-20b"]


# --------------------------------------------------------------------- #
# 9. Duplicate candidate prevention (bounded attempts)
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_no_duplicate_attempts_within_request(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b")]
    adapter = StubAdapter({"openai/gpt-oss-120b": [QuotaError("429"), QuotaError("429")]})
    db = FakeDB(candidates)
    router = build_router(candidates, {"groq": adapter})
    await router.generate_response("hi", "", db=db)
    assert adapter.calls == ["openai/gpt-oss-120b"]  # attempted exactly once


# --------------------------------------------------------------------- #
# 10. FREE-ONLY mode
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_free_only_mode_excludes_paid(monkeypatch):
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", True)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    openrouter = make_provider("openrouter", 1, ["anthropic/claude-sonnet-4"])
    candidates = [FakeRegistryModel(openrouter, "anthropic/claude-sonnet-4", free_tier_status="PAID")]
    adapter = StubAdapter({"anthropic/claude-sonnet-4": [FakeResponse()]})
    db = FakeDB(candidates)
    router = build_router(candidates, {"openrouter": adapter})
    await router.generate_response("hi", "", db=db)
    # Paid model filtered out: adapter never called; graceful fallback used.
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_free_only_mode_allows_verified_free(monkeypatch):
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", True)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    openrouter = make_provider("openrouter", 1, ["google/gemma-4-31b-it:free"])
    candidates = [FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free", free_tier_status="FREE_TIER_ELIGIBLE")]
    adapter = StubAdapter({"google/gemma-4-31b-it:free": [FakeResponse()]})
    db = FakeDB(candidates)
    router = build_router(candidates, {"openrouter": adapter})
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"


# --------------------------------------------------------------------- #
# 11. API key redaction
# --------------------------------------------------------------------- #

def test_api_key_status_never_exposes_value(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_SECRETVALUE_123456")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-SECRETVALUE_987654")
    for provider, env in (("groq", "GROQ_API_KEY"), ("openrouter", "OPENROUTER_API_KEY")):
        status = provider_state_manager.get_api_key_status(provider, env)
        assert status["status"] == "CONFIGURED"
        assert status["configured"] is True
        assert "SECRETVALUE" not in str(status)


def test_openai_anthropic_missing_key_status(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "", raising=False)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "", raising=False)
    assert provider_state_manager.get_api_key_status("openai", "OPENAI_API_KEY")["status"] == "NOT_CONFIGURED"
    assert provider_state_manager.get_api_key_status("anthropic", "ANTHROPIC_API_KEY")["status"] == "NOT_CONFIGURED"


# --------------------------------------------------------------------- #
# 12. 5xx failover across providers
# --------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_5xx_failover_across_providers(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only-key")
    groq = make_provider("groq", 1, ["openai/gpt-oss-120b"])
    openrouter = make_provider("openrouter", 2, ["google/gemma-4-31b-it:free"])
    candidates = [FakeRegistryModel(groq, "openai/gpt-oss-120b"), FakeRegistryModel(openrouter, "google/gemma-4-31b-it:free")]
    adapters = {
        "groq": StubAdapter({"openai/gpt-oss-120b": [ServerError("503 service unavailable")]}),
        "openrouter": StubAdapter({"google/gemma-4-31b-it:free": [FakeResponse()]}),
    }
    db = FakeDB(candidates)
    router = build_router(candidates, adapters)
    result = await router.generate_response("hi", "", db=db)
    assert result == "ok"
    assert adapters["openrouter"].calls == ["google/gemma-4-31b-it:free"]


# --------------------------------------------------------------------- #
# 13. OpenRouter free-model metadata classification (authoritative)
# --------------------------------------------------------------------- #

def test_openrouter_free_classification_uses_pricing_metadata():
    from backend.app.ai.adapters.openrouter_adapter import is_openrouter_free_model_metadata
    assert is_openrouter_free_model_metadata({"pricing": {"prompt": "0", "completion": "0"}}) is True
    # ':free' in the NAME but a non-zero price -> NOT free (metadata wins)
    assert is_openrouter_free_model_metadata({"id": "x:free", "pricing": {"prompt": "0.000001", "completion": "0"}}) is False
    assert is_openrouter_free_model_metadata({"pricing": {}}) is False
