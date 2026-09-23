"""
P1 — Production SECRET_KEY hardening.

Verifies real production-mode Settings construction (startup behavior):
 1. production + missing SECRET_KEY      -> startup rejected
 2. production + empty SECRET_KEY        -> startup rejected
 3. production + known default/weak key  -> startup rejected
 4. production + valid strong secret     -> startup succeeds
 5. development + existing configuration -> startup succeeds
 6. error messages never leak the secret value
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import ValidationError

from backend.app.core.config import Settings

_VALID = "x" * 48 + "-strong-production-secret-9f3a1c"


def _settings(**overrides):
    # Bypass .env so the environment overrides under test are authoritative.
    return Settings(_env_file=None, **overrides)


def test_production_missing_secret_key_is_rejected():
    with pytest.raises(ValidationError) as exc:
        _settings(ENVIRONMENT="production", SECRET_KEY="")
    assert "SECRET_KEY" in str(exc.value)


def test_production_empty_or_whitespace_secret_key_is_rejected():
    for bad in ("", "   ", "\t\n"):
        with pytest.raises(ValidationError):
            _settings(ENVIRONMENT="production", SECRET_KEY=bad)


def test_production_known_default_and_weak_keys_are_rejected():
    weak_keys = [
        # the app's own historical default
        "ait-ai-super-secret-key-change-in-production-2026",
        # common weak defaults, even when long enough to pass the length check
        "secret",
        "changeme",
        "your-secret-key-here",
        "supersecret",
        "dev-secret-key",
    ]
    for key in weak_keys:
        with pytest.raises(ValidationError):
            _settings(ENVIRONMENT="production", SECRET_KEY=key)


def test_production_short_key_is_rejected():
    with pytest.raises(ValidationError):
        _settings(ENVIRONMENT="production", SECRET_KEY="short-key-123")


def test_production_valid_secret_starts_successfully():
    s = _settings(ENVIRONMENT="production", SECRET_KEY=_VALID)
    assert s.SECRET_KEY == _VALID


def test_production_forces_debug_off():
    s = _settings(ENVIRONMENT="production", SECRET_KEY=_VALID, DEBUG=True)
    assert s.DEBUG is False


def test_production_error_message_does_not_leak_secret():
    """The sanitized startup loader must surface only the validation message,
    never the configured secret value (pydantic's raw ValidationError embeds
    input_value in its context)."""
    import backend.app.core.config as cfg
    secret_with_marker = _VALID[:10] + "-leak-marker"
    leaky_error = _validation_error_with_input(secret_with_marker)

    original = cfg.Settings
    def _failing_settings(*args, **kwargs):
        raise leaky_error
    cfg.Settings = _failing_settings
    try:
        with pytest.raises(RuntimeError) as exc:
            cfg.load_settings_safe()
        assert "leak-marker" not in str(exc.value)
        assert "SECRET_KEY" in str(exc.value)
    finally:
        cfg.Settings = original


def _validation_error_with_input(secret):
    try:
        Settings(ENVIRONMENT="production", SECRET_KEY=secret)
    except ValidationError as e:
        return e
    raise AssertionError("expected ValidationError")


def test_development_existing_configuration_still_starts():
    # Intentional development fallback (no SECRET_KEY override at all)
    s = _settings(ENVIRONMENT="development")
    assert s.SECRET_KEY  # non-empty
    # Explicit weak key is tolerated in development
    s2 = _settings(ENVIRONMENT="development", SECRET_KEY="short")
    assert s2.SECRET_KEY == "short"


def test_prod_alias_also_enforced():
    with pytest.raises(ValidationError):
        _settings(ENVIRONMENT="prod", SECRET_KEY="changeme")


def test_current_local_environment_still_loads():
    """The real module-level settings object (as used by the running app)
    must keep loading with the local .env / environment as-is."""
    from backend.app.core.config import settings
    assert settings.SECRET_KEY
    assert settings.ALGORITHM == "HS256"
