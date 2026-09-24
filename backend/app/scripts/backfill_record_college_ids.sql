-- Production Data Backfill: Assign college_id to Knowledge Records
-- 
-- CRITICAL: Run this SQL against production PostgreSQL BEFORE deploying
-- the tenant isolation security fixes from the 2026-09-24 audit.
--
-- Purpose: Existing knowledge_records created before the security fix
-- have college_id = NULL. This backfills them from their parent category.
--
-- Safety: Idempotent (safe to run multiple times)
-- Runtime: Fast (single UPDATE with subquery)
-- Rollback: Not needed (only fills NULL values, never overwrites)

BEGIN;

-- Verify current state
SELECT 
    'BEFORE BACKFILL' as stage,
    COUNT(*) as total_records,
    COUNT(college_id) as records_with_college_id,
    COUNT(*) - COUNT(college_id) as records_missing_college_id
FROM knowledge_records;

-- Backfill records missing college_id from their category
UPDATE knowledge_records
SET college_id = (
    SELECT college_id 
    FROM knowledge_categories
    WHERE knowledge_categories.id = knowledge_records.category_id
)
WHERE college_id IS NULL;

-- Verify results
SELECT 
    'AFTER BACKFILL' as stage,
    COUNT(*) as total_records,
    COUNT(college_id) as records_with_college_id,
    COUNT(*) - COUNT(college_id) as records_still_missing_college_id
FROM knowledge_records;

-- Flag orphaned records (records whose category doesn't exist)
SELECT 
    'ORPHANED RECORDS (no category)' as issue,
    COUNT(*) as count
FROM knowledge_records
WHERE category_id NOT IN (SELECT id FROM knowledge_categories);

-- Flag records still missing college_id (category also has NULL college_id)
SELECT 
    'RECORDS WITH NULL COLLEGE (category also NULL)' as issue,
    COUNT(*) as count
FROM knowledge_records
WHERE college_id IS NULL;

COMMIT;

-- Manual verification queries (run after backfill)
/*
-- Check distribution of records by college
SELECT 
    c.name as college_name,
    c.code as college_code,
    COUNT(kr.id) as record_count
FROM colleges c
LEFT JOIN knowledge_records kr ON kr.college_id = c.id
GROUP BY c.id, c.name, c.code
ORDER BY record_count DESC;

-- Verify no NULL college_id records remain (except orphans)
SELECT COUNT(*) as should_be_zero
FROM knowledge_records
WHERE college_id IS NULL
  AND category_id IN (SELECT id FROM knowledge_categories);
*/
