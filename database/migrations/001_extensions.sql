-- ==============================================================================
-- Migration: 001_extensions.sql
-- Description: Enable required PostgreSQL extensions and create common ENUM types
-- Author: Senior Database Architect
-- ==============================================================================

-- 1. EXTENSIONS
-- Required for generating UUID primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Required for cryptographic hashing and token generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Required for storing and querying 768-dimensional vector embeddings (Gemini)
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. ENUM TYPES
-- College onboarding and operational status
DO $$ BEGIN
    CREATE TYPE college_status AS ENUM ('PENDING', 'APPROVED', 'SUSPENDED', 'REJECTED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Platform user roles
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('STUDENT', 'COLLEGE_ADMIN', 'SUPER_ADMIN');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Role of an administrator within a specific college
DO $$ BEGIN
    CREATE TYPE membership_role AS ENUM ('ADMIN', 'EDITOR', 'VIEWER');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Background web crawling execution states
DO $$ BEGIN
    CREATE TYPE crawl_job_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- PDF document processing pipeline states
DO $$ BEGIN
    CREATE TYPE document_status AS ENUM ('PROCESSING', 'PENDING_REVIEW', 'COMPLETED', 'FAILED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Knowledge chunk review and publication lifecycle states
DO $$ BEGIN
    CREATE TYPE knowledge_status AS ENUM (
        'PROCESSING',
        'PENDING_REVIEW',
        'APPROVED',
        'PUBLISHED',
        'REJECTED',
        'STALE',
        'SUPERSEDED',
        'FAILED'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Chatbot answer source priority hierarchy
DO $$ BEGIN
    CREATE TYPE answer_source_type AS ENUM (
        'OFFICIAL_WEBSITE',
        'ADMIN_VERIFIED',
        'GEMINI_UNVERIFIED',
        'SECONDARY_AI_FALLBACK',
        'NO_RELIABLE_INFORMATION'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Support ticket status
DO $$ BEGIN
    CREATE TYPE support_ticket_status AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

