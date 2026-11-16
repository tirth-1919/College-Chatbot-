-- ==============================================================================
-- Migration: 007_create_chat_tables.sql
-- Description: Create chat sessions and conversational message logs
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. Entity: chat_sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Nullable for unauthenticated/guest users
    session_title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    language VARCHAR(10) NOT NULL DEFAULT 'en', -- 'en', 'hi', 'gu'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE chat_sessions IS 'Conversational threads scoped to a specific college tenant';
COMMENT ON COLUMN chat_sessions.language IS 'User preferred conversation language (en = English, hi = Hindi, gu = Gujarati)';

-- 2. Entity: chat_messages
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    message_text TEXT NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    answer_source_type answer_source_type NOT NULL DEFAULT 'NO_RELIABLE_INFORMATION',
    source_citations JSONB NOT NULL DEFAULT '[]'::jsonb,
    token_count INTEGER NOT NULL DEFAULT 0,
    model_used VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE chat_messages IS 'Turn-by-turn prompts, assistant answers, verification status, and source citations';
COMMENT ON COLUMN chat_messages.is_verified IS 'True only if grounded in official website or admin-verified documents';
COMMENT ON COLUMN chat_messages.source_citations IS 'Structured JSON array of cited sources with title, URL, page number, and section';

