"""Tests for Application Settings and DEBUG Configuration.

Verifies:
1. Default DEBUG is False.
2. DEBUG reads from environment variable correctly.
3. parse_debug validator supports truthy and falsy representations.
4. ENVIRONMENT and DEBUG can be configured independently.
"""

import os
from unittest import mock
import pytest
from app.core.config import Settings


def test_default_debug_is_false():
    """Verify that DEBUG defaults to False when not specified in env."""
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("DEBUG", None)
        s = Settings()
        assert s.DEBUG is False


@pytest.mark.parametrize(
    "truthy_value",
    ["true", "True", "TRUE", "1", "yes", "YES", "on", "ON", "dev", "development"],
)
def test_debug_env_truthy_values(truthy_value: str):
    """Verify that truthy string representations in env evaluate to True."""
    with mock.patch.dict(os.environ, {"DEBUG": truthy_value}):
        s = Settings()
        assert s.DEBUG is True


@pytest.mark.parametrize(
    "falsy_value",
    ["false", "False", "FALSE", "0", "no", "NO", "off", "OFF", "prod", "production", "release"],
)
def test_debug_env_falsy_values(falsy_value: str):
    """Verify that falsy string representations in env evaluate to False."""
    with mock.patch.dict(os.environ, {"DEBUG": falsy_value}):
        s = Settings()
        assert s.DEBUG is False


def test_debug_direct_boolean_assignment():
    """Verify direct boolean initialization works as expected."""
    assert Settings(DEBUG=True).DEBUG is True
    assert Settings(DEBUG=False).DEBUG is False


def test_environment_independent_from_debug():
    """Verify ENVIRONMENT and DEBUG are configured completely independently."""
    # Production with debug explicitly enabled (e.g. temporary diagnostic)
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "production", "DEBUG": "true"}):
        s1 = Settings(ADMIN_FRONTEND_URL="https://admin.example.test")
        assert s1.ENVIRONMENT == "production"
        assert s1.DEBUG is True

    # Development with debug disabled
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "development", "DEBUG": "false"}):
        s2 = Settings()
        assert s2.ENVIRONMENT == "development"
        assert s2.DEBUG is False

    # Staging default debug (False)
    with mock.patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
        os.environ.pop("DEBUG", None)
        s3 = Settings(ADMIN_FRONTEND_URL="https://admin.example.test")
        assert s3.ENVIRONMENT == "staging"
        assert s3.DEBUG is False


def test_parse_debug_validator_directly():
    """Verify parse_debug classmethod validator directly."""
    # Truthy strings
    assert Settings.parse_debug("true") is True
    assert Settings.parse_debug("1") is True
    assert Settings.parse_debug("yes") is True
    assert Settings.parse_debug("on") is True
    assert Settings.parse_debug("dev") is True
    assert Settings.parse_debug("development") is True

    # Falsy strings
    assert Settings.parse_debug("false") is False
    assert Settings.parse_debug("0") is False
    assert Settings.parse_debug("no") is False
    assert Settings.parse_debug("off") is False
    assert Settings.parse_debug("prod") is False
    assert Settings.parse_debug("production") is False
    assert Settings.parse_debug("release") is False

    # Booleans and None
    assert Settings.parse_debug(True) is True
    assert Settings.parse_debug(False) is False
    assert Settings.parse_debug(None) is False
