-- ==============================================================================
-- Migration: 010_create_indexes.sql
-- Description: Create performance, tenant lookup, full-text, and vector indexes
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. TENANT & CORE IDENTITY INDEXES
CREATE INDEX IF NOT EXISTS idx_colleges_status ON colleges(status);
CREATE INDEX IF NOT EXISTS idx_colleges_domain ON colleges(official_domain);
CREATE INDEX IF NOT EXISTS idx_colleges_is_active ON colleges(is_active);

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

CREATE INDEX IF NOT EXISTS idx_memberships_college ON college_memberships(college_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON college_memberships(user_id);

-- 2. CRAWLER SUBSYSTEM INDEXES
CREATE INDEX IF NOT EXISTS idx_web_sources_college ON website_sources(college_id);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_college_status ON crawl_jobs(college_id, status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source ON crawl_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_crawl_events_job ON crawl_events(crawl_job_id);

CREATE INDEX IF NOT EXISTS idx_web_pages_college ON website_pages(college_id);
CREATE INDEX IF NOT EXISTS idx_web_pages_hash ON website_pages(college_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_web_pages_url ON website_pages(url);

-- 3. DOCUMENT & OCR SUBSYSTEM INDEXES
CREATE INDEX IF NOT EXISTS idx_documents_college ON documents(college_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(college_id, checksum_sha256);

CREATE INDEX IF NOT EXISTS idx_doc_pages_doc ON document_pages(document_id);
CREATE INDEX IF NOT EXISTS idx_doc_paragraphs_page ON document_paragraphs(page_id);
CREATE INDEX IF NOT EXISTS idx_doc_paragraphs_doc ON document_paragraphs(document_id);

-- 4. KNOWLEDGE BASE & FACT INDEXES
CREATE INDEX IF NOT EXISTS idx_facts_college_category ON extracted_facts(college_id, category);
CREATE INDEX IF NOT EXISTS idx_facts_status ON extracted_facts(verification_status);

CREATE INDEX IF NOT EXISTS idx_chunks_tenant_lookup ON knowledge_chunks(college_id, status, is_active);
CREATE INDEX IF NOT EXISTS idx_reviews_chunk ON knowledge_reviews(chunk_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON knowledge_reviews(reviewed_by_user_id);

-- 5. PGVECTOR HNSW COSINE SIMILARITY INDEX
-- Enables millisecond approximate nearest neighbor retrieval across thousands of chunks
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 6. FULL-TEXT SEARCH GIN INDEX (HYBRID RETRIEVAL)
-- Enables BM25-equivalent keyword ranking alongside vector embeddings
CREATE INDEX IF NOT EXISTS idx_chunks_fts 
ON knowledge_chunks USING gin(to_tsvector('english', chunk_text));

-- 7. CHAT CONVERSATION & SUPPORT INDEXES
CREATE INDEX IF NOT EXISTS idx_chat_sessions_college_user ON chat_sessions(college_id, user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_college ON feedback(college_id);
CREATE INDEX IF NOT EXISTS idx_feedback_message ON feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_tickets_college_status ON support_tickets(college_id, status);

-- 8. AUDIT & TELEMETRY INDEXES
CREATE INDEX IF NOT EXISTS idx_provider_events_config ON ai_provider_events(config_id, event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_college ON audit_logs(college_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

