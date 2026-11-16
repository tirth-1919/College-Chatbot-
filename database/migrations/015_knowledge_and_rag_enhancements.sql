-- ==============================================================================
-- Migration: 015_knowledge_and_rag_enhancements.sql
-- Description: Knowledge Processing, Category Classification, and RAG Enhancements
-- Phase: 9 & 10
-- ==============================================================================

-- 1. Enhance knowledge_chunks with semantic category, heading, hash, and metadata
ALTER TABLE knowledge_chunks 
    ADD COLUMN IF NOT EXISTS category VARCHAR(100) NOT NULL DEFAULT 'OTHER',
    ADD COLUMN IF NOT EXISTS heading VARCHAR(255),
    ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
    ADD COLUMN IF NOT EXISTS chunk_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 2. Performance & Retrieval Indexes
CREATE INDEX IF NOT EXISTS idx_chunks_college_category ON knowledge_chunks(college_id, category);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON knowledge_chunks(college_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_chunks_college_status ON knowledge_chunks(college_id, status, is_active);

-- 3. Comments
COMMENT ON COLUMN knowledge_chunks.category IS 'One of 15 institutional categories: ADMISSIONS, FEES, COURSES, SCHOLARSHIPS, EXAMINATIONS, RESULTS, ACADEMIC_CALENDAR, FACILITIES, HOSTEL, LIBRARY, PLACEMENT, CONTACT, RULES, DEPARTMENTS, OTHER';
COMMENT ON COLUMN knowledge_chunks.heading IS 'Section heading or title hierarchy associated with this chunk';
COMMENT ON COLUMN knowledge_chunks.content_hash IS 'SHA256 hash of normalized chunk text for tenant deduplication';
COMMENT ON COLUMN knowledge_chunks.chunk_metadata IS 'Additional metadata such as token count, source title, crawl timestamp, or OCR confidence';

