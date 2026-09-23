import pytest
from backend.app.ai.adapters.gemini_adapter import GeminiProvider, GeminiQuotaError
from backend.app.core.config import settings
class FakeResponse:
    text = "ok"
    usage_metadata = None
class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = []

    async def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self.outcomes[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
class FakeClient:
    def __init__(self, models):
        self.aio = type("Aio", (), {"models": models})()

class QuotaError(Exception):
    status_code = 429
class AuthError(Exception):
    status_code = 401
@pytest.fixture
def configured_provider(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_MODELS", "gemini-3.7-flash,gemini-3.6-flash")
    monkeypatch.setattr(settings, "GEMINI_MODEL_COOLDOWN_SECONDS", 300)
    return GeminiProvider(api_key="test-only-key")

@pytest.mark.asyncio
async def test_first_model_success(configured_provider):
    models = FakeModels({"gemini-3.7-flash": [FakeResponse()]})
    configured_provider._client = FakeClient(models)
    response = await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    assert response.content == "ok"
    assert models.calls == ["gemini-3.7-flash"]

@pytest.mark.asyncio
async def test_quota_is_reported_to_router_without_hidden_rotation(configured_provider):
    models = FakeModels({
        "gemini-3.7-flash": [QuotaError()],
        "gemini-3.6-flash": [FakeResponse()],
    })
    configured_provider._client = FakeClient(models)
    with pytest.raises(GeminiQuotaError):
        await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    assert models.calls == ["gemini-3.7-flash"]

@pytest.mark.asyncio
async def test_all_quota_models_are_bounded(configured_provider):
    models = FakeModels({
        "gemini-3.7-flash": [QuotaError()],
        "gemini-3.6-flash": [QuotaError()],
    })
    configured_provider._client = FakeClient(models)
    with pytest.raises(GeminiQuotaError):
        await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    assert models.calls == ["gemini-3.7-flash"]

@pytest.mark.asyncio
async def test_auth_error_does_not_rotate(configured_provider):
    models = FakeModels({
        "gemini-3.7-flash": [AuthError()],
        "gemini-3.6-flash": [FakeResponse()],
    })
    configured_provider._client = FakeClient(models)
    with pytest.raises(AuthError):
        await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    assert models.calls == ["gemini-3.7-flash"]

@pytest.mark.asyncio
async def test_quota_model_is_skipped_during_cooldown(configured_provider):
    models = FakeModels({
        "gemini-3.7-flash": [QuotaError()],
        "gemini-3.6-flash": [FakeResponse(), FakeResponse()],
    })
    configured_provider._client = FakeClient(models)
    with pytest.raises(GeminiQuotaError):
        await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    with pytest.raises(GeminiQuotaError):
        await configured_provider.generate_response("gemini-3.7-flash", "hi", "")
    assert models.calls == ["gemini-3.7-flash"]
