-- ==============================================================================
-- Development Seed Data: development_seed.sql
-- Description: Inserts initial system configurations and test data for local development
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. SEED AI PROVIDER CONFIGURATIONS
INSERT INTO ai_provider_configs (id, provider_name, model_name, is_primary, is_active, timeout_seconds, max_retries, temperature)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'gemini', 'gemini-1.5-flash', TRUE, TRUE, 15, 3, 0.2),
    ('00000000-0000-0000-0000-000000000002', 'gemini', 'text-embedding-004', FALSE, TRUE, 10, 3, 0.0),
    ('00000000-0000-0000-0000-000000000003', 'openai', 'gpt-4o-mini', FALSE, TRUE, 15, 2, 0.2)
ON CONFLICT (provider_name, model_name) DO UPDATE 
SET is_primary = EXCLUDED.is_primary, is_active = EXCLUDED.is_active;

-- 2. SEED SAMPLE COLLEGE TENANTS
-- College A: Ahmedabad Institute of Technology
INSERT INTO colleges (id, name, slug, official_domain, contact_email, contact_phone, status, is_active)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Ahmedabad Institute of Technology',
    'ait-college',
    'aitindia.in',
    'admissions@aitindia.in',
    '+91-79-27663244',
    'APPROVED',
    TRUE
) ON CONFLICT (slug) DO NOTHING;

-- College B: RCTI College of Technology
INSERT INTO colleges (id, name, slug, official_domain, contact_email, contact_phone, status, is_active)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'RC Technical Institute',
    'rcti-college',
    'rcti.cteguj.org',
    'info@rcti.cteguj.org',
    '+91-79-27664785',
    'APPROVED',
    TRUE
) ON CONFLICT (slug) DO NOTHING;

-- 3. SEED USERS (Passwords hashed using standard bcrypt for test 'Admin@12345')
-- Super Admin
INSERT INTO users (id, email, hashed_password, full_name, role, is_verified, is_active)
VALUES (
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'superadmin@platform.com',
    '$2b$12$d7i8vi1dSvqOXDHOWv4AGOhehnvGxjrUVuRCLFkph.ysyLDV1FtmG',
    'Global System Administrator',
    'SUPER_ADMIN',
    TRUE,
    TRUE
) ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;

-- College Admin for AIT
INSERT INTO users (id, email, hashed_password, full_name, role, is_verified, is_active)
VALUES (
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'admin@aitindia.in',
    '$2b$12$d7i8vi1dSvqOXDHOWv4AGOhehnvGxjrUVuRCLFkph.ysyLDV1FtmG',
    'AIT Chief Administrator',
    'COLLEGE_ADMIN',
    TRUE,
    TRUE
) ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;

-- College Membership mapping admin to AIT
INSERT INTO college_memberships (college_id, user_id, role_in_college, is_primary)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'ADMIN',
    TRUE
) ON CONFLICT (college_id, user_id) DO NOTHING;

-- Student User
INSERT INTO users (id, email, hashed_password, full_name, role, is_verified, is_active)
VALUES (
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
    'student@gmail.com',
    '$2b$12$d7i8vi1dSvqOXDHOWv4AGOhehnvGxjrUVuRCLFkph.ysyLDV1FtmG',
    'Dharmik Vataliya',
    'STUDENT',
    TRUE,
    TRUE
) ON CONFLICT (email) DO UPDATE SET hashed_password = EXCLUDED.hashed_password;

