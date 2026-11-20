import pytest
from pydantic import ValidationError

from app.core.config import Settings


TEST_DATABASE_URL = (
    "postgresql+asyncpg://college_app_user:test-only-password"
    "@127.0.0.1:54322/postgres"
)


def isolated_test_database_settings():
    return {
        "DATABASE_URL": TEST_DATABASE_URL,
        "DATABASE_APP_ROLE_URL": TEST_DATABASE_URL,
    }


def test_test_environment_allows_loopback_admin_frontend_url():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="test",
        ADMIN_FRONTEND_URL="http://localhost:3001",
        **isolated_test_database_settings(),
    )

    assert settings.ADMIN_FRONTEND_URL == "http://localhost:3001"


def test_production_environment_rejects_loopback_admin_frontend_url():
    with pytest.raises(ValidationError, match="Localhost ADMIN_FRONTEND_URL"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            ADMIN_FRONTEND_URL="https://localhost:3001",
        )


def test_test_environment_rejects_non_loopback_database_target():
    with pytest.raises(ValidationError, match="Test database URLs"):
        Settings(
            _env_file=None,
            ENVIRONMENT="test",
            DATABASE_URL=(
                "postgresql+asyncpg://college_app_user:test-only-password"
                "@production.example:5432/postgres"
            ),
            DATABASE_APP_ROLE_URL=TEST_DATABASE_URL,
        )


def test_test_environment_rejects_admin_database_role():
    with pytest.raises(ValidationError, match="college_app_user"):
        Settings(
            _env_file=None,
            ENVIRONMENT="test",
            DATABASE_URL=TEST_DATABASE_URL,
            DATABASE_APP_ROLE_URL=(
                "postgresql+asyncpg://postgres:test-only-password"
                "@127.0.0.1:54322/postgres"
            ),
        )
