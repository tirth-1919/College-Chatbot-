-- ==============================================================================
-- SYNTHETIC TEST ROLES AND PERMISSIONS FOR DISPOSABLE LOCAL ENVIRONMENT
-- ==============================================================================
-- Uses strictly disposable local credentials. Never use in production.
-- ==============================================================================

-- 1. Restricted application test role (LOGIN)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'college_app_user') THEN
        CREATE ROLE college_app_user WITH LOGIN PASSWORD 'DISPOSABLE_LOCAL_APP_PASSWORD';
    ELSE
        ALTER ROLE college_app_user WITH LOGIN PASSWORD 'DISPOSABLE_LOCAL_APP_PASSWORD';
    END IF;
END
$$;

-- 2. Synthetic administrative role for negative privilege-escalation testing
-- MUST NOT receive LOGIN or SUPERUSER attributes.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'test_synthetic_admin') THEN
        CREATE ROLE test_synthetic_admin WITH NOLOGIN;
    ELSE
        ALTER ROLE test_synthetic_admin WITH NOLOGIN;
    END IF;
END
$$;
COMMENT ON ROLE test_synthetic_admin IS 'Synthetic administrative role for negative privilege-escalation testing; NOLOGIN and no superuser attribute.';

-- 3. Dedicated test harness principal (for direct-login tests under D-07)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'college_test_harness') THEN
        CREATE ROLE college_test_harness WITH LOGIN PASSWORD 'DISPOSABLE_LOCAL_HARNESS_PASSWORD';
    ELSE
        ALTER ROLE college_test_harness WITH LOGIN PASSWORD 'DISPOSABLE_LOCAL_HARNESS_PASSWORD';
    END IF;
END
$$;

-- 4. Initial schema grants for disposable environment
GRANT USAGE ON SCHEMA public TO college_app_user;
GRANT USAGE ON SCHEMA public TO college_test_harness;
GRANT college_app_user TO college_test_harness;
