-- ==============================================================================
-- Migration: 016_analytics_support_and_multilingual.sql
-- Description: Phase 11 & Phase 12 Schema Enhancements:
--   1. Support Ticket Categories, Priorities, Assignment & Replies
--   2. In-App User Notifications System
--   3. User Language Preferences & Telemetry
--   4. Enhanced Feedback Classification
-- ==============================================================================

-- 1. Upgrade support_ticket_status type to include WAITING_FOR_USER
DO $$ 
BEGIN
    ALTER TYPE support_ticket_status ADD VALUE IF NOT EXISTS 'WAITING_FOR_USER';
EXCEPTION 
    WHEN duplicate_object THEN NULL;
END $$;

-- 2. Enhance support_tickets table
ALTER TABLE support_tickets
    ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'OTHER',
    ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'MEDIUM',
    ADD COLUMN IF NOT EXISTS assigned_to_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS resolution_notes TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 3. Create support_ticket_replies table for conversational resolution
CREATE TABLE IF NOT EXISTS support_ticket_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID NOT NULL REFERENCES support_tickets(id) ON DELETE CASCADE,
    sender_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    sender_name VARCHAR(255) NOT NULL,
    sender_role VARCHAR(50) NOT NULL, -- 'STUDENT', 'COLLEGE_ADMIN', 'SUPER_ADMIN'
    message_text TEXT NOT NULL,
    is_internal BOOLEAN NOT NULL DEFAULT FALSE, -- Internal admin notes hidden from students
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Create in_app_notifications table
CREATE TABLE IF NOT EXISTS in_app_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    college_id UUID REFERENCES colleges(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'INFO', -- 'INFO', 'SUCCESS', 'WARNING', 'ERROR'
    link VARCHAR(255),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Add user preferences and preferred language to users table
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
    ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT '{}'::jsonb;

-- 6. Enhance feedback table with category and session context
ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS session_id UUID REFERENCES chat_sessions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'ACCURACY';

-- 7. Performance & Tenant Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_support_tickets_college_status ON support_tickets(college_id, status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_user ON support_tickets(user_id);
CREATE INDEX IF NOT EXISTS idx_ticket_replies_ticket ON support_ticket_replies(ticket_id, created_at);
CREATE INDEX IF NOT EXISTS idx_in_app_notifications_user_read ON in_app_notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_feedback_college_created ON feedback(college_id, created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);

