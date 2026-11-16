# Phase 6 — Website Knowledge Indexing & Retrieval Pipeline Trace (Part A)

**Date:** 2026-11-14
**Scope:** Code-inspection only (Part A). Read-only. No code or data changes.
**Tenant under audit:** AIT (`college_id = 11111111-1111-1111-1111-111111111111`)
**Source pages:** the 5 AIT `website_pages` rows live-verified in `.agents/tasks/live-verification-crawler-events-report.md`

> This document is **code inspection only**. It records what the source code and
> migrations say the pipeline does. Live database results (Part B), retrieval
> tests (Part C), and tenant-isolation live evidence (Part D) are a separate step
> and are NOT included here. Each finding below states whether it is *confirmed in
> code* or *not found in code*.

---

## 0. Summary of the six key findings (for the live-verification step)

| # | Item | Finding | Evidence |
|---|------|---------|----------|
| 1 | Knowledge-chunk table name + schema | `knowledge_chunks` (model `KnowledgeChunk`) | `backend/app/models/knowledge.py`; `database/migrations/006_create_knowledge_tables.sql`, `015_knowledge_and_rag_enhancements.sql` |
| 2 | Embedding model + dimensionality | **`text-embedding-004`, 768 dims** (Gemini). Confirmed in three places. | `config.py` (`EMBEDDING_DIMENSION=768`, `GEMINI_EMBEDDING_MODEL="text-embedding-004"`); `embedding_service.py` (`DIMENSION=768`, `MODEL_NAME="text-embedding-004"`); migration 006 column `embedding VECTOR(768)` |
| 3 | Chatbot retrieval service + invocation | `RAGService.retrieve_relevant_chunks` / `answer_question` (`backend/app/services/rag_service.py`), invoked from `POST /api/v1/chat/sessions/{id}/messages` (`send_chat_message`) and `POST /api/v1/chat/sessions/{id}/stream` (`stream_chat_message`) in `backend/app/api/v1/chat.py` | code, confirmed |
| 4 | Tenant (college_id) filter location | Applied **during/before** retrieval, not after: (a) application-level SQL `WHERE KnowledgeChunk.college_id == college_id` in `retrieve_relevant_chunks`; (b) DB-level RLS `p_chunks_tenant_isolation` (`college_id = current_app_tenant()`) driven by GUC `app.current_college_id` set via `set_rls_context`/`tenant_session` | code, confirmed |
| 5 | Source-citation mechanism | `RAGService.build_citations` builds a `source_citations` list per retrieved chunk: `title` (= `chunk.heading`), `source_type`, `similarity_score`, `section`, and `url` (= `chunk.source_url` for website chunks). Returned in the answer, stored on `ChatMessage.source_citations` (JSONB), and streamed as an SSE `metadata` event. | code, confirmed |
| 6 | Indexing task + auto-wiring | Celery task `process_website_knowledge_task` → `knowledge_service.process_website_pages`. **NOT wired to crawl completion.** Only caller is the manual admin endpoint `POST /api/v1/college-admin/knowledge/process`. No Celery beat schedule, no task chain. Plus the ingestion function references non-existent attributes (`cleaned_content`/`raw_html`) on `WebsitePage` (which has `cleaned_text`). | code, confirmed |

---

## 1. End-to-end pipeline diagram (real code locations)

```
                          ┌─────────────────────────────────────────────┐
  Admin triggers crawl    │  POST /api/v1/college-admin/crawler/sources  │
  (already done, prior   │  → create WebsiteSource + CrawlJob (PENDING)│
   phases)                │  → dispatch_crawl_job()                      │
                          │     backend/app/api/v1/college_admin.py     │
                          └─────────────────────────────────────────────┘
                                          │
                                          ▼
                          ┌─────────────────────────────────────────────┐
  Celery crawl task       │  run_website_crawl_job()                     │
  (app.tasks.crawler_tasks)│  → crawler_service.execute_crawl_job()      │
                          │     backend/app/services/crawler_service.py │
                          └─────────────────────────────────────────────┘
                                          │
            fetch + parse_and_clean_html  │  (+ JS fallback js_renderer)
            backend/app/services/         │
              html_extractor.py           ▼
                          ┌─────────────────────────────────────────────┐
  Stage 0 — WebsitePage   │  _save_or_deduplicate_page()                │
  ingestion (DONE)        │  → INSERT/UPDATE row in `website_pages`     │
                          │     model: WebsitePage  (website.py)        │
                          │     columns: college_id, url, title,        │
                          │      content_hash, cleaned_text,             │
                          │      content_length, http_status             │
                          └─────────────────────────────────────────────┘
                                          │
                          ★ NO automatic transition to chunks here ★
                            (see §6 below — this is the missing stage)
                                          │
              ┌───────────────────────────┴───────────────────────────┐
              │ ONLY manual path: admin POST /knowledge/process         │
              │   college_admin.py: trigger_knowledge_processing()      │
              │   → dispatch_website_knowledge_processing()             │
              │     backend/app/tasks/knowledge_tasks.py               │
              └───────────────────────────┬───────────────────────────┘
                                          ▼
                          ┌─────────────────────────────────────────────┐
  Stage 1 — chunking      │  chunker_service.chunk_content()            │
                          │   backend/app/services/chunking_service.py │
                          │   → List[ProcessedChunk]                    │
                          └─────────────────────────────────────────────┘
                                          │
  Stage 2 — embedding      ▼  embedding_service.get_embedding()         │
                          │   backend/app/services/embedding_service.py │
                          │   → 768-dim vector (Gemini or deterministic) │
                          └─────────────────────────────────────────────┘
                                          │
  Stage 3 — store          ▼  knowledge_service.process_website_pages()  │
  knowledge_chunks         │   backend/app/services/knowledge_service.py│
  (pgvector)               │   → INSERT into `knowledge_chunks`         │
                          │     status="PENDING_REVIEW", is_active=False│
                          │     embedding = Vector(768)                 │
                          └─────────────────────────────────────────────┘
                                          │
  Stage 4 — human review   ▼  approve_chunk → status=APPROVED (still inactive)
  & publish gate           │   publish_chunk → status=PUBLISHED, is_active=True
                          │   endpoints: /knowledge, /reviews/{id}/decision,
                          │     /knowledge/{id}/publish  (college_admin.py)
                          └─────────────────────────────────────────────┘
                                          │
  Student asks a question  │  POST /api/v1/chat/sessions/{id}/messages  │
                          │   → set_rls_context(college_id=session.college_id)
                          │   → rag_service.answer_question()            │
                          ▼     backend/app/api/v1/chat.py (send_chat_message)
                          ┌─────────────────────────────────────────────┐
  Stage 5 — tenant-scoped │  RAGService.retrieve_relevant_chunks()      │
  retrieval                │   backend/app/services/rag_service.py      │
                          │   SQL: WHERE college_id = X AND status='PUBLISHED'
                          │        AND is_active = TRUE                 │
                          │   (+ RLS p_chunks_tenant_isolation enforced)│
                          │   cosine similarity computed IN PYTHON      │
                          │   (pgvector <=> / HNSW index NOT used)       │
                          └─────────────────────────────────────────────┘
                                          │
  Stage 6 — chatbot       ▼  ai_provider_service.generate_response()     │
  response                 │   backend/app/services/ai_provider_service.py
                          │   Gemini primary; offline-grounded fallback │
                          └─────────────────────────────────────────────┘
                                          │
  Stage 7 — source        ▼  RAGService.build_citations()                 │
  citation                 │   → source_citations[] stored on           │
                          │     ChatMessage.source_citations (JSONB)    │
                          │   + SSE metadata event (stream_answer)      │
                          └─────────────────────────────────────────────┘
```

---

## 2. Stage-by-stage trace (with file + function/table names)

### Stage 0 — `WebsitePage` ingestion (already complete for the 5 AIT pages)
- **Table:** `website_pages`
- **Model:** `WebsitePage` — `backend/app/models/website.py`
  - Relevant columns: `college_id` (UUID FK→colleges), `source_id`, `crawl_job_id`, `url`, `title`, `meta_description`, `content_hash` (SHA-256, VARCHAR(64)), `cleaned_text` (TEXT, the extracted visible text), `content_length` (INTEGER = `len(cleaned_text)`), `http_status`, `fetched_at`.
  - **Note:** the column that holds extracted text is `cleaned_text`. There is **no** `cleaned_content` and **no** `raw_html` column. (Confirmed by reading the full model; see §6.)
- **Writer:** `crawler_service.WebsiteCrawlerService._save_or_deduplicate_page()` — `backend/app/services/crawler_service.py`. Deduplicates by `(college_id, url)` and SHA-256 `content_hash`.
- **HTML extraction:** `parse_and_clean_html()` — `backend/app/services/html_extractor.py`; JS fallback `render_page_with_browser()` — `backend/app/services/js_renderer.py` (threshold `JS_FALLBACK_THRESHOLD = 200` in `crawler_service.py`).
- **Crawl task:** `run_website_crawl_job` — `backend/app/tasks/crawler_tasks.py` → `crawler_service.execute_crawl_job()`.
- **Status:** Prior phases live-verified that 5 AIT `website_pages` rows exist with `college_id = 11111111-…` and non-empty `cleaned_text`. This stage is **DONE**.

### Stage 1 — text chunking
- **Service:** `SemanticChunkerService` (singleton `chunker_service`) — `backend/app/services/chunking_service.py`
- **Function:** `chunk_content(content, source_url, page_number, default_heading, extra_metadata) -> List[ProcessedChunk]`
  - Splits by Markdown headings (`_split_by_headings`), then sub-chunks to `target_chunk_size=800` / `max_chunk_size=1200` / `chunk_overlap=100`.
  - Skips fragments < 40 chars.
  - Classifies each chunk into 1 of 15 categories via `classifier_service.classify_text()` (`backend/app/services/classifier_service.py`).
  - Computes `content_hash` (SHA-256 via `text_normalizer.compute_sha256`) and `token_count` (`text_normalizer.estimate_tokens`).
  - Returns `ProcessedChunk` dataclass (`chunk_text`, `heading`, `category`, `confidence`, `content_hash`, `token_count`, `page_number`, `source_url`, `chunk_index`, `metadata`).

### Stage 2 — embedding generation
- **Service:** `EmbeddingService` (singleton `embedding_service`) — `backend/app/services/embedding_service.py`
- **Function:** `async get_embedding(text) -> List[float]` (768-dim). Batch helper: `get_embeddings_batch`.
- **Model:** Google Gemini **`text-embedding-004`**, dimensionality **768**.
  - `MODEL_NAME = "text-embedding-004"`, `DIMENSION = 768` (hard-coded in `embedding_service.py`).
  - Calls `https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent`.
  - **Deterministic offline fallback:** when `GEMINI_API_KEY` is placeholder/absent (`is_placeholder_key`), it uses `generate_deterministic_embedding()` — a hash/n-gram projection into a 768-dim unit vector. This is what runs in dev/test environments without a real key.
- **Dimensionality confirmed in three independent places** (see §3 below).

### Stage 3 — storage into `knowledge_chunks` (pgvector)
- **Function:** `KnowledgeService.process_website_pages(college_id, session, page_ids)` — `backend/app/services/knowledge_service.py`
  - Selects `WebsitePage` rows for the tenant (optionally filtered by `page_ids`).
  - For each page: calls `chunker_service.chunk_content(...)`, then for each `ProcessedChunk`:
    - Dedup check: `SELECT id FROM knowledge_chunks WHERE college_id=:c AND content_hash=:h`.
    - Generates embedding via `embedding_service.get_embedding(p_chunk.chunk_text)`.
    - `session.add(KnowledgeChunk(...))` with `source_type="OFFICIAL_WEBSITE"`, `source_id=page.id`, `source_url=p_chunk.source_url`, `category`, `heading`, `content_hash`, `chunk_text`, `chunk_metadata`, `embedding`, **`status="PENDING_REVIEW"`**, **`is_active=False`** (i.e. *never* auto-published).
  - `await session.commit()`.
- **Table / model:** `knowledge_chunks` / `KnowledgeChunk` — `backend/app/models/knowledge.py` (schema in §3).
- **Worker entrypoint:** `process_website_knowledge_task` (Celery, `name="app.tasks.knowledge_tasks.process_website_knowledge_task"`, `bind=True`, `max_retries=2`) — `backend/app/tasks/knowledge_tasks.py`. Runs `asyncio.run(...)` → `tenant_session(college_id)` → `knowledge_service.process_website_pages`.

### Stage 4 — human review & publish gate (gates retrieval)
- **Service methods** (`knowledge_service.py`): `approve_chunk` (→ `APPROVED`, `is_active=False`), `reject_chunk`, `publish_chunk` (→ `PUBLISHED`, `is_active=True`), `unpublish_chunk`, `update_chunk_text`. Each writes a `KnowledgeReview` audit row.
- **Admin endpoints** (`backend/app/api/v1/college_admin.py`):
  - `GET /knowledge` — `list_knowledge_chunks` (filter by status/source_type/category/search).
  - `GET /reviews` — `list_pending_reviews` (status=PENDING_REVIEW).
  - `POST /reviews/{chunk_id}/decision` — `submit_review_decision` (APPROVE/REJECT).
  - `POST /reviews/bulk-decision` — `bulk_review_decisions`.
  - `PATCH /knowledge/{chunk_id}` — `update_chunk_text` (edit before approval).
  - `POST /knowledge/{chunk_id}/publish` — `publish_knowledge_chunk` (APPROVED → PUBLISHED).
  - `POST /knowledge/bulk-publish` — bulk publish.
  - `POST /knowledge/{chunk_id}/unpublish` — `unpublish_knowledge_chunk`.
- **Critical gate:** retrieval (Stage 5) only returns `status="PUBLISHED" AND is_active=True`. New chunks are `PENDING_REVIEW` + `is_active=False`, so they are **invisible to the chatbot until an admin approves AND publishes them.**

### Stage 5 — tenant-scoped retrieval
- **Service:** `RAGService` (singleton `rag_service`) — `backend/app/services/rag_service.py`
- **Function:** `async retrieve_relevant_chunks(college_id, query, session, top_k=5, min_similarity=0.40) -> List[Tuple[KnowledgeChunk, float]]`
  - Generates query embedding via `embedding_service.get_embedding(query)`.
  - **Application-level tenant filter (in the SQL, before ranking):**
    ```python
    select(KnowledgeChunk).where(and_(
        KnowledgeChunk.college_id == college_id,
        KnowledgeChunk.status == "PUBLISHED",
        KnowledgeChunk.is_active == True,
    ))
    ```
    If empty, a fallback query relaxes to `status.in_(["APPROVED","PUBLISHED"])` but keeps `is_active==True`.
  - Loads the matching chunks, then computes cosine similarity **in Python** via `_cosine_similarity(query_vector, chunk.embedding)` and keeps those ≥ `min_similarity`, sorted desc, top `top_k`.
  - **Note (not a defect, but relevant to Part C):** the pgvector distance operator (`<=>`) and the HNSW index `idx_chunks_embedding_hnsw` (migration 010) are **not used** by this code path — ranking is done in application memory. So "similarity score" is the Python cosine value, not a DB-returned distance.
- **Invocation (chatbot):**
  - `send_chat_message` — `POST /api/v1/chat/sessions/{session_id}/messages` (`backend/app/api/v1/chat.py`). Calls `set_rls_context(session, college_id=chat_session.college_id, ...)` then `rag_service.answer_question(college_id=chat_session.college_id, query=..., session=..., language=..., college=..., session_id=...)`.
  - `stream_chat_message` — `POST /api/v1/chat/sessions/{session_id}/stream`. Returns `StreamingResponse(rag_service.stream_answer(...))`.
- **Full answer pipeline:** `answer_question` does prompt-injection check → `retrieve_relevant_chunks` → `build_citations` → recent conversation context (`get_recent_conversation_context`, last 4 turns from `chat_messages`) → multilingual instruction (`multilingual_config`) → `ai_provider_service.generate_response(...)` → `resolve_source_type_hierarchy(...)` → returns `{answer_text, is_verified, answer_source_type, source_citations, token_count, model_used}`. If no reliable evidence → localized fallback message (`multilingual_config.get_fallback_message`).

### Stage 6 — chatbot response generation
- **Service:** `AIProviderService` (singleton `ai_provider_service`) — `backend/app/services/ai_provider_service.py`
- **Function:** `async generate_response(prompt, system_instruction, context_chunks, language, session)`.
  - Primary: Google Gemini (`settings.GEMINI_DEFAULT_MODEL = "gemini-1.5-flash"`, `GEMINI_API_KEY`).
  - Secondary fallback: OpenAI/Groq (`SECONDARY_AI_ENABLED`, `SECONDARY_AI_MODEL = "gpt-4o-mini"`) — disabled by default.
  - Offline/mock fallback: `_generate_offline_grounded(...)` when the Gemini key is placeholder.
- **System instruction** is hard-coded in `rag_service.SYSTEM_INSTRUCTION` ("CampusAI … ground answers strictly in provided evidence … if evidence lacks the answer, state that official records do not have verified information").

### Stage 7 — source citation
- **Function:** `RAGService.build_citations(scored_chunks, college)` — `backend/app/services/rag_service.py`.
  - For each `(chunk, score)` builds:
    ```python
    {
      "title": chunk.heading or "<College> Verified Knowledge",
      "source_type": chunk.source_type,            # e.g. "OFFICIAL_WEBSITE"
      "similarity_score": score,
      "section": chunk.heading or chunk.category,
      "url": chunk.source_url,                       # set for website chunks
    }
    ```
  - For website chunks `chunk.source_url` is populated (= the crawled page URL, set in `process_website_pages` from `page.url`), so citations carry the real source URL. PDF/DOCUMENT chunks instead get `page_number`.
- **Persistence:** the citations list is stored on `ChatMessage.source_citations` (JSONB column) — `backend/app/models/chat.py`. The assistant message is created in `send_chat_message` with `source_citations=rag_result["source_citations"]` and `answer_source_type=rag_result["answer_source_type"]`.
- **Streaming:** `stream_answer` emits a `data: {"type":"metadata","is_verified":...,"answer_source_type":...,"source_citations":[...],...}` SSE event before `[DONE]`.

---

## 3. The six required specifics

### 3.1 Knowledge-chunk table name(s) and schema
- **Table:** `knowledge_chunks`
- **ORM model:** `KnowledgeChunk` — `backend/app/models/knowledge.py`
- **Schema (model + migrations 006 + 015):**

| Column | Type | Source |
|---|---|---|
| `id` | UUID PK | 006 |
| `college_id` | UUID, FK→colleges(id) ON DELETE CASCADE, indexed | 006 / model |
| `source_type` | VARCHAR(50) — `OFFICIAL_WEBSITE` for crawled pages | 006 / model |
| `source_id` | UUID — `WebsitePage.id` for website chunks | 006 / model |
| `source_url` | TEXT (nullable) — the crawled page URL | 015 / model |
| `page_number` | INTEGER (nullable) — used for PDF, NULL for web | 015 / model |
| `category` | VARCHAR(100) default `OTHER` — one of 15 categories | 015 / model |
| `heading` | VARCHAR(255) (nullable) — section heading | 015 / model |
| `content_hash` | VARCHAR(64) (indexed) — SHA-256 of normalized chunk text | 015 / model |
| `chunk_text` | TEXT NOT NULL | 006 / model |
| `chunk_metadata` | JSONB default `'{}'` | 015 / model |
| `embedding` | `VECTOR(768)` (nullable) | 006 / model (`Vector(settings.EMBEDDING_DIMENSION)`) |
| `status` | `knowledge_status` ENUM: `PROCESSING, PENDING_REVIEW, APPROVED, PUBLISHED, REJECTED, STALE, SUPERSEDED, FAILED` (default `PENDING_REVIEW`) | 006 / model |
| `is_active` | BOOLEAN (default TRUE in DDL, but service sets FALSE on insert) | 006 / model |
| `created_at`, `updated_at` | TIMESTAMPTZ | 006 / 015 |
- **Related tables:** `extracted_facts` (`ExtractedFact`), `knowledge_reviews` (`KnowledgeReview`, audit trail of APPROVE/REJECT/EDIT/PUBLISH/UNPUBLISH).
- **Indexes (migration 010):** `idx_chunks_tenant_lookup(college_id,status,is_active)`, HNSW `idx_chunks_embedding_hnsw` on `embedding vector_cosine_ops`, GIN `idx_chunks_fts` on `to_tsvector('english', chunk_text)`; plus 015 indexes on `(college_id,category)`, `(college_id,content_hash)`, `(college_id,status,is_active)`.
- **Note:** the HNSW and GIN indexes exist in the schema but are **not exercised** by the current retrieval code (§2 Stage 5).

### 3.2 Configured embedding model + dimensionality
- **Model:** Google Gemini **`text-embedding-004`**
- **Dimensionality:** **768**
- **Confirmed in three independent places (do not assume):**
  1. `backend/app/core/config.py` — `GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"` and `EMBEDDING_DIMENSION: int = 768`.
  2. `backend/app/services/embedding_service.py` — class constants `MODEL_NAME = "text-embedding-004"`, `DIMENSION = 768`; REST call to `…/models/text-embedding-004:embedContent`.
  3. `database/migrations/006_create_knowledge_tables.sql` — `embedding VECTOR(768)` with comment "768-dimensional vector embedding generated by Google Gemini text-embedding-004". The ORM column is `Vector(settings.EMBEDDING_DIMENSION)` i.e. `Vector(768)`.
- **Runtime behavior:** with a placeholder/absent `GEMINI_API_KEY` (the dev case), `get_embedding` returns the deterministic 768-dim fallback vector — same dimensionality, different values.

### 3.3 Chatbot retrieval service function(s) and how invoked
- **Service:** `RAGService` (`backend/app/services/rag_service.py`).
- **Retrieval function:** `retrieve_relevant_chunks(college_id, query, session, top_k=5, min_similarity=0.40)`.
- **Orchestrator:** `answer_question(...)` (and `stream_answer(...)` for SSE) which wraps retrieval + citations + LLM.
- **Invoked from:**
  - `POST /api/v1/chat/sessions/{session_id}/messages` → `send_chat_message` (`backend/app/api/v1/chat.py`) → `rag_service.answer_question(...)`.
  - `POST /api/v1/chat/sessions/{session_id}/stream` → `stream_chat_message` → `rag_service.stream_answer(...)`.
  - Both set RLS context via `set_rls_context(session, college_id=chat_session.college_id, ...)` before calling.

### 3.4 Where tenant (college_id) filtering is applied
- **Before/during retrieval, not after. Two layers:**
  1. **Application-level (in the SELECT):** `retrieve_relevant_chunks` builds the query with `KnowledgeChunk.college_id == college_id` together with the `status='PUBLISHED'`/`is_active=True` predicates — `backend/app/services/rag_service.py`. The tenant filter is part of the SQL sent to Postgres, applied before any similarity ranking.
  2. **Database-level (RLS):** policy `p_chunks_tenant_isolation` on `knowledge_chunks` (`database/migrations/017_row_level_security_policies.sql`):
     ```sql
     USING (
       college_id = current_app_tenant()
       OR is_platform_super_admin()
       OR (status='PUBLISHED' AND is_active=TRUE
           AND (current_app_tenant() IS NULL OR college_id = current_app_tenant()))
     )
     ```
     `current_app_tenant()` reads the GUC `app.current_college_id` (`database/migrations/011_prepare_rls.sql`), which is set per-transaction by `set_rls_context()` / `tenant_session()` in `backend/app/database/session.py`. RLS is `ENABLE ROW LEVEL SECURITY` on `knowledge_chunks` (migrations 011 & 017). The runtime connects as the least-privilege role `college_app_user` (`DATABASE_APP_ROLE_URL`, NOBYPASSRLS — per config docstring).
- **Conclusion:** an AIT-scoped session (`app.current_college_id = 11111111-…`) cannot read RCTI chunks either at the SQL layer or the RLS layer. Filtering is applied during the query, never only post-retrieval.

### 3.5 Source-citation mechanism
- **Builder:** `RAGService.build_citations(scored_chunks, college)` (`backend/app/services/rag_service.py`).
- Per retrieved chunk it emits `{title, source_type, similarity_score, section, url}`. For website chunks `url = chunk.source_url` (the crawled page URL). `title`/`section` default to `chunk.heading` else `chunk.category`.
- **Hierarchy banner:** `resolve_source_type_hierarchy(...)` returns `OFFICIAL_WEBSITE` if any retrieved chunk is `OFFICIAL_WEBSITE`/`WEBSITE`, else `ADMIN_VERIFIED`, else `GEMINI_UNVERIFIED`/`SECONDARY_AI_FALLBACK`/`NO_RELIABLE_INFORMATION`. `is_verified` is True only for `OFFICIAL_WEBSITE`/`ADMIN_VERIFIED`.
- **Persistence:** `ChatMessage.source_citations` (JSONB) and `ChatMessage.answer_source_type` (ENUM `answer_source_type`) — `backend/app/models/chat.py`.
- **Delivery:** returned in the JSON body of `POST /…/messages`; streamed as the `metadata` SSE event in `POST /…/stream`.

### 3.6 Indexing task + whether it is wired to run automatically on crawl completion
- **Celery task:** `process_website_knowledge_task` (`name="app.tasks.knowledge_tasks.process_website_knowledge_task"`, `bind=True`, `max_retries=2`) — `backend/app/tasks/knowledge_tasks.py`. Calls `knowledge_service.process_website_pages(...)`.
- **Dispatcher:** `dispatch_website_knowledge_processing(college_id, page_ids, background_tasks)` — same file. Tries `process_website_knowledge_task.delay(...)`; on broker failure falls back to a local async background task (`_run_async_website_knowledge`) or `asyncio.create_task`.
- **Is it wired to crawl completion? — NO.** Evidence:
  - `crawler_service.execute_crawl_job()` (`backend/app/services/crawler_service.py`) finalizes the job (status `COMPLETED`, updates `WebsiteSource.last_crawled_at`, logs the SUCCESS event) but **never** calls `dispatch_website_knowledge_processing` / `process_website_knowledge_task`. A full grep of `backend/**` shows `process_website_knowledge_task.delay` is called only from `dispatch_website_knowledge_processing`, and `dispatch_website_knowledge_processing` is called only from one place: `trigger_knowledge_processing` (`backend/app/api/v1/college_admin.py`, route `POST /api/v1/college-admin/knowledge/process`) — a **manual admin action**.
  - `celery_app.py` `include=["app.tasks.crawler_tasks","app.tasks.document_tasks"]` (knowledge_tasks not even in the include list), and there is **no `beat_schedule` / `crontab` / `chain(...)` / `on_success`** hook anywhere (grep confirmed).
  - **No database trigger** auto-creates chunks from `website_pages`: a grep of all migrations for `TRIGGER` / `INSERT INTO knowledge_chunks` / `AFTER INSERT … website_pages` returned **no matches**. So `WebsitePage` rows do **not** automatically become knowledge chunks.
- **Therefore the 5 AIT pages were NOT indexed by the crawl itself.** Indexing requires an explicit manual call to `POST /college-admin/knowledge/process` with `source_type=WEBSITE` (and either a specific `source_id` = `WebsitePage.id`, or no `source_id` to process all tenant pages).
- **Additional defect in the ingestion function itself (confirmed in code):** `knowledge_service.process_website_pages` reads
  ```python
  raw_text = page.cleaned_content or page.raw_html or ""
  ```
  (`backend/app/services/knowledge_service.py`). The `WebsitePage` model (`backend/app/models/website.py`) has **`cleaned_text`** — there is no `cleaned_content` and no `raw_html` attribute. A grep across `backend/**` confirms `cleaned_content`/`raw_html` appear nowhere on the model. Accessing a non-existent attribute on a SQLAlchemy mapped instance raises `AttributeError`, so **even if the manual trigger is invoked, `process_website_pages` raises `AttributeError` on the first page**, the Celery task fails and retries (up to `max_retries=2`), and **no chunks are created.** This is a code-level defect independent of the wiring gap.
- **Even if both were fixed**, newly created chunks are `status="PENDING_REVIEW", is_active=False`, so retrieval (which requires `status="PUBLISHED" AND is_active=True`) would still return nothing until an admin reviews and publishes them (Stage 4).

---

## 4. Missing functionality / next step (proposed plan only — NOT implemented)

This trace identifies **three** things that prevent the 5 AIT `website_pages` from being searchable. Any fix is a separate implementation step; nothing is implemented here.

1. **No automatic indexing on crawl completion.** `execute_crawl_job` does not dispatch `process_website_knowledge_processing` after a successful crawl. Recommended (separate plan): after the job finalizes to `COMPLETED`, dispatch `dispatch_website_knowledge_processing(college_id, page_ids=[…new/changed page ids…])` (respecting the existing dedup so unchanged pages are skipped).
2. **Broken ingestion attribute reference.** `process_website_pages` uses `page.cleaned_content`/`page.raw_html`, which do not exist on `WebsitePage` (correct column is `cleaned_text`). Recommended (separate plan): change line to `raw_text = page.cleaned_text or ""` and re-run the existing unit tests.
3. **Human-review publish gate.** Even after chunks are created, they are `PENDING_REVIEW`/`is_active=False` and thus excluded from `retrieve_relevant_chunks`. This is **by design** (human-in-the-loop). Recommended (separate plan, if the goal is end-to-end automated website Q&A): define whether website pages from an approved official domain may bypass review to `PUBLISHED`, or require an admin to approve+publish — a product decision, not a code fix.

Each of the above should be its own implementation task with tests; this audit does not implement any of them.

---

## 5. Confirmed in code vs not found in code

**Confirmed in code (read directly):**
- Chunk table `knowledge_chunks` and full schema (model + migrations 006/010/015).
- Embedding model `text-embedding-004`, dimensionality 768 (config + embedding_service + migration).
- Retrieval function `retrieve_relevant_chunks` + chat endpoints `send_chat_message`/`stream_chat_message`.
- Tenant filter applied in SQL `WHERE` (rag_service) AND enforced by RLS `p_chunks_tenant_isolation` via GUC `app.current_college_id` (migrations 011/017, session.py).
- Citation builder `build_citations`, storage on `ChatMessage.source_citations`, SSE metadata event.
- Indexing task `process_website_knowledge_task` exists but is NOT wired to crawl completion; only caller is manual `POST /college-admin/knowledge/process`.
- `process_website_pages` references non-existent `cleaned_content`/`raw_html` (model has `cleaned_text`).
- No DB trigger auto-creates chunks from `website_pages`.
- Celery has no beat schedule / chain / on_success hook.

**Not found in code (could not locate):**
- Any automatic `WebsitePage → knowledge_chunks` transition (trigger, signal, beat schedule, or post-crawl dispatch). Not present.
- Any use of the pgvector `<=>` operator or the HNSW/GIN indexes by the retrieval path. Not present (ranking is in-Python cosine).
- A `cleaned_content` or `raw_html` column/property anywhere on `WebsitePage` or its base mixins. Not present.

---

## 6. Safety

- Read-only code inspection only. No files modified, no migrations/seeds run, no schema/RLS/auth/role/tenant/embeddings changes, no DB writes.
- No secrets or `.env` contents referenced; only public config defaults (`config.py`) are quoted.
