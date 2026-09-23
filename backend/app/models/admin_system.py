import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, JSON, Integer, Float
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class AiProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_name = Column(String(50), unique=True, index=True, nullable=False)  # gemini, openai, anthropic, ollama
    display_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # Lower number = higher priority
    base_url = Column(String(500), nullable=True)
    api_key_env = Column(String(100), nullable=True)
    is_allowed_for_private_data = Column(Boolean, default=False, nullable=False)
    is_allowed_for_documents = Column(Boolean, default=True, nullable=False)
    is_allowed_for_images = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    models = relationship("AiModelRegistry", back_populates="provider", cascade="all, delete-orphan")

class AiModelRegistry(Base):
    __tablename__ = "ai_model_registry"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_id = Column(String(36), ForeignKey("ai_provider_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    model_identifier = Column(String(100), nullable=False, index=True)  # e.g. gemini-3.7-flash, gpt-4o-mini
    display_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=1, nullable=False)
    
    # Free-tier classification. One of:
    #   FREE_TIER_ELIGIBLE  — provider metadata confirms zero cost
    #   PAID                — provider metadata confirms a price
    #   UNKNOWN             — no authoritative info (never claim free)
    #   NOT_APPLICABLE      — local provider (e.g. Ollama)
    free_tier_status = Column(String(30), default="UNKNOWN", nullable=False)

    # Capability Matrix
    supports_text = Column(Boolean, default=True, nullable=False)
    supports_vision = Column(Boolean, default=False, nullable=False)
    supports_documents = Column(Boolean, default=False, nullable=False)
    supports_streaming = Column(Boolean, default=True, nullable=False)
    supports_structured_output = Column(Boolean, default=True, nullable=False)
    supports_tool_calling = Column(Boolean, default=False, nullable=False)
    context_limit = Column(Integer, default=32000, nullable=False)
    supported_languages = Column(JSON, default=lambda: ["en", "gu", "hi"])

    # Health & Circuit Breaker State
    health_status = Column(String(20), default="HEALTHY", nullable=False)  # HEALTHY, OPEN, HALF_OPEN
    consecutive_failures = Column(Integer, default=0, nullable=False)
    cooldown_until = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(Text, nullable=True)

    # Runtime Metrics
    requests_total = Column(Integer, default=0, nullable=False)
    requests_success = Column(Integer, default=0, nullable=False)
    requests_failed = Column(Integer, default=0, nullable=False)
    rate_limit_429_count = Column(Integer, default=0, nullable=False)
    avg_latency_ms = Column(Float, default=0.0, nullable=False)
    p95_latency_ms = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    provider = relationship("AiProviderConfig", back_populates="models")
    quotas = relationship("AiQuota", back_populates="model", cascade="all, delete-orphan")

class AiQuota(Base):
    __tablename__ = "ai_quotas"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_id = Column(String(36), ForeignKey("ai_model_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    quota_type = Column(String(50), default="requests_per_day", nullable=False)  # requests_per_minute, requests_per_day, tokens_per_minute
    limit_amount = Column(Integer, default=10000, nullable=False)
    used_amount = Column(Integer, default=0, nullable=False)
    remaining_amount = Column(Integer, default=10000, nullable=False)
    reset_time = Column(DateTime, nullable=True)
    source = Column(String(50), default="ESTIMATED", nullable=False)  # PROVIDER_REPORTED, ESTIMATED, UNKNOWN
    last_updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    model = relationship("AiModelRegistry", back_populates="quotas")

class AiUsageLog(Base):
    __tablename__ = "ai_usage_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    conversation_id = Column(String(36), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    provider_name = Column(String(50), nullable=False, index=True)
    model_identifier = Column(String(100), nullable=False, index=True)
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    http_status = Column(Integer, default=200, nullable=False)
    success = Column(Boolean, default=True, nullable=False)
    error_type = Column(String(100), nullable=True)
    failover_occurred = Column(Boolean, default=False, nullable=False)
    fallback_from_model = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class AiCredential(Base):
    """Multi-credential registry (one provider may hold several API keys).

    SECURITY: api_key_encrypted is encrypted at rest; the encryption key is
    derived separately from SECRET_KEY. The raw key is NEVER returned by any
    API — only masked_key (last 4 chars) is exposed.
    """
    __tablename__ = "ai_credentials"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_name = Column(String(50), nullable=False, index=True)  # gemini, groq, ...
    label = Column(String(100), nullable=True)                      # "Gemini Production Key 2"
    api_key_encrypted = Column(Text, nullable=False)                # encrypted at rest
    masked_key = Column(String(20), nullable=False, default="")    # "••••••••ABCD"
    priority = Column(Integer, default=1, nullable=False)           # lower = tried first
    is_enabled = Column(Boolean, default=True, nullable=False)
    # FREE_TIER_ELIGIBLE | PAID | UNKNOWN | NOT_APPLICABLE
    free_tier_status = Column(String(30), default="UNKNOWN", nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)        # last test result
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class KnowledgeConflict(Base):
    __tablename__ = "knowledge_conflicts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    college_id = Column(String(36), nullable=True, index=True)
    topic = Column(String(255), nullable=False, index=True)
    source_a = Column(String(500), nullable=False)  # e.g., Website: https://www.aitindia.in/departments/bca
    source_b = Column(String(500), nullable=False)  # e.g., Database Entity: BCA Fees
    value_a = Column(Text, nullable=False)
    value_b = Column(Text, nullable=False)
    detected_discrepancy = Column(Text, nullable=False)
    resolution_status = Column(String(50), default="UNRESOLVED", nullable=False)  # UNRESOLVED, RESOLVED_A, RESOLVED_B, SUPERSEDED, DISMISSED
    resolved_by = Column(String(36), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slug = Column(String(100), unique=True, index=True, nullable=False)  # ait_system_prompt, image_explainer_prompt
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    active_version_number = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan", order_by="PromptVersion.version_number.desc()")

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    prompt_id = Column(String(36), ForeignKey("system_prompts.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    change_reason = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(100), default="System", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    prompt = relationship("SystemPrompt", back_populates="versions")

class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    key = Column(String(100), unique=True, index=True, nullable=False)  # IMAGE_ANSWERS, VOICE, RAG, AI_FAILOVER, WEBSITE_SYNC, SEMANTIC_CACHE, NEW_CHAT_UI
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    updated_by = Column(String(100), default="System", nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class SystemBackup(Base):
    __tablename__ = "system_backups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    backup_type = Column(String(50), default="FULL", nullable=False)  # FULL, KNOWLEDGE_ONLY, USERS_ONLY
    file_size_bytes = Column(Integer, default=0, nullable=False)
    storage_path = Column(String(500), nullable=False)
    status = Column(String(50), default="COMPLETED", nullable=False)  # IN_PROGRESS, COMPLETED, FAILED
    created_by = Column(String(100), default="System", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
