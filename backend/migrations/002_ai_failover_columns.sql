-- ==============================================================================
-- Migration 002 — AI Provider Failover: ENUM extensions + new columns
-- Target: chat_messages table, answer_source_type ENUM
-- Apply with: psql $DATABASE_URL -f 002_ai_failover_columns.sql
--
-- IMPORTANT — PostgreSQL ENUM non-transactional constraint:
--   ALTER TYPE ... ADD VALUE is NON-TRANSACTIONAL in PostgreSQL. The new value
--   is added to the system catalogue immediately when the statement executes, but
--   it only becomes visible to other sessions — and to subsequent statements in
--   the SAME transaction — after the surrounding transaction commits.
--
--   Consequence: if you wrap this entire file inside a BEGIN/COMMIT block,
--   the ALTER TABLE statements below that reference the new ENUM values will
--   fail with "invalid input value for enum" on PostgreSQL < 14 because the
--   new values have not yet been committed. This file must therefore be run
--   STANDALONE (outside any explicit transaction block), which causes each
--   ALTER TYPE statement to auto-commit before the next statement runs.
--
--   Safe execution:
--     psql $DATABASE_URL -f 002_ai_failover_columns.sql
--   Unsafe (do NOT do this):
--     psql $DATABASE_URL -c "BEGIN; \i 002_ai_failover_columns.sql; COMMIT;"
--
--   This file is idempotent: IF NOT EXISTS guards on both ENUM values and
--   columns allow it to be safely re-run after a partial failure.
-- ==============================================================================

-- Step 1: Add new ENUM values (non-transactional; each auto-commits standalone)
-- IF NOT EXISTS prevents duplicate-value errors on re-run (supported since PG 9.3).
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED';

-- Step 2: Add new columns to chat_messages
-- ADD COLUMN IF NOT EXISTS is idempotent (supported since PostgreSQL 9.6).
-- All new columns are nullable or carry a server-side default so existing rows
-- are unaffected and no table rewrite occurs on a live database.
ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS answer_mode           VARCHAR(30)  NULL,
    ADD COLUMN IF NOT EXISTS actual_provider       VARCHAR(50)  NULL,
    ADD COLUMN IF NOT EXISTS actual_model          VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS fallback_reason       TEXT         NULL,
    ADD COLUMN IF NOT EXISTS attempt_count         INTEGER      NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS request_duration_ms   INTEGER      NULL;

-- ==============================================================================
-- Verification queries (read-only — uncomment and run after applying migration):
--
-- SELECT enum_range(NULL::answer_source_type);
--   Expected result includes all eight values:
--   {OFFICIAL_WEBSITE,ADMIN_VERIFIED,GEMINI_UNVERIFIED,SECONDARY_AI_FALLBACK,
--    NO_RELIABLE_INFORMATION,AI_GUIDANCE,OPENAI_UNVERIFIED,XKIRO_UNVERIFIED}
--
-- SELECT column_name, data_type, is_nullable, column_default
--   FROM information_schema.columns
--   WHERE table_name = 'chat_messages'
--   ORDER BY ordinal_position;
--   Expected: six new rows for answer_mode, actual_provider, actual_model,
--             fallback_reason, attempt_count (default 0), request_duration_ms.
-- ==============================================================================
