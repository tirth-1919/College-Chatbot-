# Phase 6 — Website Knowledge Indexing & Retrieval Audit Report

**Date:** 2026-11-14
**Project:** AI FAQ College Chat Bot
**Tenant under audit:** AIT (`college_id = 11111111-1111-1111-1111-111111111111`)
**Scope:** Read-only audit + live verification. No code changes, no migrations/seeds, no DB writes, no RCTI reads, no commits. `WebsitePage`/chunk/embedding/RLS/role/tenant configuration untouched.

> A legend is used throughout to keep evidence types distinct:
> - **[LIVE DB]** — result of a SELECT executed against the running Supabase PostgreSQL database inside an AIT tenant-scoped async session (`AsyncSessionFactory` + `set_rls_context(college_id=AIT)`), rolled back at the end (never committed).
> - **[CODE]** — read from source files (Part A pipeline trace, `phase6-pipeline-trace.md`).
> - **[TESTS]** — automated test results carried over from prior phases (105 backend tests pass).

---

## 0. Overall verdict (one line)

**Five AIT pages indexed: NO — zero `knowledge_chunks` and zero embeddings exist for the AIT tenant, so the chatbot retrieval service returns zero chunks for every test question; the crawl → chunks stage is missing/broken (see §6).**

---

## 1. Pipeline diagram based on actual code

Reproduced from the Part A trace (`phase6-pipeline-trace.md`) with real file / function / table names. Stages 1–3 are the stages that should convert a crawled page into a searchable chunk but, as the live audit (§2–§3) shows, are **not running** for these 5 pages.

```
Admin triggers crawl (PRIOR PHASES — DONE)
  POST /api/v1/college-admin/crawler/sources            backend/app/api/v1/college_admin.py
  → create WebsiteSource + CrawlJob (PENDING)
  → dispatch_crawl_job()                               backend/app/tasks/crawler_tasks.py
        │
        ▼
Celery crawl task
  run_website_crawl_job()                              backend/app/tasks/crawler_tasks.py
  → crawler_service.execute_crawl_job()                backend/app/services/crawler_service.py
  → parse_and_clean_html()  (+ JS fallback render_page_with_browser)
        backend/app/services/html_extractor.py / js_renderer.py
        │
        ▼
Stage 0 — WebsitePage ingestion (DONE for the 5 AIT pages)
  crawler_service._save_or_deduplicate_page()          backend/app/services/crawler_service.py
  → INSERT/UPDATE row in `website_pages`
  Model: WebsitePage                                   backend/app/models/website.py
  Columns: college_id, source_id, crawl_job_id, url, title, meta_description,
           content_hash (SHA-256), cleaned_text (TEXT), content_length, http_status, fetched_at
        │
        ★ NO automatic transition to chunks here ★   (see §6 — this is the missing stage)
        │
        └─ ONLY manual path: admin POST /api/v1/college-admin/knowledge/process
              college_admin.py: trigger_knowledge_processing()
              → dispatch_website_knowledge_processing()  backend/app/tasks/knowledge_tasks.py
        ▼
Stage 1 — chunking  (NOT run for these pages)
  chunker_service.chunk_content() -> List[ProcessedChunk]  backend/app/services/chunking_service.py
        │
Stage 2 — embedding ▼  embedding_service.get_embedding() -> 768-dim vector
        backend/app/services/embedding_service.py
        Model: text-embedding-004, DIMENSION=768
        (Gemini API; deterministic 768-dim fallback on placeholder key / API failure)
        │
Stage 3 — store    ▼  knowledge_service.process_website_pages(college_id, session, page_ids)
  knowledge_chunks (pgvector)                          backend/app/services/knowledge_service.py
  → INSERT into `knowledge_chunks`
    status="PENDING_REVIEW", is_active=False (never auto-published)
        │
Stage 4 — human review & publish gate
  approve_chunk → status=APPROVED (still is_active=False)
  publish_chunk → status=PUBLISHED, is_active=True
  endpoints: /knowledge, /reviews/{id}/decision, /knowledge/{id}/publish
        backend/app/api/v1/college_admin.py
        │
        ▼
Student asks a question
  POST /api/v1/chat/sessions/{id}/messages  (send_chat_message)   backend/app/api/v1/chat.py
  POST /api/v1/chat/sessions/{id}/stream    (stream_chat_message)
  → set_rls_context(session, college_id=chat_session.college_id)
  → rag_service.answer_question(...)                       backend/app/services/rag_service.py
        ▼
Stage 5 — tenant-scoped retrieval
  RAGService.retrieve_relevant_chunks(college_id, query, session, top_k=5, min_similarity=0.40)
        backend/app/services/rag_service.py
  SQL: WHERE college_id = X AND status='PUBLISHED' AND is_active = TRUE
       (fallback relaxes to status IN ('APPROVED','PUBLISHED') keeping is_active=True)
       (+ RLS policy p_chunks_tenant_isolation enforced — see §5)
  Ranking: cosine similarity computed IN PYTHON (_cosine_similarity);
          pgvector <=> / HNSW / GIN indexes are NOT used by this code path
        │
Stage 6 — chatbot response ▼  ai_provider_service.generate_response()
        backend/app/services/ai_provider_service.py
        (Gemini primary; offline-grounded fallback when key placeholder/unreachable)
        │
Stage 7 — source citation ▼  RAGService.build_citations()
  → source_citations[] per chunk: {title(=chunk.heading), source_type, similarity_score, section, url(=chunk.source_url for website chunks)}
  → stored on ChatMessage.source_citations (JSONB)   backend/app/models/chat.py
  → streamed as SSE "metadata" event (stream_answer)
```

**Key tables (real names):**

| Table | Model | File |
|---|---|---|
| `website_pages` | `WebsitePage` | `backend/app/models/website.py` |
| `knowledge_chunks` | `KnowledgeChunk` | `backend/app/models/knowledge.py` |
| `knowledge_reviews` | `KnowledgeReview` | `backend/app/models/knowledge.py` |
| `chat_messages` | `ChatMessage` | `backend/app/models/chat.py` |

**Configured embedding model + dimensionality [CODE]** — confirmed in three independent places (do not assume 768):
1. `backend/app/core/config.py`: `GEMINI_EMBEDDING_MODEL = "text-embedding-004"`, `EMBEDDING_DIMENSION = 768`.
2. `backend/app/services/embedding_service.py`: `MODEL_NAME = "text-embedding-004"`, `DIMENSION = 768`.
3. `database/migrations/006_create_knowledge_tables.sql`: `embedding VECTOR(768)`, ORM `Vector(settings.EMBEDDING_DIMENSION)` = `Vector(768)`.
**[LIVE DB]** confirmed at runtime: `settings.EMBEDDING_DIMENSION = 768`, `settings.GEMINI_EMBEDDING_MODEL = "text-embedding-004"`.

---

## 2. Exact database tables and counts (AIT tenant-scoped, read-only)

All counts below are **[LIVE DB]** — SELECTs against the live Supabase database inside an AIT tenant-scoped session (`app.current_college_id = 11111111-…`), rolled back (no commit).

### `website_pages` (AIT)

| Count | Value |
|---|---|
| Rows for `college_id = 11111111-1111-1111-1111-111111111111` | **5** |

Per page (college_id all = AIT; `content_length` == `len(cleaned_text)` in every row):

| # | url | title | http_status | content_length | cleaned_text_len | college_id == AIT |
|---|-----|-------|-------------|----------------|------------------|-------------------|
| 1 | `https://www.aitindia.in/` | `AIT` | 200 | 7097 | 7097 | yes |
| 2 | `https://www.aitindia.in/about/ait-group` | `AIT` | 200 | 3025 | 3025 | yes |
| 3 | `https://www.aitindia.in/academics/calendar` | `AIT` | 200 | 425 | 425 | yes |
| 4 | `https://www.aitindia.in/departments/computer-eng` | `AIT` | 200 | 1287 | 1287 | yes |
| 5 | `https://www.aitindia.in/placement/cell` | `AIT` | 200 | 858 | 858 | yes |

(Page `id`s, in url order: `04d70252-…`, `8482ded6-…`, `97cbe06f-…`, `e8b624eb-…`, `48ff1076-…`.)

### `knowledge_chunks` (AIT)

| Count | Value |
|---|---|
| Rows for `college_id = AIT` | **0** |
| status / is_active breakdown | **(no rows)** |
| source_type breakdown | **(no rows)** |

### Embeddings (AIT)

| Metric | Value |
|---|---|
| Total chunks | 0 |
| Chunks with non-null `embedding` | 0 |
| `vector_dims(embedding)` min / max | `None` / `None` (no embeddings exist) |

(With 0 chunks there are necessarily 0 embeddings and 0 `knowledge_reviews` audit rows for the AIT tenant. `knowledge_reviews` was not separately counted because it is vacuously 0 given 0 chunks.)

**Source-type / verification-status expectation (from code):** website chunks would be inserted as `source_type = "OFFICIAL_WEBSITE"`, `status = "PENDING_REVIEW"`, `is_active = False`. **[LIVE DB]** there are no rows at all, so no chunk has any source_type / status — i.e. the verification-status check is "N/A: no rows".

---

## 3. Are the five AIT pages indexed? (per page)

Indexing = existence of ≥ 1 row in `knowledge_chunks` with `source_id = WebsitePage.id` (and `source_type = "OFFICIAL_WEBSITE"`) for the AIT tenant. **[LIVE DB]** each page was queried directly for matching chunks.

| Page url | Indexed? | Matching `knowledge_chunks` | Reason if NO |
|---|---|---|---|
| `https://www.aitindia.in/` | **NO** | 0 | No chunk created from this page (Stages 1–3 did not run) |
| `https://www.aitindia.in/about/ait-group` | **NO** | 0 | No chunk created from this page |
| `https://www.aitindia.in/departments/computer-eng` | **NO** | 0 | No chunk created from this page |
| `https://www.aitindia.in/placement/cell` | **NO** | 0 | No chunk created from this page |
| `https://www.aitindia.in/academics/calendar` | **NO** | 0 | No chunk created from this page |

**Result: 0 of 5 pages are indexed.** `WebsitePage` records do **not** automatically become `knowledge_chunks` — verified from the data (0 matching chunks for every page), and consistent with the code trace (no DB trigger, no post-crawl dispatch, no Celery beat/chain — see §6).

---

## 4. Retrieval results per test question

Retrieval was exercised through the **actual chatbot retrieval service** `RAGService.retrieve_relevant_chunks(college_id=AIT, query, session, top_k=5, min_similarity=0.40)` (`backend/app/services/rag_service.py`), called in-process inside the same AIT tenant-scoped session. This is the same function `POST /api/v1/chat/sessions/{id}/messages` (`send_chat_message`) and `POST /…/stream` (`stream_chat_message`) call. **[LIVE DB]**

For every question the service (a) generated a query embedding via `embedding_service.get_embedding`, then (b) ran `SELECT … WHERE college_id = AIT AND status='PUBLISHED' AND is_active=True`. Because there are **0** PUBLISHED/active chunks (in fact 0 chunks total — §2), every question returned an empty result list.

> Operational note (out of scope, no action taken — the safety rules forbid changing embeddings configuration): the Gemini `text-embedding-004:embedContent` endpoint returned HTTP 404 during the run, so `get_embedding` fell back to its deterministic 768-dim vector. This does not affect the verdict: even with a working embedding, 0 PUBLISHED chunks ⇒ 0 retrieved chunks.

| # | Question | Retrieved chunk count | Source URL | College ID | Similarity score | Retrieved text supports answer? |
|---|---|---|---|---|---|---|
| 1 | What information does AIT publish about its Computer Engineering department? | 0 | — (none) | — | — | **NO** — no evidence retrieved; the chatbot cannot answer this from the crawled pages because they are not indexed |
| 2 | What does AIT's website say about placements? | 0 | — (none) | — | — | **NO** — no evidence retrieved; not indexable |
| 3 | What information is available about the academic calendar? | 0 | — (none) | — | — | **NO** — no evidence retrieved; not indexable |

**Per-question live assertion:** `all retrieved chunks college_id == AIT` = `True` for all three (vacuously true on an empty result list — there were no chunks to be mis-tenant).

**No answers were invented.** The crawled `cleaned_text` does contain relevant text for these topics (the prior JS-extraction report confirms 12,692 chars across the 5 pages, including `/departments/computer-eng`, `/placement/cell`, `/academics/calendar`), but that text lives only in `website_pages.cleaned_text` — it was never chunked, embedded, or stored in `knowledge_chunks`, so the retrieval service cannot surface it.

---

## 5. Tenant-isolation evidence

Tenant isolation is enforced at **two independent layers**, both applied **before / during retrieval, never only after**.

### 5.1 Application-level SQL filter (before ranking) — [CODE]

`backend/app/services/rag_service.py`, `RAGService.retrieve_relevant_chunks`:

```python
stmt = (
    select(KnowledgeChunk)
    .where(and_(
        KnowledgeChunk.college_id == college_id,   # tenant filter is part of the SQL
        KnowledgeChunk.status == "PUBLISHED",
        KnowledgeChunk.is_active == True,
    ))
)
result = await session.execute(stmt)
chunks = list(result.scalars().all())
# ... only AFTER this tenant-scoped SELECT does cosine similarity ranking happen
```

The `college_id` predicate is in the SELECT sent to Postgres, so non-AIT rows are never loaded into memory and never ranked. This is the substantive "before/during, not after" guarantee.

### 5.2 Database-level RLS — [CODE] + [LIVE DB]

**[CODE]** RLS policy `p_chunks_tenant_isolation` on `knowledge_chunks` — `database/migrations/017_row_level_security_policies.sql`:

```sql
USING (
  college_id = current_app_tenant()
  OR is_platform_super_admin()
  OR (status='PUBLISHED' AND is_active=TRUE
      AND (current_app_tenant() IS NULL OR college_id = current_app_tenant()))
)
```

`current_app_tenant()` reads the GUC `app.current_college_id` (`database/migrations/011_prepare_rls.sql`), set per-transaction by `set_rls_context()` / `tenant_session()` in `backend/app/database/session.py`. The application engine connects as the least-privilege role `college_app_user` (NOBYPASSRLS) — `backend/app/database/connection.py`.

**[LIVE DB]** RLS + GUC sanity (read from system catalogs / current_setting — no tenant row data read, no RCTI rows read):

| Check | Result |
|---|---|
| `current_setting('app.current_college_id')` in the AIT session | `'11111111-1111-1111-1111-111111111111'` ✅ (GUC set to AIT) |
| `knowledge_chunks` `relrowsecurity` / `relforcerowsecurity` | `(True, False)` — RLS is **enabled** on the table (not forced; see note) |
| `current_user` role attributes | `('college_app_user', rolsuper=False, rolbypassrls=False)` — the app role does **not** bypass RLS ✅ |
| `knowledge_chunks` visible to AIT session (`WHERE college_id = AIT`) | 0 |
| Distinct `college_id`s visible to the AIT session (RLS-filtered) | `[]` — no other-tenant (incl. RCTI) college_id is visible ✅ |

**Note on `relforcerowsecurity = False`:** RLS is enabled but not *forced*. "Forced" only matters for the *table owner*; the application connects as `college_app_user` (not the owner), and the live check confirms `rolbypassrls = False` for that role, so RLS is fully enforced for every app request/worker session. The "not forced" flag does not weaken isolation for the app role.

### 5.3 Live isolation conclusion

- **AIT queries retrieve only AIT knowledge:** the SELECT in `retrieve_relevant_chunks` is restricted to `college_id = AIT`; the live run returned 0 chunks and the distinct-college_id check returned `[]` (only AIT context, no other tenant). ✅
- **No RCTI chunks are visible to AIT:** under the AIT-scoped session (`app.current_college_id = AIT`, RLS enabled, app role non-bypassing), the distinct-college_id list is empty of any non-AIT id; RCTI rows are hidden by RLS. The audit read **no RCTI rows** (only system catalogs and AIT-scoped SELECTs). ✅
- **Filtering is applied before/during retrieval, not only after:** the `college_id` predicate is in the SQL `WHERE` issued before any similarity ranking (§5.1); RLS independently restricts at the DB layer before rows reach the application (§5.2). ✅

---

## 6. Missing functionality and recommended next step (proposed plan — NOT implemented)

The audit identifies **three** blockers that prevent the 5 AIT `website_pages` from being searchable. **Nothing below is implemented** — this section is a proposed plan only, per the strict safety rules. Each item should be its own implementation task with tests.

### Blocker 1 — No automatic indexing on crawl completion
`crawler_service.execute_crawl_job()` (`backend/app/services/crawler_service.py`) finalizes the job to `COMPLETED` and logs the SUCCESS event but **never** dispatches `process_website_knowledge_processing` / `process_website_knowledge_task` after a successful crawl. A full grep (Part A trace §3.6) shows `dispatch_website_knowledge_processing` is called only from the manual admin endpoint `POST /api/v1/college-admin/knowledge/process` (`college_admin.py: trigger_knowledge_processing`). There is no Celery beat schedule, no `chain(...)`, no `on_success` hook, and **no DB trigger** creating chunks from `website_pages` (no `TRIGGER` / `AFTER INSERT … website_pages` / `INSERT INTO knowledge_chunks` in any migration).
**Live consequence (this audit):** 0 of 5 pages indexed.

**Recommended plan (separate task):** after `execute_crawl_job` finalizes the job to `COMPLETED`, dispatch `dispatch_website_knowledge_processing(college_id, page_ids=[ids of new/changed pages])` so the existing dedup path skips unchanged pages. Add a unit test asserting the dispatch is called once per completed crawl and not called on `FAILED`/`CANCELLED`.

### Blocker 2 — Broken ingestion attribute reference in `process_website_pages`
`knowledge_service.process_website_pages` reads:
```python
raw_text = page.cleaned_content or page.raw_html or ""
```
(`backend/app/services/knowledge_service.py`). The `WebsitePage` model (`backend/app/models/website.py`) has **`cleaned_text`** — there is no `cleaned_content` and no `raw_html` attribute (confirmed by reading the full model and grepping `backend/**`). Accessing a non-existent attribute on a SQLAlchemy mapped instance raises `AttributeError`, so **even if the manual trigger in Blocker 1 is invoked, `process_website_pages` raises `AttributeError` on the first page**, the Celery task fails and retries (up to `max_retries=2`), and **no chunks are created.**
**Live consequence (this audit):** even a manual `POST /knowledge/process` would not have produced chunks — consistent with the 0 chunks observed.

**Recommended plan (separate task):** change the line to `raw_text = page.cleaned_text or ""` (matching the model), and add a unit test that calls `process_website_pages` against a `WebsitePage` fixture and asserts chunks are created with `source_type="OFFICIAL_WEBSITE"`, `status="PENDING_REVIEW"`, `is_active=False`, `source_url=page.url`, and a 768-dim `embedding`.

### Blocker 3 — Human-review publish gate excludes new chunks from retrieval
Even after Blockers 1–2 are fixed, new chunks are inserted as `status="PENDING_REVIEW"`, `is_active=False`. `retrieve_relevant_chunks` requires `status="PUBLISHED" AND is_active=True` (with a fallback to `status IN ("APPROVED","PUBLISHED")` keeping `is_active=True`). Publishing requires an admin to `approve_chunk` then `publish_chunk` (`college_admin.py`). This is **by design** (human-in-the-loop).
**Live consequence (this audit):** even if chunks existed in `PENDING_REVIEW`, retrieval would still return 0 for students.

**Recommended plan (separate task, product decision):** decide whether website pages crawled from an approved official domain may bypass review to `PUBLISHED` (and under what conditions), or whether an admin must always approve+publish. This is a product decision, not a code fix; it must not be auto-granted (the safety rules forbid auto-assigning `ADMIN_VERIFIED`/`OFFICIAL_WEBSITE` status, and `is_active`/status changes are out of scope here). Implement only after the decision is made, with tests for the chosen path.

### Suggested implementation order
1. Blocker 2 first (the `cleaned_text` fix) — small, unblocks the indexing function itself.
2. Blocker 1 (post-crawl dispatch) — makes indexing automatic and re-runs the existing dedup.
3. Blocker 3 (publish-gate policy) — only after a product decision; can run an admin approve+publish pass on the 5 AIT chunks once Blockers 1–2 create them.

After Blockers 1–2 + an explicit approve+publish pass, re-run this audit: expect ≥ 5 `knowledge_chunks` for AIT with `source_type="OFFICIAL_WEBSITE"`, `status="PUBLISHED"`, `is_active=True`, 768-dim embeddings, and `retrieve_relevant_chunks` returning AIT chunks for the three test questions.

---

## 7. Method, safety, and limitations

**Method.** A temporary read-only Python script (`backend/_phase6_live_audit.py`, not committed, removed after the run) opened an async session via `AsyncSessionFactory`, called `set_rls_context(college_id=AIT, user_id=None, is_super_admin=False)`, executed only `SELECT` statements (ORM `select()` plus `text()` for `pg_class`/`pg_roles`/`current_setting`/`vector_dims` metadata), called `rag_service.retrieve_relevant_chunks` in-process, then `await session.rollback()` (never commit). All counts and per-page/per-question results above are from that single live run.

**Safety checklist.**
- [x] Read-only throughout; only SELECTs; session rolled back, never committed
- [x] No migrations or seed scripts
- [x] No production / Supabase schema changes
- [x] No PDF approval or deletion
- [x] No RLS, authentication, role, tenant-ID, or embeddings-configuration changes (RLS state and the Gemini 404 fallback were observed, not modified)
- [x] No duplicate chunks or embeddings created (none exist; none created)
- [x] No RCTI records read or modified (only system catalogs + AIT-scoped SELECTs)
- [x] No secrets or `.env` contents exposed (only public config defaults `EMBEDDING_DIMENSION=768`, `GEMINI_EMBEDDING_MODEL="text-embedding-004"`, and boolean "is the URL/key set" flags are quoted)
- [x] No code changes and no git commits; the temporary audit script was removed after the run

**Limitations.**
- With 0 chunks the live tenant-isolation test is *trivially* satisfied (nothing is visible, so nothing cross-tenant is visible). The substantive guarantee is the code-level filter (§5.1) plus RLS (§5.2), both confirmed enabled live.
- Retrieval "supports answer" is **NO** for all three questions purely because indexing did not run; this is not a verdict on the crawled text quality (the text exists in `website_pages.cleaned_text`).
- The Gemini `text-embedding-004:embedContent` 404 is noted factually but **not investigated** — it is out of scope for this audit and modifying embeddings configuration is forbidden by the safety rules.

**Evidence-type summary (live DB vs code vs tests).**
- [LIVE DB]: §2 counts, §3 per-page indexing, §4 retrieval results, §5.2 RLS/GUC live checks, §0 verdict.
- [CODE]: §1 pipeline diagram + file/function/table names, §5.1 SQL filter location, §5.2 RLS policy/migration locations, §6 the three blockers.
- [TESTS]: 105 backend tests pass (prior phases); this audit added/ran no new tests (read-only, by design).
