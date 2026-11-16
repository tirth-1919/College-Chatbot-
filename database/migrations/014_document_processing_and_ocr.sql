-- ==============================================================================
-- Migration: 014_document_processing_and_ocr.sql
-- Description: Phase 8 PDF Upload, Document Processing & OCR Engine Enhancements
-- Author: Senior Database Architect & Document Processing Engineer
-- ==============================================================================

-- 1. Extend document_status ENUM with all Phase 8 pipeline states
DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'UPLOADED';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'VALIDATING';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'QUEUED';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'OCR_PROCESSING';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'EXTRACTED';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'REPROCESSING';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$
BEGIN
    ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'DELETED';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Add telemetry and metadata columns to documents table
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS category VARCHAR(50) DEFAULT 'GENERAL',
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS failure_reason TEXT,
    ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(50) DEFAULT 'PYMUPDF',
    ADD COLUMN IF NOT EXISTS ocr_applied BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 3. Add telemetry, tabular data, and college scope to document_pages
ALTER TABLE document_pages
    ADD COLUMN IF NOT EXISTS college_id UUID REFERENCES colleges(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS ocr_confidence NUMERIC(5,2),
    ADD COLUMN IF NOT EXISTS extraction_method VARCHAR(50) DEFAULT 'PYMUPDF',
    ADD COLUMN IF NOT EXISTS tables_markdown JSONB DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS has_tables BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS word_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS char_count INTEGER DEFAULT 0;

-- 4. High-performance multi-tenant indexes
CREATE INDEX IF NOT EXISTS idx_documents_college_checksum ON documents(college_id, checksum_sha256);
CREATE INDEX IF NOT EXISTS idx_documents_college_status ON documents(college_id, processing_status);
CREATE INDEX IF NOT EXISTS idx_document_pages_college ON document_pages(college_id);
CREATE INDEX IF NOT EXISTS idx_document_pages_doc_num ON document_pages(document_id, page_number);

COMMENT ON COLUMN documents.checksum_sha256 IS 'SHA-256 binary hash used for institutional duplicate detection';
COMMENT ON COLUMN documents.extraction_method IS 'Primary extraction library used (PYMUPDF, PDFPLUMBER, TESSERACT_OCR)';
COMMENT ON COLUMN document_pages.ocr_confidence IS 'Average OCR character recognition confidence percentage (0-100)';
COMMENT ON COLUMN document_pages.tables_markdown IS 'Parsed tabular contents serialized as Markdown strings';

