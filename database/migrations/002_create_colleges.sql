-- ==============================================================================
-- Migration: 002_create_colleges.sql
-- Description: Create the root tenant entity (colleges table)
-- Author: Senior Database Architect
-- ==============================================================================

CREATE TABLE IF NOT EXISTS colleges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    official_domain VARCHAR(255) NOT NULL,
    logo_url TEXT,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    status college_status NOT NULL DEFAULT 'PENDING',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Comments describing purpose and columns
COMMENT ON TABLE colleges IS 'Root tenant entity representing individual colleges and educational institutions';
COMMENT ON COLUMN colleges.id IS 'Unique identifier for the college tenant (UUID v4)';
COMMENT ON COLUMN colleges.name IS 'Full legal or official name of the college';
COMMENT ON COLUMN colleges.slug IS 'URL-safe unique identifier for college-specific routing';
COMMENT ON COLUMN colleges.official_domain IS 'Verified domain used for website crawling and email validation';
COMMENT ON COLUMN colleges.status IS 'Administrative approval state: PENDING, APPROVED, SUSPENDED, REJECTED';
COMMENT ON COLUMN colleges.is_active IS 'Global kill-switch for tenant accessibility';

