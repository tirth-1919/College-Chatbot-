"""Application Settings Configuration Module.

Loads and validates environment variables using Pydantic Settings.
"""

from typing import List, Optional
from pathlib import Path
from ipaddress import ip_address
from urllib.parse import urlsplit
from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Load the same project-level .env regardless of whether the API is launched
# from the repository root or from the backend directory. In containers,
# compose-provided environment variables remain authoritative.
_CONFIG_FILE = Path(__file__).resolve()
_REPOSITORY_ROOT = next(
    (parent for parent in _CONFIG_FILE.parents if (parent / "README.md").is_file()),
    _CONFIG_FILE.parents[2],
)


class Settings(BaseSettings):
    """Global configuration settings for the backend API and database."""

    # Project metadata
    PROJECT_NAME: str = "AI FAQ College Chat Bot"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ADMIN_FRONTEND_URL: str = "http://localhost:3001"
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if v is None:
            return False
        if isinstance(v, str):
            val = v.strip().lower()
            if val in ("true", "1", "yes", "on", "dev", "development"):
                return True
            if val in ("false", "0", "no", "off", "prod", "production", "release"):
                return False
        return bool(v)

    @model_validator(mode="after")
    def validate_admin_frontend_url(self):
        raw_url = self.ADMIN_FRONTEND_URL.strip()
        parsed = urlsplit(raw_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or any(character.isspace() for character in raw_url)
            or "\\" in raw_url
        ):
            raise ValueError("ADMIN_FRONTEND_URL must be an absolute HTTP(S) URL without credentials, query, or fragment.")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("ADMIN_FRONTEND_URL contains an invalid port.") from exc

        hostname = parsed.hostname.rstrip(".").lower()
        is_loopback = hostname == "localhost" or hostname.endswith(".localhost")
        try:
            is_loopback = is_loopback or ip_address(hostname).is_loopback
        except ValueError:
            pass

        is_development = self.ENVIRONMENT.strip().lower() in {"development", "dev", "local"}
        if is_loopback and not is_development:
            raise ValueError("Localhost ADMIN_FRONTEND_URL is allowed only in development.")
        if parsed.scheme == "http" and not (is_loopback and is_development):
            raise ValueError("HTTP ADMIN_FRONTEND_URL is allowed only for a development loopback host.")
        if self.ENVIRONMENT.strip().lower() in {"production", "prod"} and parsed.scheme != "https":
            raise ValueError("Production ADMIN_FRONTEND_URL must use HTTPS.")

        self.ADMIN_FRONTEND_URL = raw_url.rstrip("/")
        return self

    @field_validator("SMTP_HOST", "SMTP_USERNAME", "SMTP_FROM_EMAIL", mode="before")
    @classmethod
    def normalize_optional_smtp_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("SMTP_PASSWORD", mode="before")
    @classmethod
    def normalize_optional_smtp_password(cls, value):
        return None if value == "" else value

    # Database Configuration (Supabase PostgreSQL + pgvector)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
        description="Admin async PostgreSQL URI (postgres/superuser) — used only for Alembic migrations and seed scripts. NOT used by the FastAPI runtime.",
    )
    DATABASE_APP_ROLE_URL: str = Field(
        default="postgresql+asyncpg://college_app_user:CHANGE_ME@localhost:5432/postgres",
        description="Least-privilege async PostgreSQL URI for the FastAPI runtime engine. Must connect as college_app_user (NOBYPASSRLS). RLS is enforced on all sessions from this engine.",
    )
    DATABASE_URL_SYNC: Optional[str] = Field(
        default=None,
        description="Sync PostgreSQL URI for Alembic migrations (psycopg2). Uses DATABASE_URL credentials if not set explicitly.",
    )

    # Supabase Cloud & Storage Configuration
    SUPABASE_URL: str = "https://placeholder-project.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"
    SUPABASE_STORAGE_BUCKET_DOCS: str = "college-documents"

    # Security & Authentication
    JWT_SECRET_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    JWT_ALGORITHM: str = "HS256"
    RLS_CONTEXT_SECRET: Optional[SecretStr] = Field(
        default=None,
        description="Independent secret shared with the database to authenticate transaction-local RLS context.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SMTP email transport. Credentials are optional for trusted SMTP relays.
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None
    SMTP_FROM_EMAIL: Optional[EmailStr] = None
    SMTP_STARTTLS: bool = True
    SMTP_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=120)
    EMAIL_DELIVERY_TIMEOUT_SECONDS: float = Field(default=15.0, gt=0, le=120)

    # Background Processing (Redis & Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # AI Configuration
    GEMINI_API_KEY: str = "placeholder-gemini-key"
    GEMINI_DEFAULT_MODEL: str = "gemini-3.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768

    SECONDARY_AI_ENABLED: bool = False
    SECONDARY_AI_PROVIDER: str = "openai"
    SECONDARY_AI_API_KEY: Optional[str] = None
    SECONDARY_AI_MODEL: str = "gpt-4o-mini"

    # Provider model priority lists (comma-separated)
    GEMINI_MODEL_PRIORITY: str = "gemini-1.5-flash,gemini-1.5-pro,gemini-2.0-flash-exp"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL_PRIORITY: str = "gpt-4o-mini,gpt-4o,gpt-3.5-turbo"
    XKIRO_API_KEY: Optional[str] = None
    XKIRO_API_BASE_URL: str = "https://api.xkiro.com/v1"
    XKIRO_MODEL_PRIORITY: str = "xkiro-chat,xkiro-fast"

    # Failover / reliability
    AI_MAX_RETRIES: int = 3
    AI_TIMEOUT_SECONDS: int = 30
    AI_CIRCUIT_BREAKER_THRESHOLD: int = 5
    AI_COOLDOWN_SECONDS: int = 60
    AI_GENERAL_ANSWERING_ENABLED: bool = True
    # Feature flag: controls when new ENUM values (AI_GUIDANCE, OPENAI_UNVERIFIED,
    # XKIRO_UNVERIFIED) are written to the database. Set to True only after
    # 002_ai_failover_columns.sql has been confirmed applied to the database.
    # Default is False (safe pre-migration state — old ENUM values are used).
    AI_NEW_ENUM_ENABLED: bool = False

    @property
    def gemini_model_list(self) -> list:
        return [m.strip() for m in self.GEMINI_MODEL_PRIORITY.split(",") if m.strip()]

    @property
    def openai_model_list(self) -> list:
        return [m.strip() for m in self.OPENAI_MODEL_PRIORITY.split(",") if m.strip()]

    @property
    def xkiro_model_list(self) -> list:
        return [m.strip() for m in self.XKIRO_MODEL_PRIORITY.split(",") if m.strip()]

    # Monitoring & Telemetry (Sentry)
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    @property
    def sync_database_url(self) -> str:
        """Returns synchronous database URL for Alembic or psycopg2 (uses admin role)."""
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def app_role_sync_database_url(self) -> str:
        """Returns synchronous version of the app-role URL (for diagnostics only)."""
        return self.DATABASE_APP_ROLE_URL.replace("postgresql+asyncpg://", "postgresql://")

    model_config = SettingsConfigDict(
        env_file=_REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Instantiate singleton settings
settings = Settings()

