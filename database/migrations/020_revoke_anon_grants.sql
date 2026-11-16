-- ==============================================================================
-- Migration: 020_revoke_anon_grants.sql
-- Description: Revoke PostgREST / Supabase anon and authenticated role grants
--              from all application tables.
--
-- Background:
--   Supabase projects auto-grant SELECT / INSERT / UPDATE / DELETE on all
--   public schema tables to the built-in `anon` and `authenticated` roles.
--   Because this application uses CUSTOM JWT authentication (not Supabase Auth),
--   the anon key and authenticated role provide a completely bypass-able API
--   surface:  any client that obtains the Supabase anon key (which is embedded
--   in every frontend build) can reach the PostgREST endpoint and query tables
--   directly — bypassing the FastAPI application layer entirely.
--
-- This migration revokes those grants so that:
--   • Only college_app_user (the FastAPI backend role) can DML application tables.
--   • Direct PostgREST access returns permission-denied for all application tables.
--   • The Supabase service-role key still works for admin tooling (it connects as
--     the postgres / supabase_admin role which is unaffected by this migration).
--
-- Author: Senior Database Security Architect
-- Phase: 1 of Security Remediation Plan
-- Depends: 018_create_application_role.sql
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- NOTE: `anon` and `authenticated` are built-in Supabase PostgREST roles.
--       If your project does not use PostgREST at all, this migration is still
--       safe to apply; the REVOKE is a no-op if the grant never existed.
-- -----------------------------------------------------------------------------

-- 1. REVOKE from `anon` role (unauthenticated PostgREST requests)
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM anon;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM anon;

-- 2. REVOKE from `authenticated` role (Supabase Auth JWT PostgREST requests)
--    This project uses custom JWT, NOT Supabase Auth, so this role has no
--    legitimate callers.
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM authenticated;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM authenticated;
REVOKE ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public FROM authenticated;

-- 3. PREVENT future auto-grants for new tables by clearing default privileges
--    issued by Supabase bootstrap (safe to run even if defaults are already clear)
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM anon;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM authenticated;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM anon;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM authenticated;

-- 4. GRANT SCHEMA USAGE back to authenticated role ONLY for the two custom
--    RLS helper functions that the PostgREST query planner may call internally.
--    These functions are STABLE and read-only GUC accessors — no data exposure.
--    If you do NOT use PostgREST at all, comment these two lines out.
-- GRANT EXECUTE ON FUNCTION public.current_app_tenant()      TO authenticated;
-- GRANT EXECUTE ON FUNCTION public.is_platform_super_admin() TO authenticated;

-- 5. VERIFICATION QUERIES (run manually after applying to confirm)
-- Check no anon grants remain on any application table:
-- SELECT table_name, privilege_type, grantee
-- FROM information_schema.role_table_grants
-- WHERE grantee IN ('anon', 'authenticated')
--   AND table_schema = 'public'
-- ORDER BY table_name, grantee;
-- Expected: 0 rows

-- 6. COMMENT
COMMENT ON SCHEMA public IS
    'Application schema. DML access restricted to college_app_user (FastAPI backend). '
    'PostgREST anon/authenticated grants revoked in migration 020.';
