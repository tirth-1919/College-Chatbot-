-- ==============================================================================
-- Migration: 023_upgrade_college_profile_metadata.sql
-- Description: Upgrade College Profile & Institutional Metadata
--              Adds comprehensive metadata fields for institutional identity,
--              address & geolocation, official departmental contacts,
--              recognition & accreditation, leadership, social links,
--              branding assets, and draft profile state.
-- Safety: Non-destructive, additive DDL with IF NOT EXISTS checks.
-- ==============================================================================

BEGIN;

-- 1. Identity & Institutional Classification
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS short_name VARCHAR(50);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS cover_image_url TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS institution_type VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS established_year INTEGER;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS website_url VARCHAR(255);

-- 2. Address & Geolocation
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS district VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'India';
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS maps_url TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;

-- 3. Departmental & Official Contacts
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS admission_email VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS examination_email VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS placement_email VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS admission_helpline VARCHAR(50);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(50);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS working_hours VARCHAR(150);

-- 4. Recognition & Accreditation
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS affiliated_university VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS recognized_by VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS aicte_approval VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS ugc_recognition VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS naac_grade VARCHAR(50);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS nba_accreditation VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS accreditation_validity VARCHAR(100);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS approval_document_url TEXT;

-- 5. About Institution & Leadership
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS short_description VARCHAR(500);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS about_text TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS vision TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS mission TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS leader_name VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS leader_designation VARCHAR(100);

-- 6. Social Media
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS linkedin_url VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS instagram_url VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS facebook_url VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS youtube_url VARCHAR(255);
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS twitter_url VARCHAR(255);

-- 7. Branding & Theming
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS favicon_url TEXT;
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS primary_brand_color VARCHAR(20) DEFAULT '#10B981';
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS secondary_brand_color VARCHAR(20) DEFAULT '#6366F1';

-- 8. Draft Profile State (Unpublished changes buffer)
ALTER TABLE colleges ADD COLUMN IF NOT EXISTS draft_profile JSONB DEFAULT NULL;

-- Helpful comments for data catalog
COMMENT ON COLUMN colleges.short_name IS 'Short name or official abbreviation (e.g. AIT, IITB)';
COMMENT ON COLUMN colleges.cover_image_url IS 'Wide banner/cover image URL for the college';
COMMENT ON COLUMN colleges.institution_type IS 'Institutional classification (e.g. Autonomous College, Central University)';
COMMENT ON COLUMN colleges.established_year IS 'Year the institution was founded';
COMMENT ON COLUMN colleges.website_url IS 'Official campus portal or website link';
COMMENT ON COLUMN colleges.draft_profile IS 'Buffered draft changes awaiting publication by College Administrator';

COMMIT;
