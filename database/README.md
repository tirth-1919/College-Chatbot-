# Database Architecture & Supabase Implementation Guide

Welcome to the **Database Implementation Guide** for the **AI FAQ College Chat Bot**. This document explains how the data layer is architected, how to apply migrations to Supabase PostgreSQL, and how multi-tenancy and vector search work.

---

## 1. Database Architecture & Tenancy Model

The database is built on **Supabase Managed PostgreSQL (v15+)** with the **`pgvector`** extension.

### Core Multi-Tenancy Invariant
The platform is a multi-tenant SaaS application where multiple colleges (e.g., AIT College, RCTI College) share a single database cluster. 
Data isolation is strictly enforced:
- Every college-owned record contains a mandatory `college_id UUID` foreign key pointing to `colleges.id`.
- Foreign keys use `ON DELETE CASCADE` so deleting a tenant automatically removes its documents, chunks, and logs.
- Dedicated indexes on `(college_id, ...)` prevent sequential table scans and guarantee sub-10ms query times.
- PostgreSQL **Row-Level Security (RLS)** policies prevent any query from touching unauthorized tenant data.

---

## 2. Technology Stack Explanation

| Technology | Role in System | Why Chosen |
| :--- | :--- | :--- |
| **Supabase PostgreSQL** | Primary relational datastore | Reliable ACID compliance, JSONB support, built-in Auth & Storage. |
| **pgvector** | Vector similarity engine | Stores 768-dim embeddings directly alongside text; enables cosine similarity SQL queries. |
| **Supabase Storage** | Private object store | Encrypted bucket for original PDF files, accessed exclusively via signed URLs. |
| **SQLAlchemy 2.0** | Python ORM | High-performance async ORM using `Mapped` and `mapped_column` type safety. |
| **HNSW Indexing** | Vector index algorithm | Hierarchical Navigable Small World index for millisecond vector nearest-neighbor search. |

---

## 3. Entity Catalog (All 20 Tables)

### Group 1: Tenant & Core Identity
1. `colleges`: The root tenant table. Holds legal names, unique URL slugs, domains, and approval status.
2. `users`: Master user accounts for students, college administrators, and platform super administrators.
3. `college_memberships`: Enforces which College Admins have authorization to manage which college tenant.

### Group 2: Website Crawler Subsystem
4. `website_sources`: Allowed URLs and crawl parameters (depth, page limit) configured by College Admins.
5. `crawl_jobs`: Execution tracking for asynchronous background crawling tasks.
6. `crawl_events`: Granular execution logs emitted during crawling for live UI progress monitoring.
7. `website_pages`: Cleaned text, titles, HTTP status, and SHA-256 deduplication hashes of crawled pages.

### Group 3: Document & OCR Subsystem
8. `documents`: Metadata, checksums, and private storage references for uploaded PDF files.
9. `document_pages`: Page-by-page extracted text with boolean flags for scanned pages and OCR application.
10. `document_paragraphs`: Fine-grained paragraph splits and visual bounding boxes.

### Group 4: Knowledge Base & Human Review
11. `extracted_facts`: Structured atomic key-value facts (tuition fee, admission cutoff date, hostel capacity).
12. `knowledge_chunks`: The primary semantic search unit holding text chunks and 768-dimensional vector embeddings.
13. `knowledge_reviews`: Immutable review log of human admin actions (approve, edit, reject, publish).

### Group 5: Chat & Student Support
14. `chat_sessions`: Conversational threads scoped to a specific college tenant.
15. `chat_messages`: Turn-by-turn prompts, answers, verification badges, model used, and source citations.
16. `feedback`: Student thumbs up/down ratings and comments on answer accuracy.
17. `support_tickets`: Direct inquiries escalated to college staff when verified AI answers are unavailable.

### Group 6: Platform Governance & Audit
18. `ai_provider_configs`: Super Admin configuration of Google Gemini, OpenAI, and Groq settings.
19. `ai_provider_events`: Telemetry tracking latency, token consumption, timeouts, and fallback failovers.
20. `audit_logs`: Immutable security audit stream recording all privileged administrative operations.

---

## 4. Table Relationships & Cardinality

```mermaid
erDiagram
    colleges ||--o{ users : "registers"
    colleges ||--o{ college_memberships : "has"
    users ||--o{ college_memberships : "holds"
    
    colleges ||--o{ website_sources : "configures"
    website_sources ||--o{ crawl_jobs : "spawns"
    crawl_jobs ||--o{ crawl_events : "logs"
    website_sources ||--o{ website_pages : "indexes"
    
    colleges ||--o{ documents : "owns"
    documents ||--o{ document_pages : "contains"
    document_pages ||--o{ document_paragraphs : "contains"
    
    colleges ||--o{ extracted_facts : "maintains"
    colleges ||--o{ knowledge_chunks : "owns"
    knowledge_chunks ||--o{ knowledge_reviews : "audited_by"
    users ||--o{ knowledge_reviews : "performs"
    
    colleges ||--o{ chat_sessions : "scopes"
    users ||--o{ chat_sessions : "participates"
    chat_sessions ||--o{ chat_messages : "records"
    
    colleges ||--o{ feedback : "receives"
    chat_messages ||--o{ feedback : "assesses"
    colleges ||--o{ support_tickets : "receives"
    users ||--o{ support_tickets : "submits"
    
    ai_provider_configs ||--o{ ai_provider_events : "telemetry"
    users ||--o{ audit_logs : "triggers"
    colleges ||--o{ audit_logs : "scoped_to"
```

---

## 5. Migration Execution Instructions

### Option A: Direct Execution via Supabase SQL Editor (Recommended for Fast Setup)
1. Open your Supabase Project Dashboard at [supabase.com](https://supabase.com/).
2. In the left sidebar, click **SQL Editor**.
3. Click **New Query**.
4. Open the file `backend/migrations/001_initial_schema.sql` (or run each numbered file in `database/migrations/` sequentially from `001` to `011`).
5. Paste the SQL into the editor and click **Run**.
6. All 20 tables, custom ENUMs, pgvector HNSW indexes, and RLS policies are created in seconds.

### Option B: Command-Line Migration via psql
If you have PostgreSQL client tools (`psql`) installed:
```bash
# Connect to your Supabase PostgreSQL database
psql "postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Execute migrations in sequence
\i database/migrations/001_extensions.sql
\i database/migrations/002_create_colleges.sql
\i database/migrations/003_create_users_and_memberships.sql
\i database/migrations/004_create_website_tables.sql
\i database/migrations/005_create_document_tables.sql
\i database/migrations/006_create_knowledge_tables.sql
\i database/migrations/007_create_chat_tables.sql
\i database/migrations/008_create_ai_and_audit_tables.sql
\i database/migrations/009_create_feedback_and_support.sql
\i database/migrations/010_create_indexes.sql
\i database/migrations/011_prepare_rls.sql

# Optional: Load initial development seed data
\i database/seed/development_seed.sql
```

---

## 6. Supabase Cloud Configuration Guide

### 6.1. Enabling Extensions
In the Supabase Dashboard:
1. Navigate to **Database** -> **Extensions**.
2. Search for **vector** and toggle it **ON**.
3. Search for **uuid-ossp** and toggle it **ON**.
*(Note: Migration `001_extensions.sql` executes this automatically via SQL).*

### 6.2. Creating Private Storage Bucket for PDFs
1. In the Supabase Dashboard, click **Storage** in the left sidebar.
2. Click **New Bucket**.
3. Name the bucket: `college-documents`.
4. **CRITICAL**: Keep **Public Bucket** toggled **OFF** (Private).
5. Click **Save**.

### 6.3. Storage Path Convention
Uploaded files must strictly follow this hierarchical structure:
```
college-documents/
└── colleges/
    └── {college_id}/
        └── documents/
            └── {document_id}/
                └── original.pdf
```
This guarantees that storage paths mirror database foreign keys.

---

## 7. pgvector Configuration & Cosine Similarity Queries

### Vector Dimension Decision
- We use **768 dimensions** matching Google Gemini's **`text-embedding-004`** model.
- If switching to OpenAI's `text-embedding-3-small`, the dimension is 1536. This is controlled dynamically via `settings.EMBEDDING_DIMENSION`.

### Example Vector Cosine Similarity Search Query
```sql
SELECT 
    id,
    college_id,
    source_type,
    source_url,
    page_number,
    chunk_text,
    1 - (embedding <=> :user_query_vector) AS cosine_similarity
FROM knowledge_chunks
WHERE college_id = :selected_college_id
  AND status = 'PUBLISHED'
  AND is_active = TRUE
ORDER BY embedding <=> :user_query_vector ASC
LIMIT 5;
```

---

## 8. Environment Variables Setup

Copy `backend/.env.example` to `backend/.env` and populate your credentials:

```bash
cp backend/.env.example backend/.env
```

Key connection parameters:
```env
# Supabase Transaction Pooler URI
DATABASE_URL="postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"

# Supabase API Credentials
SUPABASE_URL="https://[PROJECT-REF].supabase.co"
SUPABASE_SERVICE_ROLE_KEY="[YOUR-SERVICE-ROLE-KEY]"
SUPABASE_STORAGE_BUCKET_DOCS="college-documents"

# Google Gemini API Key
GEMINI_API_KEY="[YOUR-GEMINI-API-KEY]"
```

---

## 9. Known Limitations & Approval Decisions

1. **Embedding Dimension Selection**: Set to 768 (Gemini `text-embedding-004`). If you prefer 1536 (OpenAI), notify me before applying migrations.
2. **PostgreSQL RLS in Development**: RLS is prepared in `011_prepare_rls.sql`. Full active enforcement will be tested alongside JWT authentication in Phase 2.

