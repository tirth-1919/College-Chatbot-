-- ==============================================================================
-- Migration: 003_create_users_and_memberships.sql
-- Description: Create platform users and tenant membership mappings
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. Entity: users
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

COMMENT ON TABLE users IS 'Master account table for students, college administrators, and super administrators';
COMMENT ON COLUMN users.role IS 'Platform permission level: STUDENT, COLLEGE_ADMIN, or SUPER_ADMIN';
COMMENT ON COLUMN users.is_verified IS 'Email address verification state';

-- 2. Entity: college_memberships
CREATE TABLE IF NOT EXISTS college_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_in_college membership_role NOT NULL DEFAULT 'ADMIN',
    is_primary BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_college_user UNIQUE (college_id, user_id)
);

COMMENT ON TABLE college_memberships IS 'Maps users with role COLLEGE_ADMIN to their specific authorized college tenant';
COMMENT ON COLUMN college_memberships.college_id IS 'Foreign key to colleges.id; defines tenant authorization boundary';
COMMENT ON COLUMN college_memberships.role_in_college IS 'College-level role: ADMIN, EDITOR, or VIEWER';

