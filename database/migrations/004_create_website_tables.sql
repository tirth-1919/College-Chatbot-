-- ==============================================================================
-- Migration: 004_create_website_tables.sql
-- Description: Create crawler configurations, jobs, logs, and fetched pages
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. Entity: website_sources
CREATE TABLE IF NOT EXISTS website_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    base_url TEXT NOT NULL,
    allowed_subdomains TEXT,
    max_depth INTEGER NOT NULL DEFAULT 2,
    max_pages INTEGER NOT NULL DEFAULT 50,
    crawl_frequency VARCHAR(50) NOT NULL DEFAULT 'WEEKLY',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_crawled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE website_sources IS 'Target website entry points configured by College Admins for scheduled crawling';
COMMENT ON COLUMN website_sources.college_id IS 'Tenant ownership foreign key';

-- 2. Entity: crawl_jobs
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES website_sources(id) ON DELETE CASCADE,
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    status crawl_job_status NOT NULL DEFAULT 'PENDING',
    pages_discovered INTEGER NOT NULL DEFAULT 0,
    pages_crawled INTEGER NOT NULL DEFAULT 0,
    pages_failed INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE crawl_jobs IS 'Execution records for individual asynchronous web crawler tasks';

-- 3. Entity: crawl_events (also referred to as crawl_job_events)
CREATE TABLE IF NOT EXISTS crawl_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crawl_job_id UUID NOT NULL REFERENCES crawl_jobs(id) ON DELETE CASCADE,
    log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE crawl_events IS 'Granular execution logs emitted during web crawler runs for real-time monitoring';

-- 4. Entity: website_pages
CREATE TABLE IF NOT EXISTS website_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES website_sources(id) ON DELETE CASCADE,
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    content_hash VARCHAR(64) NOT NULL,
    cleaned_text TEXT NOT NULL,
    http_status INTEGER NOT NULL DEFAULT 200,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE website_pages IS 'Cleaned text and metadata extracted from individual crawled web pages';
COMMENT ON COLUMN website_pages.content_hash IS 'SHA-256 hash of page content used for change detection and deduplication';

