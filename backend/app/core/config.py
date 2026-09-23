import os
from pydantic import field_validator, model_validator, ValidationError
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application Info — permanent platform identity (multi-college).
    # This is the PRODUCT name, independent of any college tenant.
    APP_NAME: str = "AI-Powered Colleges Chatbot"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # DEBUG may be set machine-wide to non-boolean values (e.g. DEBUG=release).
    # The validator below normalizes valid boolean strings and safely treats any
    # unrecognized value as False (production behaviour) instead of crashing startup.
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _normalize_debug(cls, value):
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ("1", "true", "yes", "on"):
                return True
            if text in ("0", "false", "no", "off"):
                return False
            # Unrecognized value (e.g. "release"): do not crash — assume not debug
            return False
        return bool(value)

    # Known weak/default SECRET_KEY values. In production these must NEVER be
    # accepted, even if they happen to exceed the minimum length.
    _KNOWN_WEAK_SECRETS = (
        "ait-ai-super-secret-key-change-in-production-2026",
        "secret",
        "secretkey",
        "changeme",
        "change-me",
        "your-secret-key",
        "your-secret-key-here",
        "supersecret",
        "super-secret-key",
        "insecure-secret-key-for-development-only",
        "dev-secret-key",
        "development-secret-key",
        "test-secret-key",
        "my-secret-key",
        "jwt-secret",
        "django-insecure",
    )

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.ENVIRONMENT.lower() in ("production", "prod"):
            # Production must always run with debug output disabled.
            object.__setattr__(self, "DEBUG", False)

            key = (self.SECRET_KEY or "")
            problems = []
            if not key.strip():
                problems.append("SECRET_KEY is missing or empty")
            elif len(key) < 32:
                problems.append("SECRET_KEY is too short (minimum 32 characters)")
            elif key.strip().lower() in self._KNOWN_WEAK_SECRETS:
                problems.append("SECRET_KEY matches a known default/weak value")

            if problems:
                # Deliberately generic: never echo the configured key value.
                raise ValueError(
                    "Refusing to start in production: " + "; ".join(problems)
                    + ". Set a strong SECRET_KEY environment variable "
                    "(e.g. python -c \"import secrets; print(secrets.token_urlsafe(48))\")."
                )
        return self

    # Institution Info
    INSTITUTION_NAME: str = "Ahmedabad Institute of Technology"
    INSTITUTION_SHORT_NAME: str = "AIT"
    INSTITUTION_URL: str = "https://www.aitindia.in"

    # Security & Auth
    # Development fallback ONLY: never accepted in production (see the
    # validate_production_secrets model validator, which rejects startup).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "ait-ai-super-secret-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin bootstrap: set this env var to create the first admin account on startup.
    # If empty, no admin is auto-seeded (admin must be created via setup command).
    # Value is consumed on first run; credentials written to .admin_bootstrap.txt (gitignored).
    ADMIN_BOOTSTRAP_PASSWORD: str = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "")
        # Demo/dev-only seed account (email 1@gmail.com). Created ONLY when this
    # flag is enabled AND the environment is not production. Default: enabled
    # in development so local/demo setups work out of the box.
    SEED_DEMO_USER: bool = os.getenv("SEED_DEMO_USER", "true").lower() in ("1", "true", "yes")

    # Google OAuth (Graceful notification if empty)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Database
    # Defaults to SQLite for immediate local plug-and-play development,
    # fully compatible with production PostgreSQL URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/ait_assistant.db")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"

    # AI Providers
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Ordered comma-separated Gemini model candidates; the adapter rotates only on quota/rate-limit errors.
    GEMINI_MODELS: str = os.getenv(
        "GEMINI_MODELS",
        "gemini-3.7-flash,gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash,"
        "gemini-flash-latest,gemini-3.5-flash-lite,gemini-3.1-flash-lite,"
        "gemini-flash-lite-latest,gemini-2.5-flash,gemini-2.5-flash-lite",
    )
    GEMINI_MODEL_COOLDOWN_SECONDS: int = int(os.getenv("GEMINI_MODEL_COOLDOWN_SECONDS", "300"))
    # A Gemini call receives only its requested model.  The router owns model and
    # provider failover, so a stalled first response must be bounded tightly.
    AI_PROVIDER_INITIAL_TIMEOUT_SECONDS: int = int(os.getenv("AI_PROVIDER_INITIAL_TIMEOUT_SECONDS", "8"))
    AI_PROVIDER_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("AI_PROVIDER_REQUEST_TIMEOUT_SECONDS", "30"))
    AI_PROVIDER_HARD_TIMEOUT_SECONDS: int = int(os.getenv("AI_PROVIDER_HARD_TIMEOUT_SECONDS", "60"))
    GEMINI_REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "8"))
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # FREE-ONLY mode: when true, paid OpenAI/Anthropic models and paid
    # OpenRouter models are never selected automatically. Gemini (existing
    # free access), Groq free-tier-eligible models, OpenRouter verified-free
    # models (pricing==0 metadata) and local Ollama models remain eligible.
    AI_FREE_ONLY_MODE: bool = os.getenv("AI_FREE_ONLY_MODE", "true").lower() in ("1", "true", "yes", "on")

    # Automatic multi-provider quota-aware failover
    PROVIDER_FAILOVER_ENABLED: bool = os.getenv("PROVIDER_FAILOVER_ENABLED", "true").lower() == "true"
    PROVIDER_QUOTA_CHECK_ENABLED: bool = os.getenv("PROVIDER_QUOTA_CHECK_ENABLED", "true").lower() == "true"
    PROVIDER_COOLDOWN_SECONDS: int = int(os.getenv("PROVIDER_COOLDOWN_SECONDS", "300"))
    # Hard cap on provider/model attempts per request; never exceeds the candidate list size
    PROVIDER_MAX_ATTEMPTS: int = int(os.getenv("PROVIDER_MAX_ATTEMPTS", "6"))
    GEMINI_PROVIDER_TIMEOUT_THRESHOLD: int = int(os.getenv("GEMINI_PROVIDER_TIMEOUT_THRESHOLD", "2"))
    PROVIDER_HEALTH_CHECK_INTERVAL: int = int(os.getenv("PROVIDER_HEALTH_CHECK_INTERVAL", "60"))

    # Storage & Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./backend/storage/uploads")
    IMAGE_STORAGE_DIR: str = os.getenv("IMAGE_STORAGE_DIR", "./backend/storage/images")
    MAX_FILE_SIZE_BYTES: int = 25 * 1024 * 1024  # 25MB
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "docx", "xlsx", "csv", "txt", "md", "png", "jpg", "jpeg", "webp"
    ]

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://www.aitindia.in"
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"

def load_settings_safe() -> Settings:
    """Load Settings and convert validation failures into a sanitized
    startup error. Pydantic's ValidationError repr embeds the offending
    input value (e.g. SECRET_KEY) in its context — never expose that in
    logs. Only the validation message is surfaced."""
    try:
        return Settings()
    except ValidationError as exc:
        messages = "; ".join(err.get("msg", "invalid configuration") for err in exc.errors())
        raise RuntimeError(f"Configuration error: {messages}") from None


settings = load_settings_safe()
