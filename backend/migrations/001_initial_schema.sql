-- ==============================================================================
-- AI FAQ COLLEGE CHAT BOT - INITIAL DATABASE SCHEMA (20 ENTITIES + PGVECTOR + RLS)
-- Target Database: Supabase PostgreSQL 15+
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. ENUM TYPES
DO $$ BEGIN
    CREATE TYPE college_status AS ENUM ('PENDING', 'APPROVED', 'SUSPENDED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('STUDENT', 'COLLEGE_ADMIN', 'SUPER_ADMIN');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE membership_role AS ENUM ('ADMIN', 'EDITOR', 'VIEWER');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE crawl_job_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE document_status AS ENUM ('PROCESSING', 'PENDING_REVIEW', 'COMPLETED', 'FAILED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE knowledge_status AS ENUM (
        'PROCESSING', 'PENDING_REVIEW', 'APPROVED', 'PUBLISHED', 
        'REJECTED', 'STALE', 'SUPERSEDED', 'FAILED'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE answer_source_type AS ENUM (
        'OFFICIAL_WEBSITE', 'ADMIN_VERIFIED', 'GEMINI_UNVERIFIED', 
        'SECONDARY_AI_FALLBACK', 'NO_RELIABLE_INFORMATION'
    );
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE support_ticket_status AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- ==============================================================================
-- 3. TENANT & CORE IDENTITY ENTITIES
-- ==============================================================================

-- Entity 1: colleges (Tenants)
CREATE TABLE IF NOT EXISTS colleges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    official_domain VARCHAR(255) NOT NULL,
    logo_url TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    status college_status NOT NULL DEFAULT 'PENDING',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_colleges_status ON colleges(status);
CREATE INDEX IF NOT EXISTS idx_colleges_domain ON colleges(official_domain);

-- Entity 2: users (All User Accounts)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'STUDENT',
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    verification_token VARCHAR(255),
    reset_password_token VARCHAR(255),
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Entity 3: college_memberships (Tenant-User Mapping for Admins)
CREATE TABLE IF NOT EXISTS college_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_college membership_role NOT NULL DEFAULT 'ADMIN',
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_college_user UNIQUE (college_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_memberships_college ON college_memberships(college_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON college_memberships(user_id);

-- ==============================================================================
-- 4. WEBSITE CRAWLER SUBSYSTEM ENTITIES
-- ==============================================================================

-- Entity 4: website_sources (Target URLs configured by College Admin)
CREATE TABLE IF NOT EXISTS website_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    base_url TEXT NOT NULL,
    allowed_subdomains TEXT,
    max_depth INTEGER NOT NULL DEFAULT 2,
    max_pages INTEGER NOT NULL DEFAULT 50,
    crawl_frequency VARCHAR(50) NOT NULL DEFAULT 'WEEKLY',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_sources_college ON website_sources(college_id);

-- Entity 5: crawl_jobs (Job execution records)
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES website_sources(id) ON DELETE CASCADE,
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    status crawl_job_status NOT NULL DEFAULT 'PENDING',
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_college_status ON crawl_jobs(college_id, status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source ON crawl_jobs(source_id);

-- Entity 6: crawl_job_events (Granular execution logs)
CREATE TABLE IF NOT EXISTS crawl_job_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_job_id UUID NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_events_job ON crawl_job_events(crawl_job_id);

-- Entity 7: website_pages (Fetched and parsed pages)
CREATE TABLE IF NOT EXISTS website_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES website_sources(id) ON DELETE CASCADE,
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    content_hash VARCHAR(64) NOT NULL,
    cleaned_text TEXT NOT NULL,
    http_status INTEGER NOT NULL DEFAULT 200,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_web_pages_college ON website_pages(college_id);
CREATE INDEX IF NOT EXISTS idx_web_pages_hash ON website_pages(college_id, content_hash);

-- ==============================================================================
-- 5. PDF DOCUMENT & OCR SUBSYSTEM ENTITIES
-- ==============================================================================

-- Entity 8: documents (Uploaded PDF metadata)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
    file_size_bytes BIGINT NOT NULL,
    total_pages INTEGER NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64) NOT NULL,
    processing_status document_status NOT NULL DEFAULT 'PROCESSING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_college ON documents(college_id);
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(college_id, checksum_sha256);

-- Entity 9: document_pages (Deconstructed pages)
CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    extracted_text TEXT NOT NULL,
    is_scanned BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_applied BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_doc_page UNIQUE (document_id, page_number)
);

CREATE INDEX IF NOT EXISTS idx_doc_pages_doc ON document_pages(document_id);

-- Entity 10: document_paragraphs (Structured paragraphs and coordinates)
CREATE TABLE IF NOT EXISTS document_paragraphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES document_pages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    paragraph_index INTEGER NOT NULL,
    paragraph_text TEXT NOT NULL,
    bounding_box JSONB
);

CREATE INDEX IF NOT EXISTS idx_doc_paragraphs_page ON document_paragraphs(page_id);

-- ==============================================================================
-- 6. KNOWLEDGE BASE & HUMAN REVIEW ENTITIES
-- ==============================================================================

-- Entity 11: extracted_facts (Atomic extracted claims)
CREATE TABLE IF NOT EXISTS extracted_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'WEBSITE', 'PDF', 'MANUAL'
    source_id UUID NOT NULL,
    category VARCHAR(100) NOT NULL, -- 'ADMISSION', 'FEES', 'COURSES', 'FACULTY', 'HOSTEL'
    fact_key VARCHAR(255) NOT NULL,
    fact_value TEXT NOT NULL,
    verification_status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_facts_college_category ON extracted_facts(college_id, category);
CREATE INDEX IF NOT EXISTS idx_facts_status ON extracted_facts(verification_status);

-- Entity 12: knowledge_chunks (Embeddings & Semantic Search Unit)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- 'OFFICIAL_WEBSITE', 'ADMIN_VERIFIED'
    source_id UUID NOT NULL,
    source_url TEXT,
    page_number INTEGER,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(768), -- Google Gemini text-embedding-004 dimension
    status knowledge_status NOT NULL DEFAULT 'PENDING_REVIEW',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_tenant_lookup ON knowledge_chunks(college_id, status, is_active);

-- HNSW Vector Index for ultra-fast Cosine Similarity Retrieval
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Full-Text Search index for BM25 hybrid ranking
CREATE INDEX IF NOT EXISTS idx_chunks_fts 
ON knowledge_chunks USING gin(to_tsvector('english', chunk_text));

-- Entity 13: knowledge_reviews (Human-in-the-loop review audit)
CREATE TABLE IF NOT EXISTS knowledge_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES knowledge_chunks(id) ON DELETE CASCADE,
    reviewed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    review_action VARCHAR(50) NOT NULL, -- 'APPROVE', 'REJECT', 'EDIT', 'PUBLISH', 'UNPUBLISH'
    notes TEXT,
    edited_chunk_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reviews_chunk ON knowledge_reviews(chunk_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON knowledge_reviews(reviewed_by_user_id);

-- ==============================================================================
-- 7. CHAT CONVERSATION & STUDENT TELEMETRY ENTITIES
-- ==============================================================================

-- Entity 14: chat_sessions (Student conversation threads)
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Nullable for anonymous guest chats
    session_title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    language VARCHAR(10) NOT NULL DEFAULT 'en', -- 'en', 'hi', 'gu'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_college_user ON chat_sessions(college_id, user_id);

-- Entity 15: chat_messages (Individual prompt and response turns)
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

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);

-- Entity 16: feedback (User ratings on responses)
CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    rating INTEGER NOT NULL, -- 1 for thumbs up, -1 for thumbs down
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_college ON feedback(college_id);

-- Entity 17: support_tickets (Escalated inquiries when AI cannot verify)
CREATE TABLE IF NOT EXISTS support_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    student_name VARCHAR(255) NOT NULL,
    student_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status support_ticket_status NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickets_college_status ON support_tickets(college_id, status);

-- ==============================================================================
-- 8. PLATFORM GOVERNANCE & AUDIT ENTITIES
-- ==============================================================================

-- Entity 18: ai_provider_configs (LLM configuration managed by Super Admin)
CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) NOT NULL, -- 'gemini', 'openai', 'groq'
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

-- Entity 19: provider_events (AI usage, tokens, and latency telemetry)
CREATE TABLE IF NOT EXISTS provider_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID REFERENCES ai_provider_configs(id) ON DELETE SET NULL,
    event_type VARCHAR(50) NOT NULL, -- 'SUCCESS', 'TIMEOUT', 'RATE_LIMITED', 'CIRCUIT_BREAKER_FAILOVER'
    latency_ms INTEGER NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_provider_events_config ON provider_events(config_id, event_type);

-- Entity 20: audit_logs (Immutable security audit stream)
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

CREATE INDEX IF NOT EXISTS idx_audit_logs_college ON audit_logs(college_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

-- ==============================================================================
-- 9. ROW-LEVEL SECURITY (RLS) FOR MULTI-TENANCY
-- ==============================================================================

-- Enable RLS on all tenant-specific tables
ALTER TABLE website_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;

-- Dynamic Tenant Isolation Policy Example:
-- Checks whether session tenant setting matches row college_id, or allows Super Admin bypass.
CREATE OR REPLACE FUNCTION current_app_tenant() RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_college_id', true), '')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- RLS Policy on knowledge_chunks
DROP POLICY IF EXISTS p_knowledge_chunks_tenant ON knowledge_chunks;
CREATE POLICY p_knowledge_chunks_tenant ON knowledge_chunks
    FOR ALL
    USING (
        college_id = current_app_tenant() 
        OR current_setting('app.is_super_admin', true) = 'true'
        OR (status = 'PUBLISHED' AND is_active = TRUE) -- Allow read for published chunks in student chat
    );

-- RLS Policy on documents
DROP POLICY IF EXISTS p_documents_tenant ON documents;
CREATE POLICY p_documents_tenant ON documents
    FOR ALL
    USING (
        college_id = current_app_tenant() 
        OR current_setting('app.is_super_admin', true) = 'true'
    );
