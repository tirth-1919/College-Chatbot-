-- ==============================================================================
-- Migration: 008_create_ai_and_audit_tables.sql
-- Description: Create AI provider configuration, telemetry, and platform audit logs
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. Entity: ai_provider_configs
CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) NOT NULL, -- 'gemini', 'openai', 'groq', 'anthropic'
    model_name VARCHAR(100) NOT NULL, -- 'gemini-1.5-flash', 'gpt-4o-mini'
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    timeout_seconds INTEGER NOT NULL DEFAULT 15,
    max_retries INTEGER NOT NULL DEFAULT 3,
    temperature FLOAT NOT NULL DEFAULT 0.2,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_model UNIQUE (provider_name, model_name)
);

COMMENT ON TABLE ai_provider_configs IS 'Global AI provider runtime parameters managed by the Super Administrator';

-- 2. Entity: ai_provider_events (also referred to as provider_events)
CREATE TABLE IF NOT EXISTS ai_provider_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES ai_provider_configs(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL, -- 'SUCCESS', 'TIMEOUT', 'RATE_LIMITED', 'CIRCUIT_BREAKER_FAILOVER'
    latency_ms INTEGER NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ai_provider_events IS 'Telemetry stream tracking latency, token usage, and circuit-breaker events';

-- 3. Entity: audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id) ON DELETE SET NULL,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL, -- 'COLLEGE_APPROVED', 'FACT_EDITED', 'KNOWLEDGE_PUBLISHED'
    target_entity VARCHAR(100) NOT NULL,
    target_id UUID NOT NULL,
    payload_diff JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE audit_logs IS 'Immutable compliance audit trail of all security and privileged operations';

