# Phase 2.1 — Final Safety Review Before Supabase Migration
**Report date:** Read-only investigation — no DB writes, no migration executed  
**Workspace root:** `c:\Users\HP\OneDrive\Desktop\College Chatbot`

---

## Summary

All 49 tests pass. The migration SQL is syntactically correct and idempotent. One structural discrepancy exists (ORM targets `ai_provider_events`; `001_initial_schema.sql` creates `provider_events`), causing silent telemetry failures. The `chat_messages` RLS policy in `database/migrations/019_complete_rls_policies.sql` does **not** block assistant inserts — it gates on the parent `chat_sessions.college_id`, not on `sender_role`. The tenant context is set before the assistant INSERT in `chat.py`. The feature flag (`AI_NEW_ENUM_ENABLED=False` default) correctly prevents new ENUM values from being written pre-migration.

**Recommendation:** GO for running migration `002_ai_failover_columns.sql` against an isolated test database, with one pre-migration fix required: resolve the `provider_events` vs `ai_provider_events` table name mismatch.

---

## Section 1 — Migration 002 Verification

### File: `backend/migrations/002_ai_failover_columns.sql`

**ENUM type name**  
The migration operates on `answer_source_type`. In `001_initial_schema.sql` the type is created as:
```sql
CREATE TYPE answer_source_type AS ENUM (
    'OFFICIAL_WEBSITE', 'ADMIN_VERIFIED', 'GEMINI_UNVERIFIED', 
    'SECONDARY_AI_FALLBACK', 'NO_RELIABLE_INFORMATION'
);
```
Migration 002 uses the same name: `ALTER TYPE answer_source_type ADD VALUE ...`. **Names match. ✓**

**New ENUM values**  
All three values are present:
- `ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE';`
- `ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED';`
- `ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED';`

**`IF NOT EXISTS` guards**  
All three `ALTER TYPE ... ADD VALUE` statements carry `IF NOT EXISTS`. This prevents "enum value already exists" errors on re-run. **All present. ✓**

**Column definitions — exact spec vs ORM**

| Column | SQL definition | ORM (`chat.py`) | Match |
|---|---|---|---|
| `answer_mode` | `VARCHAR(30) NULL` | `String(30), nullable=True` | ✓ |
| `actual_provider` | `VARCHAR(50) NULL` | `String(50), nullable=True` | ✓ |
| `actual_model` | `VARCHAR(100) NULL` | `String(100), nullable=True` | ✓ |
| `fallback_reason` | `TEXT NULL` | `Text, nullable=True` | ✓ |
| `attempt_count` | `INTEGER NOT NULL DEFAULT 0` | `Integer, default=0, server_default="0", nullable=False` | ✓ |
| `request_duration_ms` | `INTEGER NULL` | `Integer, nullable=True` | ✓ |

**`IF NOT EXISTS` guards on `ADD COLUMN`**  
All six columns are added in a single `ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS ...` statement. The `IF NOT EXISTS` clause is present for each column. **All present. ✓**

**`BEGIN`/`COMMIT` wrapping**  
The file contains **no** `BEGIN` or `COMMIT` block. It runs as six standalone auto-committing statements. **Correct. ✓**

**Verification queries**  
Two commented-out verification queries are present: one for `enum_range(NULL::answer_source_type)` and one for `information_schema.columns`. **Present. ✓**

**PG 17 transaction behavior note**  
The file header documents the pre-PG-14 restriction. For completeness: PostgreSQL 17 fully allows `ALTER TYPE ... ADD VALUE` inside a transaction block, and the new value *is* visible within that same transaction. The file's standalone (no-wrapping-transaction) approach is safe on all supported PostgreSQL versions including 17 — the `IF NOT EXISTS` guard makes all six ENUM statements idempotent regardless of execution context.

**Rerun safety**  
`IF NOT EXISTS` on both ENUM values and columns makes the file safe to rerun after a partial failure without manual cleanup.

---

### File: `backend/migrations/002_ai_failover_columns_down.sql`

- **`DROP COLUMN IF EXISTS`** for all six columns: `answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count`, `request_duration_ms`. **All present. ✓**
- **ENUM removal documented as no-op:** A clearly marked block explains that `ALTER TYPE ... DROP VALUE` does not exist in PostgreSQL and documents the manual 4-step procedure (convert to VARCHAR, drop type, recreate, restore). **Present. ✓**
- **Warning header present.** **✓**

**Rollback limitations**  
Dropping the six columns is permanent data loss. The comment in the downgrade script correctly instructs to back up first. The ENUM values (`AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED`) cannot be removed without a full table rewrite; the downgrade script correctly documents this as a no-op while the flag `AI_NEW_ENUM_ENABLED=False` is active.

**Existing rows**  
Migration 002 adds only nullable columns (or columns with a `DEFAULT 0` server default). No existing `chat_messages` rows are modified. No table rewrites. **Safe. ✓**

---

## Section 2 — Feature-Flag Analysis

### `AI_NEW_ENUM_ENABLED` default

In `backend/app/core/config.py`:
```python
AI_NEW_ENUM_ENABLED: bool = False
```
Default is explicitly `False`. The module-level flag in `rag_service.py` picks this up at import time:
```python
_NEW_ENUM_VALUES_AVAILABLE: bool = getattr(settings, 'AI_NEW_ENUM_ENABLED', False)
```

### Every code path that sets `answer_source_type`

**Path 1: `RAGService._source_type_for_general_ai(provider)` in `rag_service.py`**  
Called when `answer_mode == "GENERAL_AI"` and `AI_GENERAL_ANSWERING_ENABLED=True`.

| Provider | `_NEW_ENUM_VALUES_AVAILABLE=False` | `_NEW_ENUM_VALUES_AVAILABLE=True` |
|---|---|---|
| `OPENAI` | `SECONDARY_AI_FALLBACK` | `OPENAI_UNVERIFIED` |
| `XKIRO` / `SECONDARY_AI_FALLBACK` | `SECONDARY_AI_FALLBACK` | `XKIRO_UNVERIFIED` |
| `GEMINI` / `OFFLINE_GROUNDED` | `GEMINI_UNVERIFIED` | `AI_GUIDANCE` |
| `UNAVAILABLE` | `NO_RELIABLE_INFORMATION` | `NO_RELIABLE_INFORMATION` |

When flag is `False`, none of the new ENUM values (`AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED`) can be produced. **Safe pre-migration. ✓**

**Path 2: `RAGService.resolve_source_type_hierarchy(scored_chunks, provider_source)` in `rag_service.py`**  
Called when `answer_mode` is `MIXED` or `COLLEGE_KNOWLEDGE`. Returns one of:
- `OFFICIAL_WEBSITE` — when any chunk has `source_type` in `("WEBSITE", "OFFICIAL_WEBSITE")`
- `ADMIN_VERIFIED` — when any chunk has `source_type` in `("DOCUMENT", "PDF", "ADMIN_STRUCTURED", "FAQ")`
- `SECONDARY_AI_FALLBACK` — when provider is `SECONDARY_AI_FALLBACK`, `OPENAI`, or `XKIRO` and no website/admin chunks
- `GEMINI_UNVERIFIED` — fallback for GEMINI provider

This method has no dependency on `_NEW_ENUM_VALUES_AVAILABLE` and never produces the three new values. **Safe pre-migration. ✓**

**Path 3: Security block in `RAGService.answer_question()`**  
On prompt injection detection, hardcodes `"ADMIN_VERIFIED"`. This is an existing value. **Safe. ✓**

**Path 4: Unavailability path in `answer_question()`**  
When `actual_provider == "UNAVAILABLE"`, hardcodes `"NO_RELIABLE_INFORMATION"`. **Safe. ✓**

**Path 5: Disabled general AI path**  
When `answer_mode == "GENERAL_AI"` and `AI_GENERAL_ANSWERING_ENABLED=False`, hardcodes `"NO_RELIABLE_INFORMATION"`. **Safe. ✓**

**Path 6: `api/v1/chat.py` user message INSERT**  
The user message is inserted with `answer_source_type="OFFICIAL_WEBSITE"` — a hardcoded existing value, unrelated to the flag. **Safe. ✓**

### Pre-migration GO/NO-GO

**GO.** When `AI_NEW_ENUM_ENABLED=False` (the default), no code path can produce `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, or `XKIRO_UNVERIFIED`. The application starts and operates correctly against the pre-migration schema.

---

## Section 3 — Telemetry Discrepancy

### Exact table name in SQL vs ORM

| Source | Table name |
|---|---|
| `backend/migrations/001_initial_schema.sql` (Entity 19) | `provider_events` |
| `backend/app/models/ai.py` (`AIProviderEvent.__tablename__`) | `ai_provider_events` |

These do not match.

### Current failure behavior

`AIProviderService._log_telemetry()` in `ai_provider_service.py` does:
```python
async def _log_telemetry(self, ...):
    try:
        event = AIProviderEvent(...)
        session.add(event)
        await session.flush()
    except Exception as exc:
        logger.warning("Failed to record AI telemetry event: %s", exc)
```

The `except` clause catches all exceptions and logs a warning, so telemetry INSERTs fail **silently**. The API continues to function; only telemetry is lost. No crash, no user-visible error.

### Two fix options

**Option A — Rename the database table from `provider_events` to `ai_provider_events`**  
Requires a new migration: `ALTER TABLE provider_events RENAME TO ai_provider_events;`. This carries risk: any existing RLS policies, indexes, foreign keys, or Supabase triggers referencing `provider_events` by name must be updated. The index `idx_provider_events_config` would also need renaming. Must be coordinated with any external tooling or dashboards querying `provider_events`.

**Option B — Change the ORM `__tablename__` from `ai_provider_events` to `provider_events`**  
A one-line Python change: `__tablename__ = "provider_events"`. No DB migration required. No RLS policy changes. No data risk. Existing rows in `provider_events` immediately become visible to the ORM.

**Recommendation: Option B.** It requires no database schema change, no migration coordination, no RLS updates, and carries zero data risk. The ORM `__tablename__` is an application-layer mapping, not a database constraint.

**Note:** This discrepancy is a pre-existing issue not introduced by Phase 2. It should be fixed in a separate tracked change before migration 002 is applied to production, as telemetry is needed to validate provider failover behavior post-migration.

---

## Section 4 — RLS Root Cause and Fix Proposal

### RLS policies on `chat_messages`

`001_initial_schema.sql` does **not** enable RLS on `chat_messages` and defines no policies on it. The actual policies are defined in `database/migrations/011_prepare_rls.sql` (enables RLS) and `database/migrations/019_complete_rls_policies.sql` (creates policies).

**Policy 1: `p_chat_messages_tenant`**
```sql
CREATE POLICY p_chat_messages_tenant ON chat_messages
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = current_app_tenant()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM chat_sessions cs
            WHERE cs.id = chat_messages.session_id
              AND cs.college_id = current_app_tenant()
        )
    );
```
- Command: `ALL` (SELECT, INSERT, UPDATE, DELETE)
- Role: not role-restricted (applies to `college_app_user`)
- USING / WITH CHECK: requires `chat_sessions.college_id = current_app_tenant()`
- Does **not** inspect `sender_role`; does **not** use `auth.uid()`

**Policy 2: `p_chat_messages_super_admin`**
```sql
CREATE POLICY p_chat_messages_super_admin ON chat_messages
    FOR ALL
    USING (is_platform_super_admin())
    WITH CHECK (is_platform_super_admin());
```
- Allows super admins to bypass the tenant check.

### Root cause of assistant INSERT failure

The WITH CHECK expression for `p_chat_messages_tenant` requires that the parent `chat_sessions` row exists AND its `college_id` matches `current_app_tenant()`. The INSERT fails if `app.current_college_id` is not set before the assistant message INSERT.

Examining `api/v1/chat.py`'s `send_chat_message()` handler:

1. An early `set_rls_context` call sets the college_id from the `X-College-ID` header (line ~230), but this is a partial context with `user_id=None`.
2. A second `set_rls_context` call (line ~243) sets the full context from `chat_session.college_id` and `chat_session.user_id`. This runs before `create_message(user_msg)`.
3. After RAG generation, a **third** `set_rls_context` call (line ~306) re-applies the same full context immediately before `create_message(assistant_msg)`.

The assistant INSERT therefore has the tenant context set before it executes. The previously reported "new row violates row-level security policy" error is **not caused by missing tenant context** — it would only occur if `current_app_tenant()` returns `NULL`, meaning `app.current_college_id` was not set or was reset between the user message INSERT and the assistant message INSERT.

**The third `set_rls_context` call before the assistant INSERT is the correct fix and is already in place.**

The `create_message()` repository method does not set any RLS context — it relies entirely on the caller, which is correct.

### Minimal safe fix confirmation

The fix is already implemented: `set_rls_context` is called a third time immediately before `saved_assistant_msg = await chat_repo.create_message(assistant_msg)`. No policy change is required. No `sender_role` restriction exists. Tenant isolation is maintained.

If the error recurs in live testing, the cause would be one of:
1. The session using the `DATABASE_URL` (admin role with BYPASSRLS) instead of `DATABASE_APP_ROLE_URL` — both are in config. Confirm the FastAPI runtime uses `DATABASE_APP_ROLE_URL`.
2. A transaction commit between the user and assistant inserts that discards the transaction-local GUC, combined with a missing `set_rls_context` call before the second transaction begins. The existing code guards against this.

---

## Section 5 — Metadata Pipeline Trace

Tracing a Gemini→OpenAI failover request end-to-end:

### Step 1: `ai_provider_service.generate_response()` return dict

On success, the dict returned contains:
```
text, provider, model, latency_ms, answer_mode, fallback_reason, attempt_count,
prompt_tokens, completion_tokens
```
Note: `answer_mode` is hardcoded to `"COLLEGE_KNOWLEDGE"` for all successful real-API calls in `generate_response()`, regardless of the actual answer mode (which is determined by chunk retrieval in `rag_service`). `latency_ms` is wall-clock time from `start_time` to after the successful call.

### Step 2: `rag_service.answer_question()` return dict

```python
return {
    "answer_text":          answer_text,
    "is_verified":          is_verified,
    "answer_source_type":   final_source_type,
    "source_citations":     citations,
    "token_count":          ai_result.get("completion_tokens", 0) + ai_result.get("prompt_tokens", 0),
    "model_used":           actual_model or ai_result.get("model", ""),
    "answer_mode":          answer_mode,          # correctly set by RAG logic
    "actual_provider":      actual_provider,       # from ai_result["provider"]
    "actual_model":         actual_model,          # from ai_result["model"]
    "fallback_reason":      ai_result.get("fallback_reason"),
    "attempt_count":        ai_result.get("attempt_count", 0),
    "request_duration_ms":  ai_result.get("latency_ms"),   # mapped from latency_ms
}
```

All 6 new fields are present. `request_duration_ms` correctly maps from `latency_ms`. **No gaps here. ✓**

**Minor note on `answer_mode`:** `ai_provider_service` returns `answer_mode="COLLEGE_KNOWLEDGE"` for all successful calls, but `rag_service` correctly overwrites this in its return dict with the value determined by chunk retrieval (`GENERAL_AI`, `MIXED`, or `COLLEGE_KNOWLEDGE`). The RAG service value is authoritative.

### Step 3: `api/v1/chat.py` `ChatMessage(...)` constructor

```python
assistant_msg = ChatMessage(
    id=uuid.uuid4(),
    session_id=session_id,
    sender_role="assistant",
    message_text=rag_result["answer_text"],
    is_verified=rag_result["is_verified"],
    answer_source_type=rag_result["answer_source_type"],
    source_citations=rag_result["source_citations"],
    token_count=rag_result["token_count"],
    model_used=model_used,
    answer_mode=rag_result.get("answer_mode"),
    actual_provider=rag_result.get("actual_provider"),
    actual_model=rag_result.get("actual_model"),
    fallback_reason=rag_result.get("fallback_reason"),
    attempt_count=rag_result.get("attempt_count", 0),
    request_duration_ms=rag_result.get("request_duration_ms"),
)
```

All 6 fields are explicitly named. **No gaps. ✓**

### Step 4: `schemas/chat.py` `ChatMessageResponse`

```python
class ChatMessageResponse(BaseModel):
    # ... existing fields ...
    answer_mode: Optional[str] = None
    actual_provider: Optional[str] = None
    actual_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    attempt_count: int = 0
    request_duration_ms: Optional[int] = None

    class Config:
        from_attributes = True
```

All 6 fields are present with correct types and `Optional`/default values for backward compatibility. **No gaps. ✓**

### Step 5: `VerificationBadge.tsx`

The TypeScript `sourceType` prop union covers all 8 ENUM values:

| ENUM value | Badge label | Icon |
|---|---|---|
| `OFFICIAL_WEBSITE` | "Verified by Official Website" | ShieldCheck |
| `ADMIN_VERIFIED` | "Admin Verified Document" | CheckCircle |
| `GEMINI_UNVERIFIED` | "General AI Guidance (Unverified)" | Sparkles |
| `SECONDARY_AI_FALLBACK` | "Fallback AI Guidance (Unverified)" | RefreshCcw |
| `AI_GUIDANCE` | "AI Guidance — Not verified by college" | Sparkles |
| `OPENAI_UNVERIFIED` | "OpenAI AI Guidance — Not verified by college" | RefreshCcw |
| `XKIRO_UNVERIFIED` | "xKiro AI Guidance — Not verified by college" | RefreshCcw |
| _(fallthrough / `NO_RELIABLE_INFORMATION`)_ | "No Verified Information Available" | HelpCircle |

All 8 values handled. **No gaps. ✓**

The `ChatMessageData` TypeScript interface in `chat-service.ts` also includes all 8 ENUM values in the `answer_source_type` union and all 6 new metadata fields as optional properties. **No gaps. ✓**

### Pipeline gaps summary

**One gap noted:** `request_duration_ms` measures wall-clock time from the start of `generate_response()` to the first successful API response. For a failover scenario (Gemini times out, OpenAI responds), `latency_ms` includes the Gemini timeout duration plus the OpenAI response time. This is documented behavior — it's total request time, not provider response time. No data is lost; this is expected semantics.

---

## Section 6 — Test Results

**Command run:**
```
.\.venv\Scripts\python.exe -m pytest backend/tests/test_phase2_metadata.py backend/tests/test_ai_answering.py backend/tests/test_rag_security_and_citations.py backend/tests/test_multi_tenant_isolation.py -v
```
**Platform:** Python 3.13.14, pytest 8.4.2, Windows

| Test file | Tests | Passed | Failed |
|---|---|---|---|
| `test_phase2_metadata.py` | 9 | 9 | 0 |
| `test_ai_answering.py` | 32 | 32 | 0 |
| `test_rag_security_and_citations.py` | 5 | 5 | 0 |
| `test_multi_tenant_isolation.py` | 3 | 3 | 0 |
| **Total** | **49** | **49** | **0** |

**Run time:** 6.70 seconds  
**No failures, no warnings.**

All tests use mocks for database and external AI API calls. No real Supabase writes occurred.

---

## Section 7 — GO/NO-GO Recommendation

### Verdict: **CONDITIONAL GO**

Safe to run `002_ai_failover_columns.sql` against an **isolated test database** provided the one pre-migration check below is addressed.

### Blockers before production deployment

| # | Item | Severity | Required action |
|---|---|---|---|
| 1 | **Telemetry table name mismatch** (`provider_events` in DB vs `ai_provider_events` in ORM) | Medium | Fix before production: either change `AIProviderEvent.__tablename__ = "provider_events"` (recommended, zero DB risk) or add a rename migration. Without this fix, all telemetry is silently lost post-migration — no data corruption, but failover metrics are unavailable. |
| 2 | **Confirm FastAPI runtime uses `DATABASE_APP_ROLE_URL`** (NOBYPASSRLS role) | High pre-prod | Verify `.env` has the app-role URL, not the admin URL. The admin URL bypasses RLS entirely. If the wrong URL is in use, all RLS testing is invalid. |

### Items confirmed safe to proceed with

- Migration SQL is idempotent, non-destructive, and correctly structured for standalone execution.
- All 6 ORM columns match the SQL definitions.
- Feature flag (`AI_NEW_ENUM_ENABLED=False`) prevents new ENUM values from being written before migration.
- The five original ENUM values are preserved; existing chat rows are unaffected.
- RLS policy on `chat_messages` does not block assistant inserts when tenant context is set.
- `set_rls_context` is called before the assistant INSERT in `send_chat_message`.
- All 8 ENUM values are handled in the frontend `VerificationBadge`.
- All 6 metadata fields flow cleanly from `ai_provider_service` → `rag_service` → `chat.py` → `ChatMessage` → `ChatMessageResponse`.
- 49/49 tests pass with no DB writes.

### Post-migration steps

1. Set `AI_NEW_ENUM_ENABLED=True` in the environment (after confirming migration applied).
2. Verify with the read-only verification queries in the migration file header.
3. Watch logs for telemetry warnings (once table name is fixed, these should cease).

---

## Section 8 — Explicit Safety Confirmation

- **No migration executed.** Neither `002_ai_failover_columns.sql` nor `002_ai_failover_columns_down.sql` was run.
- **No database writes.** All test invocations use mocked sessions; no connection to Supabase or any PostgreSQL instance was opened.
- **No secrets printed.** No API keys, database passwords, or service role keys appear in this report.
- **No RLS changes.** No policy was created, dropped, or altered.
- **No code modified.** This is a read-only investigation.
- **`AI_NEW_ENUM_ENABLED` was not changed.** It remains `False` (the default).
- **No role, membership, college ID, or embedding changes.** Not applicable to this investigation.
- **No crawler or PDF code touched.**
