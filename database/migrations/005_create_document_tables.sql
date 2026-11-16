-- ==============================================================================
-- Migration: 005_create_document_tables.sql
-- Description: Create document storage metadata, pages, and paragraph entities
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. Entity: documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID NOT NULL REFERENCES colleges(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
    file_size_bytes BIGINT NOT NULL,
    total_pages INTEGER NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(64) NOT NULL,
    processing_status document_status NOT NULL DEFAULT 'PROCESSING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE documents IS 'Tracks metadata for PDF documents uploaded by administrators into private Supabase Storage';
COMMENT ON COLUMN documents.storage_path IS 'Relative path in private storage bucket: colleges/{college_id}/documents/{document_id}/original.pdf';
COMMENT ON COLUMN documents.checksum_sha256 IS 'Cryptographic checksum to detect identical document uploads';

-- 2. Entity: document_pages
CREATE TABLE IF NOT EXISTS document_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    extracted_text TEXT NOT NULL,
    is_scanned BOOLEAN NOT NULL DEFAULT FALSE,
    ocr_applied BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_document_page UNIQUE (document_id, page_number)
);

COMMENT ON TABLE document_pages IS 'Stores page-by-page extracted text and OCR flags for uploaded documents';

-- 3. Entity: document_paragraphs
CREATE TABLE IF NOT EXISTS document_paragraphs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES document_pages(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    paragraph_index INTEGER NOT NULL,
    paragraph_text TEXT NOT NULL,
    bounding_box JSONB
);

COMMENT ON TABLE document_paragraphs IS 'Deconstructs document pages into fine-grained paragraphs and spatial bounding boxes';

