# DBA Review — AI Provider Failover Schema Migration
**Prepared:** Read-only investigation  
**No live database writes occurred during this investigation.**

---

## Summary

The `chat_messages` table was created by `backend/migrations/001_initial_schema.sql`, which is a plain SQL file — there is **no Alembic infrastructure** in this project (no `alembic.ini`, no `env.py`, no `versions/` directory). The term "Alembic migration" in the design document is aspirational; the first migration must bootstrap Alembic or be applied as a raw SQL script. This report provides both a raw SQL migration and an equivalent Alembic file so the team can choose.

The ORM `ChatMessage.answer_source_type` ENUM lists exactly the original five values. All six proposed new columns (`answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count`, `request_duration_ms`) are **absent from both the ORM model and the SQL schema** — they must be added. The three proposed new ENUM values (`AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED`) are also absent and must be added.

**Pre-migration compatibility: NO CRASH.** Both `rag_service.py` and `ai_provider_service.py` already contain explicit safe-proxy mappings that avoid writing the new ENUM values to the database before the migration runs. The app is safe to deploy today.

---

## Section A — Actual Live Schema Findings

### A1. `backend/app/models/chat.py` — `ChatMessage` ORM

**Python class:** `ChatMessage` (line ~52)

**ENUM definition:**
```python
PG_ENUM(
    "OFFICIAL_WEBSITE", "ADMIN_VERIFIED", "GEMINI_UNVERIFIED",
    "SECONDARY_AI_FALLBACK", "NO_RELIABLE_INFORMATION",
    name="answer_source_type", create_type=False
)
```
- `create_type=False` means SQLAlchemy will not attempt to CREATE the type; it must already exist in PostgreSQL.
- The five existing values exactly match what `001_initial_schema.sql` creates.

**All current columns (ChatMessage):**

| Column | SQLAlchemy type | Nullable | Default |
|--------|-----------------|----------|---------|
| `id` | UUID (PK) | No | gen_random_uuid() |
| `session_id` | UUID (FK → chat_sessions) | No | — |
| `sender_role` | String(20) | No | — |
| `message_text` | Text | No | — |
| `is_verified` | Boolean | No | False |
| `answer_source_type` | PG_ENUM (5 values) | No | NO_RELIABLE_INFORMATION |
| `source_citations` | JSONB | No | [] |
| `token_count` | Integer | No | 0 |
| `model_used` | String(100) | Yes | None |
| `created_at` | DateTime(tz) | No | utc_now |

**Missing columns (proposed, not yet present):**  
`answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count`, `request_duration_ms` — **none of these exist in the ORM or SQL schema.**

### A2. `backend/app/models/ai.py` — `AIProviderEvent`

**Table:** `ai_provider_events`

| Column | SQLAlchemy type | Nullable | Default |
|--------|-----------------|----------|---------|
| `id` | UUID (PK) | No | — |
| `config_id` | UUID (FK → ai_provider_configs, SET NULL) | Yes | — |
| `event_type` | String(50) | No | — |
| `latency_ms` | Integer | No | — |
| `prompt_tokens` | Integer | No | 0 |
| `completion_tokens` | Integer | No | 0 |
| `error_message` | Text | Yes | None |
| `created_at` | DateTime(tz) | No | utc_now |

**Note:** The SQL schema calls this table `provider_events`; the ORM calls it `ai_provider_events`. This is a pre-existing discrepancy that is out of scope for this migration but should be resolved separately.

### A3. Migration Infrastructure

There is **no Alembic infrastructure**. The project has:
- `backend/migrations/001_initial_schema.sql` — the only migration file, plain SQL, applied manually.
- No `alembic.ini`, no `alembic/env.py`, no `versions/` directory anywhere in the worktree (excluding `.venv` site-packages).

The "current head revision" is therefore the state after `001_initial_schema.sql`. There is no Alembic revision hash to reference.

**Consequence:** To apply this migration, the team must either:
1. Apply `002_ai_failover_columns.sql` as a raw SQL script (simplest path), or
2. Bootstrap Alembic first with `alembic init`, configure it, stamp the initial revision, then create a proper Alembic file.

Both options are provided below.

### A4. `backend/app/schemas/chat.py` — Pydantic Schemas

`ChatMessageResponse` serialises `answer_source_type` as `str` (no Enum constraint). It does not include `answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count`, or `request_duration_ms`. These fields are therefore never returned to the frontend even if the service computes them.

`SourceCitation.source_type` has a string default of `"OFFICIAL_WEBSITE"` — not an Enum; this is fine.

### A5. `backend/app/repositories/chat_repository.py`

`create_message()` does `self.session.add(message)` — it persists whatever fields are set on the `ChatMessage` ORM object. The repository is not the bottleneck. The bottleneck is that `chat.py` constructs `ChatMessage(...)` without the new fields, so they are silently omitted even after migration.

### A6. `backend/app/api/v1/chat.py`

The `send_chat_message` handler (line ~153) constructs `ChatMessage` with these fields only:
```python
ChatMessage(
    sender_role, message_text, is_verified, answer_source_type,
    source_citations, token_count, model_used
)
```
It explicitly reads `rag_result.get("actual_model")` and `rag_result.get("actual_provider")` for logic, but does **not** pass `answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count`, or `request_duration_ms` to the `ChatMessage` constructor. Post-migration, these six lines must be added.

The API response is `ChatMessageResponse.model_validate(saved_assistant_msg)`, which currently excludes the new fields from the JSON response because they are absent from both the ORM model and the Pydantic schema.

### A7. Frontend ENUM References

**User-frontend** (`apps/user-frontend/src/`):

| File | References |
|------|-----------|
| `services/chat-service.ts` | `answer_source_type` typed as `"OFFICIAL_WEBSITE" \| "ADMIN_VERIFIED" \| "GEMINI_UNVERIFIED" \| "SECONDARY_AI_FALLBACK" \| "NO_RELIABLE_INFORMATION"` (line 47) |
| `components/chat/VerificationBadge.tsx` | Handles all five existing values explicitly; unrecognised values fall through to the default "No Verified Information Available" branch (safe) |
| `app/chat/page.tsx` | References `answer_source_type: "OFFICIAL_WEBSITE"` in mock/test data only |

**Admin-frontend** (`apps/admin-frontend/src/`):

| File | References |
|------|-----------|
| `app/super-admin/.../page.tsx` | `badge_distribution` object with all five existing values as keys (hardcoded in a UI dashboard metrics mock) |
| `app/college-admin/.../page.tsx` | Tier descriptions referencing the five existing value names as strings in UI text |
| `types/college-admin.ts` | `source_type` typed as `"WEBSITE" \| "DOCUMENT" \| "ADMIN_STRUCTURED" \| ...` — not the ENUM, different field |

**Key finding:** No frontend code references `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, or `XKIRO_UNVERIFIED`. The existing type unions in `chat-service.ts` and `VerificationBadge.tsx` will need updating after migration, but they will not break before migration since the backend currently never emits the new values.

### A8. `backend/app/services/rag_service.py`

The service has two safe-proxy methods:

**`_source_type_for_general_ai(provider)`** (line ~175):
```python
if provider in ("OPENAI", "XKIRO", "SECONDARY_AI_FALLBACK"):
    return "SECONDARY_AI_FALLBACK"
if provider == "UNAVAILABLE":
    return "NO_RELIABLE_INFORMATION"
return "GEMINI_UNVERIFIED"  # GEMINI or OFFLINE_GROUNDED
```
The comment explicitly states: "AI_GUIDANCE / OPENAI_UNVERIFIED / XKIRO_UNVERIFIED are not yet in the DB enum. Safe proxies until migrations run."

**`resolve_source_type_hierarchy()`** also maps `provider_source in ("SECONDARY_AI_FALLBACK", "OPENAI", "XKIRO")` → `"SECONDARY_AI_FALLBACK"`.

**`answer_question()`** returns `answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count` in the result dict but notes they are written to memory only until the migration runs.

**Conclusion:** `rag_service.py` will never attempt to INSERT `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, or `XKIRO_UNVERIFIED` before migration. No crash risk.

### A9. `backend/app/services/ai_provider_service.py`

Returns `provider` values of `"GEMINI"`, `"OPENAI"`, `"XKIRO"`, `"UNAVAILABLE"`, `"OFFLINE_GROUNDED"`, `"NO_RELIABLE_INFORMATION"`. These are internal service labels, not DB ENUM values — they are never written to the database directly. `rag_service.py` translates them to DB-safe ENUM values before creating `ChatMessage`. No crash risk.

---

## Section B — Proposed Changes Confirmed Necessary

### B1. ENUM additions

| Value | In ORM? | In DB (001_initial_schema.sql)? | Action |
|-------|---------|----------------------------------|--------|
| `AI_GUIDANCE` | ❌ No | ❌ No | Add |
| `OPENAI_UNVERIFIED` | ❌ No | ❌ No | Add |
| `XKIRO_UNVERIFIED` | ❌ No | ❌ No | Add |
| `OFFICIAL_WEBSITE` | ✅ Yes | ✅ Yes | Preserve |
| `ADMIN_VERIFIED` | ✅ Yes | ✅ Yes | Preserve |
| `GEMINI_UNVERIFIED` | ✅ Yes | ✅ Yes | Preserve |
| `SECONDARY_AI_FALLBACK` | ✅ Yes | ✅ Yes | Preserve |
| `NO_RELIABLE_INFORMATION` | ✅ Yes | ✅ Yes | Preserve |

### B2. New columns

| Column | In ORM? | In DB SQL? | Action |
|--------|---------|------------|--------|
| `answer_mode VARCHAR(30)` | ❌ No | ❌ No | Add |
| `actual_provider VARCHAR(50)` | ❌ No | ❌ No | Add |
| `actual_model VARCHAR(100)` | ❌ No | ❌ No | Add |
| `fallback_reason TEXT` | ❌ No | ❌ No | Add |
| `attempt_count INTEGER NOT NULL DEFAULT 0` | ❌ No | ❌ No | Add |
| `request_duration_ms INTEGER` | ❌ No | ❌ No | Add |

All six columns are entirely absent. All must be added.

---

## Section C — Discrepancies Between Proposed Migration Doc and Actual Code

1. **No Alembic exists.** The design doc (`schema_changes_required.md`) references "Alembic migration" but the project has no Alembic infrastructure. The migration SQL is correct; the delivery mechanism does not yet exist.

2. **ORM not updated.** The design doc says "After migration, the ORM model and `chat.py` endpoint can be updated to persist the additional columns." The ORM model has not been updated and neither has the `ChatMessage(...)` constructor call in `chat.py`. These are required follow-on changes after migration (see Section G).

3. **`ai_provider_events` table name mismatch.** `001_initial_schema.sql` creates `provider_events`; the ORM (`ai.py`) maps `AIProviderEvent` to `ai_provider_events`. The design doc says "no changes to `ai_provider_events`" — which is correct for this migration — but the name discrepancy means the ORM telemetry inserts in `ai_provider_service.py` likely fail silently (the `except` clause at line ~270 catches and logs the error). Out of scope for this migration but flagged.

4. **`request_duration_ms` not populated by `rag_service.py`.** The service returns `answer_mode`, `actual_provider`, `actual_model`, `fallback_reason`, `attempt_count` — but not `request_duration_ms`. The column will always be NULL until `rag_service.py` is updated to pass `ai_result.get("latency_ms")`. Flag for the implementation step.

5. **`SourceCitation.source_type` in `chat-service.ts`** includes `"GEMINI_UNVERIFIED"` and `"SECONDARY_AI_FALLBACK"` as valid citation source types. These are not citation source types in the backend (`build_citations()` returns `chunk.source_type` which is `"OFFICIAL_WEBSITE"`, `"DOCUMENT"`, `"PDF"`, etc.). The TypeScript type union is wider than what the backend actually returns. Not a blocker but should be cleaned up.

---

## Section D — Exact Migration File

### D1. Raw SQL migration (apply manually — matches existing project pattern)

**File to create:** `backend/migrations/002_ai_failover_columns.sql`

```sql
-- ==============================================================================
-- Migration 002 — AI Provider Failover: ENUM extensions + new columns
-- Target: chat_messages table, answer_source_type ENUM
-- Apply with: psql $DATABASE_URL -f backend/migrations/002_ai_failover_columns.sql
--
-- IMPORTANT — PostgreSQL ENUM transaction-safety note:
--   ALTER TYPE ... ADD VALUE is NON-TRANSACTIONAL in PostgreSQL < 14.
--   In PostgreSQL 14+ it is transactional within a transaction block ONLY if
--   the value has not yet been used in any row. Because this is a purely additive
--   ADD VALUE (not modifying existing values), it is safe. However, the ALTER TYPE
--   statements MUST be committed BEFORE any INSERT using the new values runs.
--   This file issues each ALTER TYPE as an independent statement outside any
--   surrounding transaction so the new values are visible to subsequent statements.
--   If you wrap this file in a BEGIN/COMMIT block, the new ENUM values will NOT be
--   visible to ALTER TABLE statements in the same transaction on PG < 12.
--   Run this file standalone, not inside a transaction block.
-- ==============================================================================

-- Step 1: Add new ENUM values (non-transactional; must be committed first)
-- IF NOT EXISTS is supported from PostgreSQL 9.3+.
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED';

-- Step 2: Add new columns to chat_messages
-- ADD COLUMN IF NOT EXISTS is idempotent (PostgreSQL 9.6+).
-- All new columns are nullable or have a server default; existing rows are unaffected.
ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS answer_mode       VARCHAR(30)  NULL,
    ADD COLUMN IF NOT EXISTS actual_provider   VARCHAR(50)  NULL,
    ADD COLUMN IF NOT EXISTS actual_model      VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS fallback_reason   TEXT         NULL,
    ADD COLUMN IF NOT EXISTS attempt_count     INTEGER      NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS request_duration_ms INTEGER    NULL;

-- ==============================================================================
-- Verification queries (read-only, run after applying):
-- SELECT enum_range(NULL::answer_source_type);
--   Expected: {OFFICIAL_WEBSITE,ADMIN_VERIFIED,GEMINI_UNVERIFIED,
--              SECONDARY_AI_FALLBACK,NO_RELIABLE_INFORMATION,
--              AI_GUIDANCE,OPENAI_UNVERIFIED,XKIRO_UNVERIFIED}
--
-- SELECT column_name, data_type, is_nullable, column_default
--   FROM information_schema.columns
--   WHERE table_name = 'chat_messages'
--   ORDER BY ordinal_position;
-- ==============================================================================

-- Downgrade note:
--   PostgreSQL does NOT support removing values from an ENUM type without
--   dropping and recreating the type (which requires rewriting every table
--   that uses it). Downgrade of the ENUM additions is therefore a no-op —
--   the extra values remain in the type but will never be inserted by application
--   code (which still maps to old values via safe proxies). Column removal is
--   straightforward: DROP COLUMN IF EXISTS for each new column. See downgrade
--   script below.
```

**Downgrade script:** `backend/migrations/002_ai_failover_columns_down.sql`

```sql
-- ==============================================================================
-- Downgrade 002 — Remove new columns (ENUM values cannot be removed safely)
-- ==============================================================================

-- Remove new columns (safe, no data loss to existing columns)
ALTER TABLE chat_messages
    DROP COLUMN IF EXISTS answer_mode,
    DROP COLUMN IF EXISTS actual_provider,
    DROP COLUMN IF EXISTS actual_model,
    DROP COLUMN IF EXISTS fallback_reason,
    DROP COLUMN IF EXISTS attempt_count,
    DROP COLUMN IF EXISTS request_duration_ms;

-- ENUM values AI_GUIDANCE, OPENAI_UNVERIFIED, XKIRO_UNVERIFIED are intentionally
-- NOT removed. Removing ENUM values in PostgreSQL requires dropping and recreating
-- the type with a full table rewrite of every table that uses it. This is a
-- destructive operation. The values are harmless if unused by application code.
-- If removal is strictly required, follow this procedure:
--   1. ALTER TABLE chat_messages ALTER COLUMN answer_source_type TYPE VARCHAR(50);
--   2. DROP TYPE answer_source_type;
--   3. CREATE TYPE answer_source_type AS ENUM (...original five values...);
--   4. ALTER TABLE chat_messages ALTER COLUMN answer_source_type
--        TYPE answer_source_type USING answer_source_type::answer_source_type;
-- Step 4 will fail if any row contains 'AI_GUIDANCE', 'OPENAI_UNVERIFIED',
-- or 'XKIRO_UNVERIFIED'. Ensure all such rows are updated before running.
```

### D2. Equivalent Alembic migration (if Alembic is bootstrapped)

If the team decides to introduce Alembic, the equivalent migration file would be:

**File:** `backend/alembic/versions/002_ai_failover_columns.py`

```python
"""AI provider failover: ENUM extensions and new chat_messages columns.

Revision ID: 002_ai_failover
Revises: 001_initial  (assign the actual revision hash after alembic stamp)
Create Date: 2026-11-11

IMPORTANT — PostgreSQL ENUM transaction-safety:
    ALTER TYPE ... ADD VALUE is non-transactional on PostgreSQL < 14.
    Alembic wraps migrations in a transaction by default. To ensure the new
    ENUM values are committed before the subsequent ALTER TABLE uses them,
    this migration uses op.get_bind().execute() with individual statements
    and disables Alembic's transaction wrapper via transaction_per_migration.
    See: https://alembic.sqlalchemy.org/en/latest/ops.html#alembic.operations.Operations.execute
"""

from alembic import op
from sqlalchemy import text

# revision identifiers
revision = "002_ai_failover"
down_revision = "001_initial"  # replace with the actual stamped revision hash
branch_labels = None
depends_on = None

# Alembic transaction-per-migration must be disabled so ENUM ADD VALUE
# is committed before ALTER TABLE runs. Set in alembic/env.py:
#     context.configure(..., transaction_per_migration=False)
# Then this migration manages its own commit points via op.get_bind().


def upgrade() -> None:
    bind = op.get_bind()

    # Step 1: Add new ENUM values — each in its own implicit transaction commit.
    # In PostgreSQL, ALTER TYPE ADD VALUE takes effect only after the surrounding
    # transaction commits. We execute and commit between each ADD VALUE call.
    bind.execute(text("ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE'"))
    bind.execute(text("COMMIT"))
    bind.execute(text("ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED'"))
    bind.execute(text("COMMIT"))
    bind.execute(text("ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED'"))
    bind.execute(text("COMMIT"))

    # Step 2: Add new columns — idempotent via IF NOT EXISTS.
    bind.execute(text("""
        ALTER TABLE chat_messages
            ADD COLUMN IF NOT EXISTS answer_mode       VARCHAR(30)  NULL,
            ADD COLUMN IF NOT EXISTS actual_provider   VARCHAR(50)  NULL,
            ADD COLUMN IF NOT EXISTS actual_model      VARCHAR(100) NULL,
            ADD COLUMN IF NOT EXISTS fallback_reason   TEXT         NULL,
            ADD COLUMN IF NOT EXISTS attempt_count     INTEGER      NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS request_duration_ms INTEGER    NULL
    """))


def downgrade() -> None:
    bind = op.get_bind()

    # Remove columns (safe)
    bind.execute(text("""
        ALTER TABLE chat_messages
            DROP COLUMN IF EXISTS answer_mode,
            DROP COLUMN IF EXISTS actual_provider,
            DROP COLUMN IF EXISTS actual_model,
            DROP COLUMN IF EXISTS fallback_reason,
            DROP COLUMN IF EXISTS attempt_count,
            DROP COLUMN IF EXISTS request_duration_ms
    """))

    # ENUM values are NOT removed — see downgrade note in Section D1.
    # Downgrade of ENUM additions without dropping the type is intentionally
    # a no-op. The three new values become dead labels; application code
    # continues to work because it never writes those values pre-migration.
```

---

## Section E — Pre-Migration Compatibility Assessment

**Verdict: SAFE. The application will not crash before this migration is applied.**

### Evidence

Both services contain explicit safe-proxy mappings:

**`rag_service.py` — `_source_type_for_general_ai()`:**
```python
# OPENAI and XKIRO → SECONDARY_AI_FALLBACK (already in DB)
# GEMINI / OFFLINE_GROUNDED → GEMINI_UNVERIFIED (already in DB)
# UNAVAILABLE → NO_RELIABLE_INFORMATION (already in DB)
```

**`rag_service.py` — `resolve_source_type_hierarchy()`:**
```python
if provider_source in ("SECONDARY_AI_FALLBACK", "OPENAI", "XKIRO"):
    return "SECONDARY_AI_FALLBACK"
```

**`ai_provider_service.py`:** Returns internal labels (`"GEMINI"`, `"OPENAI"`, `"XKIRO"`) — never writes directly to `answer_source_type`. `rag_service.py` translates these before constructing `ChatMessage`.

### Post-Migration Mapping (requires ORM and API changes — Section G)

| Scenario | Pre-migration value | Post-migration value |
|----------|---------------------|----------------------|
| Gemini General AI | `GEMINI_UNVERIFIED` | `AI_GUIDANCE` (after code change) |
| OpenAI General AI | `SECONDARY_AI_FALLBACK` | `OPENAI_UNVERIFIED` (after code change) |
| xKiro General AI | `SECONDARY_AI_FALLBACK` | `XKIRO_UNVERIFIED` (after code change) |
| OpenAI College Knowledge | `SECONDARY_AI_FALLBACK` | `SECONDARY_AI_FALLBACK` (unchanged) |

---

## Section F — Security Confirmation

This migration:

| Check | Status |
|-------|--------|
| Does NOT disable RLS | ✅ Confirmed — no `ALTER TABLE ... DISABLE ROW LEVEL SECURITY` |
| Does NOT change RLS policies | ✅ Confirmed — no `DROP POLICY` or `CREATE POLICY` |
| Does NOT grant BYPASSRLS or SUPERUSER | ✅ Confirmed — no GRANT statements |
| Does NOT modify `knowledge_chunks` | ✅ Confirmed — only `chat_messages` and `answer_source_type` ENUM |
| Does NOT modify `ai_provider_events` | ✅ Confirmed |
| Does NOT touch college IDs, user roles, or memberships | ✅ Confirmed |
| Does NOT change embedding dimensions | ✅ Confirmed — `knowledge_chunks.embedding VECTOR(768)` unchanged |
| Does NOT execute live database writes | ✅ Confirmed — this is a read-only investigation report |

---

## Section G — ORM and API Changes Required After Migration

These changes are **not part of the migration** but are required before the new columns carry useful data.

### G1. `backend/app/models/chat.py` — Add six fields to `ChatMessage`

```python
# Add after model_used column:
answer_mode: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
actual_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
actual_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
attempt_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
request_duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
```

**Note:** Use `server_default="0"` on `attempt_count` to match the DB column default. Without it, SQLAlchemy will not set a value for pre-migration rows fetched from the ORM.

### G2. `backend/app/schemas/chat.py` — Extend `ChatMessageResponse`

```python
class ChatMessageResponse(BaseModel):
    # existing fields ...
    answer_mode: Optional[str] = None
    actual_provider: Optional[str] = None
    actual_model: Optional[str] = None
    fallback_reason: Optional[str] = None
    attempt_count: int = 0
    request_duration_ms: Optional[int] = None
```

### G3. `backend/app/api/v1/chat.py` — Pass new fields to `ChatMessage` constructor

In `send_chat_message()`, update the `assistant_msg = ChatMessage(...)` block:

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
    # New fields — only set after migration:
    answer_mode=rag_result.get("answer_mode"),
    actual_provider=rag_result.get("actual_provider"),
    actual_model=rag_result.get("actual_model"),
    fallback_reason=rag_result.get("fallback_reason"),
    attempt_count=rag_result.get("attempt_count", 0),
    request_duration_ms=rag_result.get("latency_ms"),  # rag_service doesn't return this yet
)
```

### G4. `backend/app/services/rag_service.py` — Switch to new ENUM values after migration

Update `_source_type_for_general_ai()`:

```python
def _source_type_for_general_ai(self, provider: str) -> str:
    if provider in ("OPENAI", "XKIRO", "SECONDARY_AI_FALLBACK"):
        # Post-migration: use specific values
        if provider == "OPENAI":
            return "OPENAI_UNVERIFIED"
        return "XKIRO_UNVERIFIED"
    if provider == "UNAVAILABLE":
        return "NO_RELIABLE_INFORMATION"
    # GEMINI or OFFLINE_GROUNDED → AI_GUIDANCE (post-migration)
    return "AI_GUIDANCE"
```

Also add `request_duration_ms` to the `answer_question()` return dict (from `ai_result.get("latency_ms")`).

### G5. Update the ORM `PG_ENUM` definition

After migration, update the `answer_source_type` column's `PG_ENUM(...)` call in `chat.py` to include the three new values:

```python
answer_source_type: Mapped[str] = mapped_column(
    PG_ENUM(
        "OFFICIAL_WEBSITE", "ADMIN_VERIFIED", "GEMINI_UNVERIFIED",
        "SECONDARY_AI_FALLBACK", "NO_RELIABLE_INFORMATION",
        "AI_GUIDANCE", "OPENAI_UNVERIFIED", "XKIRO_UNVERIFIED",
        name="answer_source_type", create_type=False
    ),
    default="NO_RELIABLE_INFORMATION",
    nullable=False,
)
```

### G6. Frontend TypeScript type unions

After migration and after the backend starts returning new values, update:

**`apps/user-frontend/src/services/chat-service.ts`** (line 47):
```typescript
answer_source_type: "OFFICIAL_WEBSITE" | "ADMIN_VERIFIED" | "GEMINI_UNVERIFIED" |
                   "SECONDARY_AI_FALLBACK" | "NO_RELIABLE_INFORMATION" |
                   "AI_GUIDANCE" | "OPENAI_UNVERIFIED" | "XKIRO_UNVERIFIED";
```

**`apps/user-frontend/src/components/chat/VerificationBadge.tsx`**: Add handling for `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED`. The existing default branch already renders a neutral badge for unrecognised values, so this is cosmetic only.

**`apps/admin-frontend/src/app/super-admin/.../page.tsx`**: The `badge_distribution` mock data object keys may need extending for the new values.

---

## Section H — Tests Needed

### H1. Pre-migration regression tests (run before applying migration)

```python
# tests/test_chat_message_insert.py

async def test_existing_enum_values_persist():
    """Existing five ENUM values can still be written and read back."""
    for value in ["OFFICIAL_WEBSITE", "ADMIN_VERIFIED", "GEMINI_UNVERIFIED",
                  "SECONDARY_AI_FALLBACK", "NO_RELIABLE_INFORMATION"]:
        msg = ChatMessage(session_id=..., sender_role="assistant",
                          message_text="test", answer_source_type=value, ...)
        # Insert and read back; assert answer_source_type == value

async def test_safe_proxy_mapping():
    """OpenAI/xKiro providers map to SECONDARY_AI_FALLBACK pre-migration."""
    result = rag_service._source_type_for_general_ai("OPENAI")
    assert result == "SECONDARY_AI_FALLBACK"
    result = rag_service._source_type_for_general_ai("XKIRO")
    assert result == "SECONDARY_AI_FALLBACK"
    result = rag_service._source_type_for_general_ai("GEMINI")
    assert result == "GEMINI_UNVERIFIED"

async def test_new_enum_values_not_in_db_do_not_crash():
    """RAG service does not write AI_GUIDANCE/OPENAI_UNVERIFIED/XKIRO_UNVERIFIED
    to DB before migration; pre-migration inserts succeed."""
    # Mock ai_provider_service to return provider="OPENAI"
    # Call rag_service.answer_question(...)
    # Assert returned answer_source_type == "SECONDARY_AI_FALLBACK"
    # Assert ChatMessage INSERT does not raise DataError
```

### H2. Post-migration tests (run after applying migration)

```python
async def test_new_enum_values_accepted():
    """New ENUM values can be written and read back after migration."""
    for value in ["AI_GUIDANCE", "OPENAI_UNVERIFIED", "XKIRO_UNVERIFIED"]:
        msg = ChatMessage(session_id=..., sender_role="assistant",
                          message_text="test", answer_source_type=value, ...)
        # Insert and read back; assert answer_source_type == value

async def test_new_columns_nullable():
    """New columns accept NULL for existing-row compatibility."""
    msg = ChatMessage(session_id=..., sender_role="assistant",
                      message_text="test", answer_source_type="GEMINI_UNVERIFIED",
                      answer_mode=None, actual_provider=None, ...)
    # Insert succeeds; all new columns are NULL

async def test_attempt_count_default():
    """attempt_count defaults to 0 when not set."""
    msg = ChatMessage(session_id=..., sender_role="assistant",
                      message_text="test", answer_source_type="GEMINI_UNVERIFIED")
    # Insert and read; assert msg.attempt_count == 0

async def test_full_new_fields_persisted():
    """All six new fields are correctly written and read when explicitly set."""
    msg = ChatMessage(...,
        answer_mode="GENERAL_AI",
        actual_provider="OPENAI",
        actual_model="gpt-4o-mini",
        fallback_reason="gemini_timeout",
        attempt_count=3,
        request_duration_ms=1240,
    )
    # Insert, fetch by ID, assert each field value matches

async def test_existing_rows_unaffected():
    """Rows inserted before migration have NULL for new columns (no data loss)."""
    # SELECT answer_mode, actual_provider FROM chat_messages
    # WHERE created_at < migration_timestamp
    # Assert all are NULL

async def test_openai_provider_emits_openai_unverified():
    """After code change: OpenAI provider → OPENAI_UNVERIFIED (post-migration)."""
    result = rag_service._source_type_for_general_ai("OPENAI")
    assert result == "OPENAI_UNVERIFIED"
```

---

## Section I — PostgreSQL ENUM Transaction-Safety Notes

PostgreSQL's `ALTER TYPE ... ADD VALUE` has specific transaction semantics that differ from normal DDL:

1. **Non-transactional in PostgreSQL < 12:** `ALTER TYPE ... ADD VALUE` cannot be executed inside a transaction block and have the new value be visible within that same transaction. The `IF NOT EXISTS` guard is available from PG 9.3+.

2. **PostgreSQL 12+:** The statement is allowed within a transaction block but the new value is not visible to queries within the same transaction until after `COMMIT`.

3. **Safe application approach:** Execute each `ALTER TYPE ... ADD VALUE` as an auto-committed statement (outside a `BEGIN`/`COMMIT` block), then proceed with the `ALTER TABLE` as a separate statement or transaction. The raw SQL file in Section D1 does this correctly.

4. **Alembic workaround:** Alembic wraps migrations in transactions by default. The Alembic file in Section D1 uses `op.get_bind().execute(text("COMMIT"))` after each `ADD VALUE` to force a commit within the migration, then continues with the column additions. This is the standard workaround. Alternatively, configure `transaction_per_migration=False` in `alembic/env.py`.

5. **Idempotency:** `IF NOT EXISTS` makes both the ENUM additions and the column additions idempotent. Running the migration twice will not error.

6. **Ordering constraint:** The `ALTER TABLE ... ADD COLUMN` statements must run after the `ALTER TYPE ... ADD VALUE` statements have committed. The migration file respects this order.

---

## Confirmation

**No live database writes occurred during this investigation.** All findings are derived exclusively from reading source files in the workspace. No SQL was executed, no database connection was opened, and no migration was applied.

---

*End of DBA Review Report*
