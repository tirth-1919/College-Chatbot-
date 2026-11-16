-- ==============================================================================
-- WARNING — DOWNGRADE SCRIPT FOR MIGRATION 002
-- This script reverses the column additions from 002_ai_failover_columns.sql.
-- It does NOT reverse the ENUM value additions (see note below).
--
-- Apply with: psql $DATABASE_URL -f 002_ai_failover_columns_down.sql
-- ==============================================================================

-- Step 1: Remove the six new columns from chat_messages.
-- DROP COLUMN IF EXISTS is idempotent and safe to re-run.
-- Data in these columns is permanently deleted — back up first if needed.
ALTER TABLE chat_messages
    DROP COLUMN IF EXISTS answer_mode,
    DROP COLUMN IF EXISTS actual_provider,
    DROP COLUMN IF EXISTS actual_model,
    DROP COLUMN IF EXISTS fallback_reason,
    DROP COLUMN IF EXISTS attempt_count,
    DROP COLUMN IF EXISTS request_duration_ms;

-- ==============================================================================
-- ENUM VALUE REMOVAL IS A NO-OP
--
-- The three ENUM values added by migration 002 (AI_GUIDANCE, OPENAI_UNVERIFIED,
-- XKIRO_UNVERIFIED) are intentionally NOT removed by this downgrade script.
--
-- PostgreSQL does not provide ALTER TYPE ... DROP VALUE. Removing ENUM values
-- requires dropping and recreating the entire type, which forces a full table
-- rewrite of every table that references it. This is a destructive operation
-- that risks data loss if any existing row contains a value being removed.
--
-- The three values are harmless if unused: application code continues to map
-- providers to the original five values via safe-proxy logic (rag_service.py)
-- as long as AI_NEW_ENUM_ENABLED remains False.
--
-- If you must remove these values (e.g. to strictly restore the original type),
-- follow this manual procedure ONLY after confirming no rows contain the values:
--
--   1. Verify no rows use the new values:
--      SELECT COUNT(*) FROM chat_messages
--        WHERE answer_source_type IN ('AI_GUIDANCE','OPENAI_UNVERIFIED','XKIRO_UNVERIFIED');
--      -- Must return 0 before proceeding.
--
--   2. Convert the column to VARCHAR temporarily:
--      ALTER TABLE chat_messages
--        ALTER COLUMN answer_source_type TYPE VARCHAR(50);
--
--   3. Drop and recreate the ENUM with only the original five values:
--      DROP TYPE answer_source_type;
--      CREATE TYPE answer_source_type AS ENUM (
--          'OFFICIAL_WEBSITE', 'ADMIN_VERIFIED', 'GEMINI_UNVERIFIED',
--          'SECONDARY_AI_FALLBACK', 'NO_RELIABLE_INFORMATION'
--      );
--
--   4. Restore the column type (will fail if any row holds a removed value):
--      ALTER TABLE chat_messages
--        ALTER COLUMN answer_source_type TYPE answer_source_type
--        USING answer_source_type::answer_source_type;
--
--   Steps 2-4 require an exclusive table lock and will block concurrent reads
--   and writes for the duration of the operation. Plan for a maintenance window.
-- ==============================================================================
