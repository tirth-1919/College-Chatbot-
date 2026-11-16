-- ==============================================================================
-- Migration: 011_prepare_rls.sql
-- Description: Enable PostgreSQL Row-Level Security (RLS) and define multi-tenant policies
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. TENANT SESSION CONTEXT HELPER FUNCTION
-- Reads the college_id bound to the current PostgreSQL transaction/connection
CREATE OR REPLACE FUNCTION current_app_tenant() RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_college_id', true), '')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- Checks if the current session has Global Super Administrator privileges
CREATE OR REPLACE FUNCTION is_platform_super_admin() RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(current_setting('app.is_super_admin', true) = 'true', FALSE);
EXCEPTION WHEN OTHERS THEN
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql STABLE;

-- 2. ENABLE ROW-LEVEL SECURITY ON ALL TENANT-SCOPED TABLES
ALTER TABLE website_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_paragraphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;

-- 3. POLICIES: colleges
ALTER TABLE colleges ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS p_colleges_public_read ON colleges;
CREATE POLICY p_colleges_public_read ON colleges
    FOR SELECT
    USING (is_active = TRUE AND status = 'APPROVED');

DROP POLICY IF EXISTS p_colleges_admin_all ON colleges;
CREATE POLICY p_colleges_admin_all ON colleges
    FOR ALL
    USING (id = current_app_tenant() OR is_platform_super_admin());

-- 4. POLICIES: knowledge_chunks
DROP POLICY IF EXISTS p_chunks_tenant_isolation ON knowledge_chunks;
CREATE POLICY p_chunks_tenant_isolation ON knowledge_chunks
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
        OR (status = 'PUBLISHED' AND is_active = TRUE) -- Allow public read for student chat RAG search
    );

-- 5. POLICIES: documents
DROP POLICY IF EXISTS p_documents_tenant_isolation ON documents;
CREATE POLICY p_documents_tenant_isolation ON documents
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
    );

-- 6. POLICIES: website_sources & crawl_jobs
DROP POLICY IF EXISTS p_sources_tenant_isolation ON website_sources;
CREATE POLICY p_sources_tenant_isolation ON website_sources
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

DROP POLICY IF EXISTS p_crawl_jobs_tenant_isolation ON crawl_jobs;
CREATE POLICY p_crawl_jobs_tenant_isolation ON crawl_jobs
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

-- 7. POLICIES: chat_sessions & chat_messages
DROP POLICY IF EXISTS p_chat_sessions_tenant ON chat_sessions;
CREATE POLICY p_chat_sessions_tenant ON chat_sessions
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

