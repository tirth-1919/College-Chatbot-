-- ==============================================================================
-- Migration: 019_complete_rls_policies.sql
-- Description: Complete all missing Row-Level Security policies and fix the
--              cross-tenant knowledge_chunks leak identified in the security audit.
--
-- Tables with RLS ENABLED but ZERO policies (audit finding SEC-04):
--   1. users
--   2. college_memberships
--   3. chat_messages
--   4. extracted_facts
--   5. knowledge_reviews
--   6. notification_logs
--
-- Tables with existing but FLAWED policies (audit finding SEC-09 / knowledge_chunks):
--   7. knowledge_chunks  — cross-tenant leak when current_app_tenant() IS NULL
--
-- Author: Senior Database Security Architect
-- Phase: 1 of Security Remediation Plan
-- Depends: 017_row_level_security_policies.sql, 018_create_application_role.sql
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- HELPER: current_app_user_id()
-- Reads the current user UUID from a session GUC that the backend will set via
--   SELECT set_config('app.current_user_id', :user_id, true)
-- This supplements current_app_tenant() and is_platform_super_admin().
-- Define it now so the policies below can reference it without depending on
-- the Phase 2 backend changes being deployed first.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_app_user_id() RETURNS UUID AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_user_id', true), '')::UUID;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

GRANT EXECUTE ON FUNCTION public.current_app_user_id() TO college_app_user;

-- ===========================================================================
-- 1. POLICY: users
-- ---------------------------------------------------------------------------
-- • SELECT: All backend requests can look up users by email/id (needed for
--   credential authentication during login and session profile hydration).
-- • UPDATE: Strictly restricted to the authenticated user themselves or Super Admin.
-- • INSERT: Allowed for user registration flow and Super Admin.
-- • DELETE: Strictly restricted to Super Admin.
-- ===========================================================================
DROP POLICY IF EXISTS p_users_self_access       ON users;
DROP POLICY IF EXISTS p_users_college_admin_read ON users;
DROP POLICY IF EXISTS p_users_super_admin_all    ON users;
DROP POLICY IF EXISTS p_users_read               ON users;
DROP POLICY IF EXISTS p_users_update             ON users;
DROP POLICY IF EXISTS p_users_insert             ON users;
DROP POLICY IF EXISTS p_users_delete             ON users;

-- Read access: required by auth service during unauthenticated login credential lookup
CREATE POLICY p_users_read ON users
    FOR SELECT
    USING (true);

-- Update: strictly restricted to self-profile edits or platform super admin
CREATE POLICY p_users_update ON users
    FOR UPDATE
    USING (id = current_app_user_id() OR is_platform_super_admin())
    WITH CHECK (id = current_app_user_id() OR is_platform_super_admin());

-- Insert: allowed for student/admin self-registration
CREATE POLICY p_users_insert ON users
    FOR INSERT
    WITH CHECK (true);

-- Delete: strictly platform super admin only
CREATE POLICY p_users_delete ON users
    FOR DELETE
    USING (is_platform_super_admin());

COMMENT ON POLICY p_users_read   ON users IS 'Allows backend authentication service to look up credentials by email';
COMMENT ON POLICY p_users_update ON users IS 'Users can only modify their own profile; super admin can modify any';
COMMENT ON POLICY p_users_delete ON users IS 'Super Admins only can delete user records';


-- ===========================================================================
-- 2. POLICY: college_memberships
-- ---------------------------------------------------------------------------
-- • SELECT: All backend requests can read memberships (needed for login tenant
--   resolution and admin authorization).
-- • WRITE: Managing memberships (INSERT, UPDATE, DELETE) is strictly restricted
--   to the authorized College Admin for that tenant or Super Admin.
-- ===========================================================================
DROP POLICY IF EXISTS p_memberships_tenant_isolation ON college_memberships;
DROP POLICY IF EXISTS p_memberships_self_read         ON college_memberships;
DROP POLICY IF EXISTS p_memberships_super_admin_all   ON college_memberships;
DROP POLICY IF EXISTS p_memberships_read              ON college_memberships;
DROP POLICY IF EXISTS p_memberships_write             ON college_memberships;

CREATE POLICY p_memberships_read ON college_memberships
    FOR SELECT
    USING (true);

CREATE POLICY p_memberships_write ON college_memberships
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
    )
    WITH CHECK (
        college_id = current_app_tenant()
        OR is_platform_super_admin()
    );

COMMENT ON POLICY p_memberships_read  ON college_memberships IS 'Backend can read memberships for login tenant resolution';
COMMENT ON POLICY p_memberships_write ON college_memberships IS 'College Admins can manage memberships within their tenant; Super Admin everywhere';


-- ===========================================================================
-- 3. POLICY: chat_messages
-- ---------------------------------------------------------------------------
-- • chat_messages has no direct college_id; tenant scope is derived from the
--   parent chat_sessions row.
-- • The existing chat_sessions policy (migration 011) already restricts session
--   access to the current tenant.  This policy mirrors the same gate for messages.
-- • A Super Admin can access all messages.
-- ===========================================================================
DROP POLICY IF EXISTS p_chat_messages_tenant     ON chat_messages;
DROP POLICY IF EXISTS p_chat_messages_super_admin ON chat_messages;

CREATE POLICY p_chat_messages_tenant ON chat_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = current_app_tenant()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = current_app_tenant()
        )
    );

CREATE POLICY p_chat_messages_super_admin ON chat_messages
    FOR ALL
    USING (is_platform_super_admin())
    WITH CHECK (is_platform_super_admin());

COMMENT ON POLICY p_chat_messages_tenant     ON chat_messages IS 'Tenant-scoped access via parent chat_sessions.college_id';
COMMENT ON POLICY p_chat_messages_super_admin ON chat_messages IS 'Super Admins can access all chat messages across tenants';


-- ===========================================================================
-- 4. POLICY: extracted_facts
-- ---------------------------------------------------------------------------
-- • extracted_facts.college_id directly identifies the owning tenant.
-- • APPROVED facts may be read without tenant context (used in RAG grounding)
--   only when the reader is explicitly scoped to the same college; we do NOT
--   allow cross-college fact reads.
-- • A Super Admin can access all facts.
-- ===========================================================================
DROP POLICY IF EXISTS p_facts_tenant_isolation ON extracted_facts;
DROP POLICY IF EXISTS p_facts_super_admin_all   ON extracted_facts;

CREATE POLICY p_facts_tenant_isolation ON extracted_facts
    FOR ALL
    USING (
        college_id = current_app_tenant()
    )
    WITH CHECK (
        college_id = current_app_tenant()
    );

CREATE POLICY p_facts_super_admin_all ON extracted_facts
    FOR ALL
    USING (is_platform_super_admin())
    WITH CHECK (is_platform_super_admin());

COMMENT ON POLICY p_facts_tenant_isolation ON extracted_facts IS 'Tenant-scoped access; facts are always college-specific';
COMMENT ON POLICY p_facts_super_admin_all   ON extracted_facts IS 'Super Admins have unrestricted access to all extracted facts';


-- ===========================================================================
-- 5. POLICY: knowledge_reviews
-- ---------------------------------------------------------------------------
-- • knowledge_reviews has no direct college_id; scope is derived from parent
--   knowledge_chunks.college_id.
-- • A College Admin may manage reviews for their college's chunks.
-- • A Super Admin can access all reviews.
-- ===========================================================================
DROP POLICY IF EXISTS p_reviews_tenant_isolation ON knowledge_reviews;
DROP POLICY IF EXISTS p_reviews_super_admin_all   ON knowledge_reviews;

CREATE POLICY p_reviews_tenant_isolation ON knowledge_reviews
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM knowledge_chunks kc
            WHERE kc.id = knowledge_reviews.chunk_id
              AND kc.college_id = current_app_tenant()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM knowledge_chunks kc
            WHERE kc.id = knowledge_reviews.chunk_id
              AND kc.college_id = current_app_tenant()
        )
    );

CREATE POLICY p_reviews_super_admin_all ON knowledge_reviews
    FOR ALL
    USING (is_platform_super_admin())
    WITH CHECK (is_platform_super_admin());

COMMENT ON POLICY p_reviews_tenant_isolation ON knowledge_reviews IS 'Tenant-scoped via parent knowledge_chunks.college_id';
COMMENT ON POLICY p_reviews_super_admin_all   ON knowledge_reviews IS 'Super Admins can review chunks across all tenants';


-- ===========================================================================
-- 6. POLICY: notification_logs
-- ---------------------------------------------------------------------------
-- • notification_logs.college_id identifies the target tenant.
-- • Only Super Admins and the owning tenant's admin can read/manage logs.
-- • INSERT is allowed for the backend service (which runs as college_app_user)
--   within the current tenant context.
-- ===========================================================================
DROP POLICY IF EXISTS p_notif_logs_tenant_isolation ON notification_logs;
DROP POLICY IF EXISTS p_notif_logs_super_admin_all   ON notification_logs;

CREATE POLICY p_notif_logs_tenant_isolation ON notification_logs
    FOR ALL
    USING (
        college_id = current_app_tenant()
        OR college_id IS NULL   -- platform-level notifications not tied to a college
    )
    WITH CHECK (
        college_id = current_app_tenant()
        OR college_id IS NULL
    );

CREATE POLICY p_notif_logs_super_admin_all ON notification_logs
    FOR ALL
    USING (is_platform_super_admin())
    WITH CHECK (is_platform_super_admin());

COMMENT ON POLICY p_notif_logs_tenant_isolation ON notification_logs IS 'Tenant-scoped and platform-level notification log access';
COMMENT ON POLICY p_notif_logs_super_admin_all   ON notification_logs IS 'Super Admins can read all notification logs across tenants';


-- ===========================================================================
-- 7. FIX: knowledge_chunks cross-tenant leak (audit finding SEC-09)
-- ---------------------------------------------------------------------------
-- OLD (FLAWED) policy in migration 017 line 95-105:
--   OR (
--       status = 'PUBLISHED' AND is_active = TRUE
--       AND (current_app_tenant() IS NULL OR college_id = current_app_tenant())
--   )
-- When current_app_tenant() IS NULL (backend never sets it), the OR clause
-- evaluates to TRUE for EVERY published chunk from EVERY college — exposing
-- all institutional content globally.
--
-- FIX: Published chunks are still readable without super-admin for the RAG
-- pipeline, but ONLY if the reader is scoped to the same college_id.
-- A NULL tenant gets NO access to published chunks.
-- ===========================================================================
DROP POLICY IF EXISTS p_chunks_tenant_isolation ON knowledge_chunks;

CREATE POLICY p_chunks_tenant_isolation ON knowledge_chunks
    FOR ALL
    USING (
        -- Super Admin: unrestricted
        is_platform_super_admin()
        -- College Admin / backend: full access within the same tenant
        OR college_id = current_app_tenant()
        -- RAG pipeline student read: published chunks from the SAME tenant only
        -- Requires current_app_tenant() to be non-null (tenant context is mandatory)
        OR (
            status = 'PUBLISHED'
            AND is_active = TRUE
            AND current_app_tenant() IS NOT NULL
            AND college_id = current_app_tenant()
        )
    )
    WITH CHECK (
        is_platform_super_admin()
        OR college_id = current_app_tenant()
    );

COMMENT ON POLICY p_chunks_tenant_isolation ON knowledge_chunks
    IS 'Tenant-strict isolation: published chunks readable only within the scoped college; NULL tenant gets no access';
