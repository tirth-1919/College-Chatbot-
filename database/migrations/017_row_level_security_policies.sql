-- ==============================================================================
-- Migration: 017_row_level_security_policies.sql
-- Description: Production PostgreSQL Row-Level Security (RLS) & Multi-Tenant Separation
-- Author: Senior Database Security Architect
-- ==============================================================================

-- 1. Ensure RLS is Enabled across All Application Tables
ALTER TABLE colleges ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE college_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE crawl_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_paragraphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_ticket_replies ENABLE ROW LEVEL SECURITY;
ALTER TABLE in_app_notifications ENABLE ROW LEVEL SECURITY;

-- 2. POLICIES: support_tickets
DROP POLICY IF EXISTS p_support_tickets_tenant_isolation ON support_tickets;
CREATE POLICY p_support_tickets_tenant_isolation ON support_tickets
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
        OR user_id = auth.uid()
    );

-- 3. POLICIES: support_ticket_replies
DROP POLICY IF EXISTS p_ticket_replies_student_read ON support_ticket_replies;
CREATE POLICY p_ticket_replies_student_read ON support_ticket_replies
    FOR SELECT
    USING (
        -- Staff can see all replies including internal notes
        is_platform_super_admin()
        OR EXISTS (
            SELECT 1 FROM support_tickets st
            WHERE st.id = support_ticket_replies.ticket_id
              AND (st.college_id = current_app_tenant() OR is_platform_super_admin())
        )
        -- Students can only see non-internal replies for their own tickets
        OR (
            is_internal = FALSE
            AND EXISTS (
                SELECT 1 FROM support_tickets st
                WHERE st.id = support_ticket_replies.ticket_id
                  AND st.user_id = auth.uid()
            )
        )
    );

DROP POLICY IF EXISTS p_ticket_replies_staff_insert ON support_ticket_replies;
CREATE POLICY p_ticket_replies_staff_insert ON support_ticket_replies
    FOR INSERT
    WITH CHECK (
        is_platform_super_admin()
        OR EXISTS (
            SELECT 1 FROM support_tickets st
            WHERE st.id = support_ticket_replies.ticket_id
              AND (st.college_id = current_app_tenant() OR st.user_id = auth.uid())
        )
    );

-- 4. POLICIES: in_app_notifications
DROP POLICY IF EXISTS p_notifications_user_isolation ON in_app_notifications;
CREATE POLICY p_notifications_user_isolation ON in_app_notifications
    FOR ALL
    USING (
        user_id = auth.uid()
        OR college_id = current_app_tenant()
        OR is_platform_super_admin()
    );

-- 5. POLICIES: feedback
DROP POLICY IF EXISTS p_feedback_tenant_isolation ON feedback;
CREATE POLICY p_feedback_tenant_isolation ON feedback
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
        OR user_id = auth.uid()
    );

-- 6. POLICIES: knowledge_chunks (Tighten public search to target college only)
DROP POLICY IF EXISTS p_chunks_tenant_isolation ON knowledge_chunks;
CREATE POLICY p_chunks_tenant_isolation ON knowledge_chunks
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
        OR (
            status = 'PUBLISHED'
            AND is_active = TRUE
            AND (current_app_tenant() IS NULL OR college_id = current_app_tenant())
        )
    );

-- 7. POLICIES: website_pages & crawl_events
DROP POLICY IF EXISTS p_pages_tenant_isolation ON website_pages;
CREATE POLICY p_pages_tenant_isolation ON website_pages
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

DROP POLICY IF EXISTS p_events_tenant_isolation ON crawl_events;
CREATE POLICY p_events_tenant_isolation ON crawl_events
    FOR ALL
    USING (
        is_platform_super_admin()
        OR EXISTS (
            SELECT 1 FROM crawl_jobs cj
            WHERE cj.id = crawl_events.crawl_job_id
              AND (cj.college_id = current_app_tenant() OR is_platform_super_admin())
        )
    );

-- 8. POLICIES: document_pages & document_paragraphs
DROP POLICY IF EXISTS p_doc_pages_tenant_isolation ON document_pages;
CREATE POLICY p_doc_pages_tenant_isolation ON document_pages
    FOR ALL
    USING (
        is_platform_super_admin()
        OR EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = document_pages.document_id
              AND (d.college_id = current_app_tenant() OR is_platform_super_admin())
        )
    );

DROP POLICY IF EXISTS p_doc_paras_tenant_isolation ON document_paragraphs;
CREATE POLICY p_doc_paras_tenant_isolation ON document_paragraphs
    FOR ALL
    USING (
        is_platform_super_admin()
        OR EXISTS (
            SELECT 1 FROM documents d
            WHERE d.id = document_paragraphs.document_id
              AND (d.college_id = current_app_tenant() OR is_platform_super_admin())
        )
    );

-- 9. Verification Helper Comments
COMMENT ON POLICY p_support_tickets_tenant_isolation ON support_tickets IS 'Enforces strict tenant isolation and student user access for tickets';
COMMENT ON POLICY p_ticket_replies_student_read ON support_ticket_replies IS 'Redacts internal staff notes from ordinary student users';
COMMENT ON POLICY p_chunks_tenant_isolation ON knowledge_chunks IS 'Prevents cross-college leakage of institutional answers';

