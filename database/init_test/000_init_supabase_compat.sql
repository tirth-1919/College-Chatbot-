-- ==============================================================================
-- DATABASE-LEVEL COMPATIBILITY LAYER FOR SUPABASE SCHEMAS & EXTENSIONS
-- ==============================================================================
-- NOTE: This script provides PostgreSQL database-level compatibility for schemas
-- (e.g. 'auth') and required extensions ('vector', 'pgcrypto', 'uuid-ossp').
-- It does NOT provide a complete Supabase platform installation (GoTrue, PostgREST,
-- Kong, Realtime, Storage). The application under test connects purely via PostgreSQL.
-- ==============================================================================

-- 1. Required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Supabase compatibility schema
CREATE SCHEMA IF NOT EXISTS auth;

-- 3. Supabase auth compatibility stub functions
-- Required by legacy RLS policies referencing auth.uid() or auth.role()
CREATE OR REPLACE FUNCTION auth.uid()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULL::uuid;
$$;

CREATE OR REPLACE FUNCTION auth.role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT 'anon'::text;
$$;

COMMENT ON SCHEMA auth IS 'Database-level compatibility schema for Supabase functions; not a full Supabase platform.';

-- 4. Supabase PostgREST roles referenced by the repository's security migrations
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        CREATE ROLE anon NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
END
$$;
