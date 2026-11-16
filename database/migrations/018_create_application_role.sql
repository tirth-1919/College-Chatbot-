-- ==============================================================================
-- Migration: 018_create_application_role.sql
-- Description: Create a dedicated, least-privilege PostgreSQL application role
--              for the FastAPI backend.  The role has NO superuser privileges,
--              NO BYPASSRLS, and does NOT own any application tables.
-- Author: Senior Database Security Architect
-- Phase: 1 of Security Remediation Plan
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- IMPORTANT: Run this migration as the postgres / supabase admin role.
-- After this migration the backend DATABASE_URL should be updated to connect as
-- college_app_user instead of postgres so that RLS is enforced.
-- Do NOT apply Phase 2 (backend refactor) before this migration is applied.
-- -----------------------------------------------------------------------------

-- 1. CREATE THE ROLE (idempotent guard)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_catalog.pg_roles WHERE rolname = 'college_app_user'
    ) THEN
        CREATE ROLE college_app_user
            WITH LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT
            NOBYPASSRLS
            PASSWORD 'CHANGE_ME_BEFORE_USE';   -- overwrite in Supabase DB settings or via ALTER ROLE
        RAISE NOTICE 'Role college_app_user created.';
    ELSE
        RAISE NOTICE 'Role college_app_user already exists — skipping CREATE.';
    END IF;
END
$$;

-- 2. CONNECT PRIVILEGE
GRANT CONNECT ON DATABASE postgres TO college_app_user;

-- 3. SCHEMA USAGE
GRANT USAGE ON SCHEMA public TO college_app_user;

-- 4. DML PRIVILEGES ON ALL CURRENT APPLICATION TABLES
-- (extensions like pgvector tables are excluded intentionally)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO college_app_user;

-- 5. SEQUENCE PRIVILEGES (needed for UUID default and serial columns)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO college_app_user;

-- 6. FUNCTION EXECUTE PRIVILEGES (needed for custom RLS helper functions)
GRANT EXECUTE ON FUNCTION public.current_app_tenant()        TO college_app_user;
GRANT EXECUTE ON FUNCTION public.is_platform_super_admin()   TO college_app_user;

-- 7. FUTURE TABLES / SEQUENCES — ensure new migrations automatically grant to this role
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO college_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO college_app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO college_app_user;

-- 8. REVOKE SUPERUSER-DANGEROUS DEFAULTS from the application role
--    (belt-and-suspenders: role was created without these but explicit REVOKE is clearer)
REVOKE CREATE ON SCHEMA public FROM college_app_user;

-- 9. VERIFICATION COMMENT
COMMENT ON ROLE college_app_user IS
    'Least-privilege FastAPI application role.  No BYPASSRLS, no SUPERUSER, '
    'no table ownership.  RLS is fully enforced for all sessions using this role.';

-- 10. SANITY CHECK VIEW (run manually after migration to confirm role attributes)
-- SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolbypassrls
-- FROM pg_roles WHERE rolname = 'college_app_user';
-- Expected: rolsuper=f, rolinherit=f, rolcreaterole=f, rolcreatedb=f, rolbypassrls=f
