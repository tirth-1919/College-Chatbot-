-- ==============================================================================
-- Migration: 012_college_onboarding_and_registration.sql
-- Description: Phase 6 - College Onboarding, Registration Workflow, Admin Invitations,
--              Onboarding Progress Tracking, and Compliance Notification Logs
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. ENUMS FOR REGISTRATION WORKFLOW & INVITATIONS
DO $$ BEGIN
    CREATE TYPE registration_status AS ENUM (
        'PENDING',
        'UNDER_REVIEW',
        'APPROVED',
        'REJECTED',
        'ADDITIONAL_INFORMATION_REQUIRED'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE invitation_status AS ENUM (
        'PENDING',
        'ACCEPTED',
        'EXPIRED',
        'REVOKED'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_delivery_status AS ENUM (
        'QUEUED',
        'SENT',
        'SIMULATED',
        'FAILED'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- 2. ENTITY: college_registrations
-- Stores incoming institutional registration applications prior to approval
CREATE TABLE IF NOT EXISTS college_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id) ON DELETE SET NULL,
    college_name VARCHAR(255) NOT NULL,
    college_code VARCHAR(50),
    slug VARCHAR(100) UNIQUE NOT NULL,
    official_domain VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(50),
    contact_person_name VARCHAR(255) NOT NULL,
    contact_person_email VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    description TEXT,
    accreditation_details TEXT,
    website_url VARCHAR(255),
    logo_url TEXT,
    supporting_documents JSONB NOT NULL DEFAULT '[]'::jsonb,
    status registration_status NOT NULL DEFAULT 'PENDING',
    tracking_code VARCHAR(50) UNIQUE NOT NULL,
    
    -- Designee Administrator Credentials (for auto-provisioning upon approval)
    initial_admin_name VARCHAR(255),
    initial_admin_email VARCHAR(255),
    initial_admin_password_hash VARCHAR(255),
    initial_admin_designation VARCHAR(100) DEFAULT 'College Administrator',

    -- Review & Governance Metadata
    submitted_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by_admin_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_comments TEXT,
    additional_info_requested TEXT,
    additional_info_submitted TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE college_registrations IS 'Institutional registration queue awaiting Super Admin verification and approval';
COMMENT ON COLUMN college_registrations.tracking_code IS 'Public tracking token (e.g. APP-AIT-7A9B) used by colleges to track onboarding status';
COMMENT ON COLUMN college_registrations.status IS 'Lifecycle state: PENDING, UNDER_REVIEW, APPROVED, REJECTED, ADDITIONAL_INFORMATION_REQUIRED';


-- 3. ENTITY: registration_reviews
-- Immutable history of reviewer decisions, remarks, and state transitions
CREATE TABLE IF NOT EXISTS registration_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID NOT NULL REFERENCES college_registrations(id) ON DELETE CASCADE,
    reviewer_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    previous_status registration_status NOT NULL,
    new_status registration_status NOT NULL,
    comments TEXT,
    action_type VARCHAR(100) NOT NULL, -- 'SUBMITTED', 'REQUEST_INFO', 'INFO_SUBMITTED', 'APPROVED', 'REJECTED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE registration_reviews IS 'Audit trail of administrative reviews and decisions on college registrations';


-- 4. ENTITY: college_admin_invitations
-- Allows Super Admins or Primary College Admins to securely invite institutional administrators
CREATE TABLE IF NOT EXISTS college_admin_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    invited_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role_in_college membership_role NOT NULL DEFAULT 'ADMIN',
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    status invitation_status NOT NULL DEFAULT 'PENDING',
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE college_admin_invitations IS 'Token-based invitations for college administrator onboarding';
COMMENT ON COLUMN college_admin_invitations.invitation_token IS 'Cryptographically secure one-time invite token';


-- 5. ENTITY: college_onboarding_progress
-- Tracks multi-step onboarding wizard progression per approved college tenant
CREATE TABLE IF NOT EXISTS college_onboarding_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID UNIQUE NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    current_step INTEGER NOT NULL DEFAULT 1, -- 1: Welcome, 2: Profile, 3: Website, 4: Documents, 5: Review Intro, 6: Completed
    is_approved BOOLEAN NOT NULL DEFAULT TRUE,
    admin_assigned BOOLEAN NOT NULL DEFAULT TRUE,
    profile_completed BOOLEAN NOT NULL DEFAULT FALSE,
    website_configured BOOLEAN NOT NULL DEFAULT FALSE,
    documents_uploaded BOOLEAN NOT NULL DEFAULT FALSE,
    knowledge_ready BOOLEAN NOT NULL DEFAULT FALSE,
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    step_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE college_onboarding_progress IS 'Step-by-step onboarding progress tracking for college administrators';


-- 6. ENTITY: notification_logs
-- Multi-channel communication audit log for onboarding and governance events
CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id) ON DELETE SET NULL,
    recipient_email VARCHAR(255) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    delivery_status notification_delivery_status NOT NULL DEFAULT 'QUEUED',
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE notification_logs IS 'Platform notifications and email delivery tracking log';


-- 7. PERFORMANCE INDEXES
CREATE INDEX IF NOT EXISTS idx_registrations_status ON college_registrations(status);
CREATE INDEX IF NOT EXISTS idx_registrations_slug ON college_registrations(slug);
CREATE INDEX IF NOT EXISTS idx_registrations_domain ON college_registrations(official_domain);
CREATE INDEX IF NOT EXISTS idx_registrations_tracking ON college_registrations(tracking_code);
CREATE INDEX IF NOT EXISTS idx_registrations_admin_email ON college_registrations(initial_admin_email);

CREATE INDEX IF NOT EXISTS idx_reviews_reg_id ON registration_reviews(registration_id);
CREATE INDEX IF NOT EXISTS idx_invitations_college ON college_admin_invitations(college_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON college_admin_invitations(invitation_token);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON college_admin_invitations(status);

CREATE INDEX IF NOT EXISTS idx_onboarding_college ON college_onboarding_progress(college_id);
CREATE INDEX IF NOT EXISTS idx_notifications_college ON notification_logs(college_id);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notification_logs(recipient_email);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notification_logs(event_type);


-- 8. ROW LEVEL SECURITY (RLS) POLICIES
ALTER TABLE college_registrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE registration_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE college_admin_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE college_onboarding_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_logs ENABLE ROW LEVEL SECURITY;

-- Super Admins can manage all registrations and reviews
DROP POLICY IF EXISTS p_registrations_super_admin ON college_registrations;
CREATE POLICY p_registrations_super_admin ON college_registrations
    FOR ALL
    USING (is_platform_super_admin());

DROP POLICY IF EXISTS p_reviews_super_admin ON registration_reviews;
CREATE POLICY p_reviews_super_admin ON registration_reviews
    FOR ALL
    USING (is_platform_super_admin());

-- College Admin access to onboarding progress (strictly scoped to assigned college)
DROP POLICY IF EXISTS p_onboarding_tenant_isolation ON college_onboarding_progress;
CREATE POLICY p_onboarding_tenant_isolation ON college_onboarding_progress
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

-- Invitations accessible by Super Admin or Primary College Admin for their college
DROP POLICY IF EXISTS p_invitations_tenant_isolation ON college_admin_invitations;
CREATE POLICY p_invitations_tenant_isolation ON college_admin_invitations
    FOR ALL
    USING (college_id = current_app_tenant() OR is_platform_super_admin());

