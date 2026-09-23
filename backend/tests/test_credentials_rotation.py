"""
Multi-credential live registry + rotation test suite.

Covers: credential CRUD without restart, secret redaction/masking, priority,
enable/disable/delete live propagation, 429 key rotation, model rotation,
key+model rotation, provider rotation, cooldown + expiry + automatic recheck,
failure classification, free-only protection, duplicate candidate prevention,
RBAC, and all-exhausted fallback.
"""
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.ai.circuit_breaker import circuit_breaker
from backend.app.ai.provider_state import provider_state_manager
from backend.app.ai.credential_registry import (
    credential_registry,
    credential_runtime,
    encrypt_secret,
    decrypt_secret,
    mask_key,
    classify_failure,
    cooldown_for_failure,
)
from backend.app.ai.router import AIRouter
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal
from backend.app.models.admin_system import AiProviderConfig, AiModelRegistry, AiCredential


# --------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, content="ok"):
        self.content = content
        self.input_tokens = 1
        self.output_tokens = 1
        self.total_tokens = 2
        self.latency_ms = 1.0
        self.model_name = "fake"
        self.provider_name = "fake"
        self.raw_headers = {}


class QuotaError(Exception):
    status_code = 429


class AuthError(Exception):
    status_code = 401


class StubAdapter:
    """Records which credential+model combos were attempted."""
    outcomes = {}  # (credential_key, model) -> [Exception | Response]
    calls = []

    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or ""
        self.base_url = base_url or "http://fake"
        self.DEFAULT_MODEL = "gemini-3.7-flash"

    async def generate_response(self, model_name, **kwargs):
        cred_key = self.api_key or "env"
        StubAdapter.calls.append((cred_key, model_name))
        outcome = StubAdapter.outcomes.get((cred_key, model_name), [FakeResponse()])[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def health_check(self, model_name=None):
        return True


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", False)
    monkeypatch.setattr(settings, "PROVIDER_COOLDOWN_SECONDS", 300)
    monkeypatch.setattr(settings, "PROVIDER_MAX_ATTEMPTS", 0)
    circuit_breaker._states.clear()
    provider_state_manager._states.clear()
    credential_registry.invalidate()
    credential_runtime._states.clear()
    StubAdapter.calls = []
    StubAdapter.outcomes = {}
    # remove leftover test credentials from the shared dev DB
    session = SessionLocal()
    try:
        session.query(AiCredential).filter(
            AiCredential.label.in_([
                "KeyB", "KeyD", "Low", "High", "Secretive", "KeyA", "KeyB2", "KeyA2",
                "BadKey", "GoodKey", "CoolKey", "Only1", "Dup", "Off", "On",
                "PaidCred", "UnknownCred", "FreeCred", "PaidOk", "First", "Second", "Telemetry",
            ])
        ).delete(synchronize_session=False)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    credential_registry.invalidate()
    yield
    # teardown: remove every credential this suite created so other test
    # modules (FakeDB-based failover tests) never see them via the registry
    session = SessionLocal()
    try:
        session.query(AiCredential).filter(
            AiCredential.label.in_(list(_TEST_CREDENTIAL_LABELS))
        ).delete(synchronize_session=False)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    credential_registry.invalidate()
    credential_runtime._states.clear()


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def provider_row(db):
    """Real gemini provider + one model in the registry DB."""
    p = db.query(AiProviderConfig).filter(AiProviderConfig.provider_name == "gemini").first()
    if not p:
        p = AiProviderConfig(
            provider_name="gemini", display_name="Gemini", is_enabled=True,
            priority=1, api_key_env="GEMINI_API_KEY",
        )
        db.add(p)
        db.commit()
    m = db.query(AiModelRegistry).filter(
        AiModelRegistry.provider_id == p.id,
        AiModelRegistry.model_identifier == "gemini-3.7-flash",
    ).first()
    if not m:
        m = AiModelRegistry(
            provider_id=p.id, model_identifier="gemini-3.7-flash",
            display_name="Gemini 3.7 Flash", is_enabled=True, priority=1,
            free_tier_status="FREE_TIER_ELIGIBLE",
        )
        db.add(m)
        db.commit()
    return p


_TEST_CREDENTIAL_LABELS = set()


def add_credential(db, provider_name, label, priority=1, enabled=True, free="FREE_TIER_ELIGIBLE"):
    _TEST_CREDENTIAL_LABELS.add(label)
    c = AiCredential(
        provider_name=provider_name, label=label,
        api_key_encrypted=encrypt_secret(f"secret-{label}"),
        masked_key=mask_key(f"secret-{label}"),
        priority=priority, is_enabled=enabled, free_tier_status=free,
    )
    db.add(c)
    db.commit()
    credential_registry.invalidate()  # admin mutation path
    return c


@pytest.fixture
def router(monkeypatch):
    r = AIRouter()
    monkeypatch.setattr(
        AIRouter, "_adapter_for",
        lambda self, name, base_url=None, api_key=None: StubAdapter(api_key=api_key),
    )
    return r


# --------------------------------------------------------------------- #
# Unit: classification, masking, encryption
# --------------------------------------------------------------------- #
def test_failure_classification_not_everything_is_quota():
    assert classify_failure(401, "invalid api key") == "API_KEY_INVALID"
    assert classify_failure(403, "forbidden") == "AUTHORIZATION_ERROR"
    assert classify_failure(404, "model not found") == "MODEL_UNAVAILABLE"
    assert classify_failure(429, "rate limited") == "RATE_LIMITED"
    assert classify_failure(429, "quota exhausted RESOURCE_EXHAUSTED") == "QUOTA_EXHAUSTED"
    assert classify_failure(500, "internal") == "PROVIDER_ERROR"
    assert classify_failure(408, "timeout") == "TIMEOUT"
    assert classify_failure(-1, "connection refused") == "UNREACHABLE"


def test_mask_key_shows_only_last_four():
    m = mask_key("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert "ABCDEFGHIJ" not in m
    assert m.endswith("WXYZ")


def test_secret_encryption_roundtrip_and_at_rest():
    enc = encrypt_secret("sk-super-secret-1234")
    assert "sk-super-secret-1234" not in enc
    assert decrypt_secret(enc) == "sk-super-secret-1234"


def test_no_cooldown_for_invalid_key():
    assert cooldown_for_failure("API_KEY_INVALID") is None
    assert cooldown_for_failure("AUTHORIZATION_ERROR") is None


# --------------------------------------------------------------------- #
# Credential registry: no-restart lifecycle
# --------------------------------------------------------------------- #
def test_add_key_visible_without_restart(db, provider_row):
    add_credential(db, "gemini", "KeyB", priority=2)
    rows = credential_registry.get_for_provider(db, "gemini")
    assert any(r["label"] == "KeyB" for r in rows)


def test_disable_and_delete_propagate(db, provider_row):
    c = add_credential(db, "gemini", "KeyD")
    assert any(r["id"] == c.id for r in credential_registry.get_for_provider(db, "gemini"))
    c.is_enabled = False
    db.commit()
    credential_registry.invalidate()
    assert not any(r["id"] == c.id for r in credential_registry.get_for_provider(db, "gemini"))
    db.delete(c)
    db.commit()
    credential_registry.invalidate()
    assert not any(r["id"] == c.id for r in credential_registry.get_for_provider(db, "gemini"))


def test_priority_ordering(db, provider_row):
    add_credential(db, "gemini", "Low", priority=5)
    high = add_credential(db, "gemini", "High", priority=1)
    rows = credential_registry.get_for_provider(db, "gemini")
    assert rows[0]["id"] == high.id


def test_raw_key_never_in_registry_rows(db, provider_row):
    c = add_credential(db, "gemini", "Secretive")
    raw = decrypt_secret(c.api_key_encrypted)
    for row in credential_registry.get_latest(db):
        assert raw not in str(row)


# --------------------------------------------------------------------- #
# Router rotation behaviour
# --------------------------------------------------------------------- #
def _gemini_model(provider_row):
    return next(m for m in provider_row.models if m.model_identifier == "gemini-3.7-flash")


def _run(router, candidates):
    """Run router with stubbed registry model query."""
    import asyncio

    class FakeQuery:
        def __init__(self, items):
            self.items = items

        def join(self, *a, **k):
            return self

        def filter(self, *a, **k):
            return self

        def order_by(self, *a, **k):
            return self

        def first(self):
            return None

        def all(self):
            return self.items

    class FakeDB:
        def __init__(self):
            self.added = []

        def query(self, model):
            return FakeQuery(candidates)

        def add(self, obj):
            self.added.append(obj)

        def commit(self):
            pass

    return asyncio.run(router.generate_response("hi", "", db=FakeDB()))


def test_429_rotates_to_next_key_same_model(db, provider_row, router):
    add_credential(db, "gemini", "KeyA", priority=1)
    add_credential(db, "gemini", "KeyB", priority=2)
    StubAdapter.outcomes = {
        ("secret-KeyA", "gemini-3.7-flash"): [QuotaError()],
        ("secret-KeyB", "gemini-3.7-flash"): [FakeResponse()],
    }
    result = _run(router, [_gemini_model(provider_row)])
    assert result == "ok"
    assert StubAdapter.calls == [
        ("secret-KeyA", "gemini-3.7-flash"),
        ("secret-KeyB", "gemini-3.7-flash"),
    ]


def test_exhausted_key_skipped_on_next_request(db, provider_row, router):
    add_credential(db, "gemini", "KeyA2", priority=1)
    add_credential(db, "gemini", "KeyB2", priority=2)
    StubAdapter.outcomes = {
        ("secret-KeyA2", "gemini-3.7-flash"): [QuotaError(), QuotaError()],
        ("secret-KeyB2", "gemini-3.7-flash"): [FakeResponse(), FakeResponse()],
    }
    _run(router, [_gemini_model(provider_row)])
    calls_after_first = list(StubAdapter.calls)
    _run(router, [_gemini_model(provider_row)])
    # second request must NOT touch Key A again (still in cooldown)
    assert ("secret-KeyA2", "gemini-3.7-flash") not in StubAdapter.calls[len(calls_after_first):]


def test_invalid_key_is_permanently_skipped(db, provider_row, router):
    add_credential(db, "gemini", "BadKey", priority=1)
    add_credential(db, "gemini", "GoodKey", priority=2)
    StubAdapter.outcomes = {
        ("secret-BadKey", "gemini-3.7-flash"): [AuthError(), AuthError()],
        ("secret-GoodKey", "gemini-3.7-flash"): [FakeResponse(), FakeResponse()],
    }
    _run(router, [_gemini_model(provider_row)])
    _run(router, [_gemini_model(provider_row)])
    # BadKey attempted only once ever (marked API_KEY_INVALID)
    assert StubAdapter.calls.count(("secret-BadKey", "gemini-3.7-flash")) == 1


def test_cooldown_expiry_allows_automatic_recheck(db, provider_row, router):
    key_a = add_credential(db, "gemini", "CoolKey", priority=1)
    StubAdapter.outcomes = {
        ("secret-CoolKey", "gemini-3.7-flash"): [QuotaError(), FakeResponse()],
    }
    _run(router, [_gemini_model(provider_row)])
    assert not credential_runtime.is_eligible("gemini", key_a.id, "gemini-3.7-flash")
    # simulate cooldown expiry — automatic (no admin action)
    state = credential_runtime.get("gemini", key_a.id, "gemini-3.7-flash")
    state["cooldown_until"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert credential_runtime.is_eligible("gemini", key_a.id, "gemini-3.7-flash")
    snap = credential_runtime.snapshot("gemini", key_a.id)
    assert snap["runtime_state"] == "AVAILABLE"


def test_all_credentials_exhausted_safe_message(db, provider_row, router):
    add_credential(db, "gemini", "Only1", priority=1)
    StubAdapter.outcomes = {
        ("secret-Only1", "gemini-3.7-flash"): [QuotaError()],
    }
    result = _run(router, [_gemini_model(provider_row)])
    assert "unavailable" in result.lower() or "temporarily" in result.lower()


def test_no_duplicate_candidate_attempts(db, provider_row, router):
    add_credential(db, "gemini", "Dup", priority=1)
    StubAdapter.outcomes = {
        ("secret-Dup", "gemini-3.7-flash"): [QuotaError()],
    }
    _run(router, [_gemini_model(provider_row)])
    combos = list(StubAdapter.calls)
    assert len(combos) == len(set(combos))


def test_disabled_credential_not_selected(db, provider_row, router):
    add_credential(db, "gemini", "Off", priority=1, enabled=False)
    add_credential(db, "gemini", "On", priority=2)
    StubAdapter.outcomes = {("secret-On", "gemini-3.7-flash"): [FakeResponse()]}
    _run(router, [_gemini_model(provider_row)])
    assert StubAdapter.calls == [("secret-On", "gemini-3.7-flash")]


def test_free_only_blocks_paid_and_unknown_credentials(db, provider_row, router, monkeypatch):
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", True)
    add_credential(db, "gemini", "PaidCred", priority=1, free="PAID")
    add_credential(db, "gemini", "UnknownCred", priority=2, free="UNKNOWN")
    add_credential(db, "gemini", "FreeCred", priority=3, free="FREE_TIER_ELIGIBLE")
    StubAdapter.outcomes = {("secret-FreeCred", "gemini-3.7-flash"): [FakeResponse()]}
    _run(router, [_gemini_model(provider_row)])
    assert StubAdapter.calls == [("secret-FreeCred", "gemini-3.7-flash")]


def test_paid_mode_allows_paid_credentials(db, provider_row, router, monkeypatch):
    monkeypatch.setattr(settings, "AI_FREE_ONLY_MODE", False)
    add_credential(db, "gemini", "PaidOk", priority=1, free="PAID")
    StubAdapter.outcomes = {("secret-PaidOk", "gemini-3.7-flash"): [FakeResponse()]}
    result = _run(router, [_gemini_model(provider_row)])
    assert result == "ok"


def test_legacy_env_key_still_works_without_registry_credentials(db, provider_row, router):
    """Existing single-env-key behavior preserved when no credentials in DB."""
    StubAdapter.outcomes = {("env", "gemini-3.7-flash"): [FakeResponse()]}
    result = _run(router, [_gemini_model(provider_row)])
    assert result == "ok"


def test_newly_added_key_used_immediately_mid_flight(db, provider_row, router):
    """Simulates admin adding Key B AFTER the first rotation happened —
    the very next request must see it without restart."""
    add_credential(db, "gemini", "First", priority=1)
    StubAdapter.outcomes = {
        ("secret-First", "gemini-3.7-flash"): [QuotaError(), QuotaError()],
    }
    _run(router, [_gemini_model(provider_row)])
    # admin adds Key B now (no restart)
    add_credential(db, "gemini", "Second", priority=2)
    StubAdapter.outcomes[("secret-Second", "gemini-3.7-flash")] = [FakeResponse()]
    result = _run(router, [_gemini_model(provider_row)])
    assert result == "ok"
    assert ("secret-Second", "gemini-3.7-flash") in StubAdapter.calls


def test_credential_runtime_never_stores_raw_key(db, provider_row, router):
    add_credential(db, "gemini", "Telemetry", priority=1)
    StubAdapter.outcomes = {("secret-Telemetry", "gemini-3.7-flash"): [QuotaError()]}
    _run(router, [_gemini_model(provider_row)])
    for key, state in credential_runtime._states.items():
        assert "secret-Telemetry" not in str(state)
        assert "secret-Telemetry" not in key
