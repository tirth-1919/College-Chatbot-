# Phase 9 & Phase 10: Knowledge Processing, Verification, Publishing & RAG Answer Generation

## Executive Summary

Phase 9 (**Knowledge Processing, Verification & Publishing Workflow**) and Phase 10 (**RAG-Based AI Answer Generation**) establish the zero-hallucination knowledge core and student conversation engine for the **CampusAI Multi-Tenant College Chatbot Platform**.

---

## 1. Architecture Overview

```mermaid
flowchart TD
    subgraph Sources["1. Multi-Source Ingestion (Phase 7 & 8)"]
        W[Crawled Website Pages]
        D[Uploaded PDF / OCR Pages]
        F[Admin Structured Facts]
        Q[Institutional FAQs]
    end

    subgraph Pipeline["2. Knowledge Processing Pipeline (Phase 9)"]
        N[Text Normalizer: Tables, Markdown, Clean Boilerplate]
        C[15-Category Classifier: Admissions, Fees, Courses, etc.]
        K[Heading-Aware Chunker: 800 chars, Overlap 100]
        H[Deduplication: SHA256 Content Hash]
        E[Configured Gemini embedding model: 768 dimensions]
    end

    subgraph Review["3. Human-in-the-Loop Review State Machine"]
        S1[PENDING_REVIEW] -->|Approve| S2[APPROVED]
        S1 -->|Reject| S3[REJECTED]
        S2 -->|Publish| S4[PUBLISHED (Live Vector Search)]
        S4 -->|Unpublish| S2
    end

    subgraph RAG["4. RAG Retrieval & AI Generation (Phase 10)"]
        Qry[Student Question]
        Sec[Prompt Injection & Jailbreak Guard]
        V[pgvector Cosine Similarity Search: Tenant-Isolated]
        TopK[Top-K Re-ranking & Relevance Threshold]
        LLM[Google Gemini 1.5 Flash / Secondary Fallback]
        SSE[Server-Sent Events Streaming & Grounded Citations]
    end

    Sources --> N --> C --> K --> H --> E --> S1
    S4 -.-> V
    Qry --> Sec --> V --> TopK --> LLM --> SSE
```

---

## 2. Implemented Components

### A. Database Enhancements (`database/migrations/015_knowledge_and_rag_enhancements.sql`)
- **`knowledge_chunks` columns added**:
  - `category VARCHAR(100) DEFAULT 'OTHER'`: Standardized academic topic taxonomy.
  - `heading VARCHAR(255)`: Section title / header hierarchy.
  - `content_hash VARCHAR(64)`: SHA256 digest for tenant-level deduplication.
  - `chunk_metadata JSONB`: Token telemetry, crawl job reference, OCR metadata.
  - `updated_at TIMESTAMPTZ`.
- **Indexes**:
  - `idx_chunks_college_category` on `(college_id, category)`.
  - `idx_chunks_content_hash` on `(college_id, content_hash)`.
  - `idx_chunks_college_status` on `(college_id, status, is_active)`.

### B. Core Backend Services (`backend/app/services/`)
1. [text_normalizer.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/text_normalizer.py)
   - Scrubs web chrome (nav bars, headers, footers, copyright, cookie disclaimers).
   - Preserves Markdown tables (`| ... |`) and heading hierarchy (`#`, `##`, `###`).
   - Unifies curly quotes, unicode dashes, and non-breaking spaces into clean ASCII.
   - Computes deterministic SHA256 hashes and token approximations.
2. [classifier_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/classifier_service.py)
   - Classifies text into 15 official academic categories:
     `ADMISSIONS`, `COURSES`, `FEES`, `SCHOLARSHIPS`, `EXAMINATIONS`, `RESULTS`, `ACADEMIC_CALENDAR`, `FACILITIES`, `HOSTEL`, `LIBRARY`, `PLACEMENT`, `CONTACT`, `RULES`, `DEPARTMENTS`, `OTHER`.
   - Weighted scoring: URL signal (3.0x), Heading signal (2.5x), Body frequency (1.0x-3.0x).
   - Returns predicted category, confidence score (0.0 to 1.0), and topical tags.
3. [chunking_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/chunking_service.py)
   - Splits content into semantic chunks bounded by 800-character target and 100-character overlap.
   - Retains Markdown tables as atomic undivided blocks.
   - Attaches heading ancestry, category, hash, and token count.
4. [embedding_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/embedding_service.py)
   - Uses `GEMINI_EMBEDDING_MODEL` with the configured 768-dimensional output.
   - Indexing and retrieval fail explicitly when real embeddings are unavailable; synthetic vectors are not stored.
5. [ai_provider_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/ai_provider_service.py)
   - Primary AI: Google Gemini (`gemini-1.5-flash`).
   - Secondary AI: Configurable fallback (OpenAI `gpt-4o-mini`, Groq, Anthropic).
   - Telemetry: Logs prompt tokens, completion tokens, latency, and failovers into `ai_provider_events`.
   - Grounded offline fallback synthesizer.
6. [rag_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/rag_service.py)
   - Security prompt injection defense against adversarial jailbreaks ("ignore previous instructions", "act as DAN", "system prompt leakage").
   - Strict tenant-boundary retrieval (`college_id == :id` AND `status == 'PUBLISHED'` AND `is_active == TRUE`).
   - Source priority hierarchy resolution:
     1. `OFFICIAL_WEBSITE`
     2. `ADMIN_VERIFIED`
     3. `GEMINI_UNVERIFIED`
     4. `SECONDARY_AI_FALLBACK`
     5. `NO_RELIABLE_INFORMATION`
   - Real-time Server-Sent Events (SSE) streaming token generator.
7. [knowledge_service.py](file:///c:/Users/Vataliya%20Dharmik/OneDrive/Documents/College%20Chatbot/backend/app/services/knowledge_service.py)
   - Shared pipeline ingestion from `WebsitePage` and `DocumentPage`, preserving source identifiers and citations.
   - PDF pages are indexed from `extracted_text`; ordered paragraphs and pending facts are recorded separately.
   - Lifecycle state machine: `PROCESSING` -> `PENDING_REVIEW` -> `APPROVED` -> `PUBLISHED`.
   - Separate approval and publishing enforcement.
   - Full audit trail logging to `KnowledgeReview`.

### C. Background Tasks (`backend/app/tasks/knowledge_tasks.py`)
- `dispatch_website_knowledge_processing`: Dispatches asynchronous extraction with Celery / async fallback.
- `dispatch_document_knowledge_processing`: Dispatches PDF/OCR extraction to knowledge pipeline.
- Celery knowledge jobs reuse the persistent worker event loop used by document and crawler jobs.

---

## 3. API Endpoints

### College Admin Knowledge Management
- `GET /api/v1/college-admin/knowledge`: Query chunks with `status_filter`, `source_type`, `category`, and `search`.
- `GET /api/v1/college-admin/reviews`: List pending review chunks awaiting admin review.
- `POST /api/v1/college-admin/reviews/{id}/decision`: Approve or reject knowledge chunk.
- `POST /api/v1/college-admin/reviews/bulk-decision`: Batch review decision.
- `PATCH /api/v1/college-admin/knowledge/{id}`: Correct or edit chunk text.
- `POST /api/v1/college-admin/knowledge/{id}/publish`: Publish approved chunk to live search.
- `POST /api/v1/college-admin/knowledge/bulk-publish`: Batch publish approved chunks.
- `POST /api/v1/college-admin/knowledge/{id}/unpublish`: Unpublish chunk from live search.
- `POST /api/v1/college-admin/knowledge/process`: Trigger extraction on crawled page or document.

### Student Chat & RAG
- `POST /api/v1/chat/sessions`: Create chat conversation session.
- `GET /api/v1/chat/sessions`: List student sessions.
- `GET /api/v1/chat/sessions/{id}`: Fetch turn-by-turn session messages.
- `POST /api/v1/chat/sessions/{id}/messages`: Submit user prompt and receive grounded answer with citations.
- `POST /api/v1/chat/sessions/{id}/stream`: Stream answer tokens via Server-Sent Events (SSE).
- `POST /api/v1/chat/messages/{id}/feedback`: Submit rating and feedback on answer accuracy.

---

## 4. Frontend Enhancements

1. **Student Chat Interface** (`apps/user-frontend/src/app/chat/page.tsx`):
   - Fixed race conditions: Uses `generateUUID()` (RFC 4122 v4) preventing 422 UUID parsing errors.
   - Ref-backed message queue: Prevents `loadSessions` from overwriting active user inquiries.
   - Instant response on pressing **Enter** in the textarea or clicking any **Suggested Question**.
   - Verified citation badges, source links, and copy/audio toolbar.
2. **Knowledge Explorer** (`apps/admin-frontend/src/app/college-admin/knowledge/page.tsx`):
   - Category filtering across all 15 domains.
   - Chunk text search, heading display, and source origin badges.
   - Individual "Publish" and "Unpublish" action controls.
3. **Review Queue** (`apps/admin-frontend/src/app/college-admin/reviews/page.tsx`):
   - Category tags, source links, and page number badges on each review card.
   - Edit modal, approve confirmation, and reject dialog with comment logging.

---

## 5. Verification Results

| Suite | Status | Metrics |
| :--- | :--- | :--- |
| `scripts/test_phase9_phase10_rag.js` | **PASSED** | 79 / 79 tests (100%) |
| Python Syntax (`py_compile`) | **PASSED** | 10 services & routers compiled cleanly |
| User Frontend Build (`next build`) | **PASSED** | 12 / 12 routes compiled (0 errors) |
| Admin Frontend Build (`next build`) | **PASSED** | 32 / 32 routes compiled (0 errors) |

