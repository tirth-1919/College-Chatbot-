-- ==============================================================================
-- Migration: 013_crawler_engine.sql
-- Description: Phase 7 Official College Website Crawler Engine Enhancements
-- Author: Senior Database Architect & Web Crawling Engineer
-- ==============================================================================

-- 1. Ensure crawl_job_status ENUM includes RUNNING and PAUSED
DO $$
BEGIN
    ALTER TYPE crawl_job_status ADD VALUE IF NOT EXISTS 'RUNNING';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE crawl_job_status ADD VALUE IF NOT EXISTS 'PAUSED';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Add crawl_job_id and metadata columns to website_pages
ALTER TABLE website_pages
    ADD COLUMN IF NOT EXISTS crawl_job_id UUID REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS meta_description TEXT,
    ADD COLUMN IF NOT EXISTS content_length INTEGER DEFAULT 0;

-- 3. Add source and job indexes for high-throughput crawler lookups
CREATE INDEX IF NOT EXISTS idx_website_pages_job ON website_pages(crawl_job_id);
CREATE INDEX IF NOT EXISTS idx_website_pages_college_hash ON website_pages(college_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_website_pages_college_url ON website_pages(college_id, url);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source ON crawl_jobs(source_id);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_college_status ON crawl_jobs(college_id, status);
CREATE INDEX IF NOT EXISTS idx_crawl_events_job ON crawl_events(crawl_job_id);

COMMENT ON COLUMN website_pages.crawl_job_id IS 'FK to the specific crawl job execution that fetched or updated this page';
COMMENT ON COLUMN website_pages.meta_description IS 'Extracted HTML meta description tag';
COMMENT ON COLUMN website_pages.content_length IS 'Character count of cleaned extracted text content';

