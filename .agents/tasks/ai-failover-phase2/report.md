# Phase 2 — AI Failover Metadata Implementation Report

**Status:** Complete — no live database writes or migrations executed.

---

## 1. Files Changed

| File | Reason |
|------|--------|
| `backend/migrations/002_ai_failover_columns.sql` | New — standalone SQL migration adding 3 ENUM values and 6 columns |
| `backend/migrations/002_ai_failover_columns_down.sql` | New — downgrade script (column drops only; ENUM removal documented as manual procedure) |
| `backend/app/models/chat.py` | Added 6 failover metadata fields to `ChatMessage`; expanded `PG_ENUM` to 8 values |
| `backend/app/services/rag_service.py` | Added `_NEW_ENUM_VALUES_AVAILABLE` feature flag; updated `_source_type_for_general_ai()`; added `request_duration_ms` to return dict |
| `backend/app/api/v1/chat.py` | Passes all 6 new fields to `ChatMessage(...)` constructor |
| `backend/app/schemas/chat.py` | Added 6 optional fields to `ChatMessageResponse` with defaults |
| `backend/app/core/config.py` | Added `AI_NEW_ENUM_ENABLED: bool = False` setting |
| `apps/user-frontend/src/services/chat-service.ts` | Extended `answer_source_type` union; added 6 optional metadata fields to `ChatMessageData` |
| `apps/user-frontend/src/components/chat/VerificationBadge.tsx` | Added cases for `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED` with amber styling |
| `apps/admin-frontend/src/app/college-admin/analytics/page.tsx` | Added 3 new ENUM values to mock data and badge distribution display tiles |
| `apps/admin-frontend/src/app/super-admin/analytics/page.tsx` | Added 3 new tier description cards to Citation Grounding Tier Distribution panel |
| `backend/tests/test_phase2_metadata.py` | New — 9 tests for all Phase 2 deliverables |

---

## 2. Migration SQL — 002_ai_failover_columns.sql

```sql
-- ==============================================================================
-- Migration 002 — AI Provider Failover: ENUM extensions + new columns
-- Target: chat_messages table, answer_source_type ENUM
-- Apply with: psql $DATABASE_URL -f 002_ai_failover_columns.sql
--
-- IMPORTANT — PostgreSQL ENUM non-transactional constraint:
--   ALTER TYPE ... ADD VALUE is NON-TRANSACTIONAL in PostgreSQL. This file
--   must be run STANDALONE (outside any BEGIN/COMMIT block) so each ALTER TYPE
--   auto-commits before the subsequent ALTER TABLE runs.
--   Safe: psql $DATABASE_URL -f 002_ai_failover_columns.sql
--   Unsafe: wrapping in BEGIN/COMMIT will cause "invalid input value for enum"
--   on PostgreSQL < 14.
-- ==============================================================================

ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED';

ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS answer_mode           VARCHAR(30)  NULL,
    ADD COLUMN IF NOT EXISTS actual_provider       VARCHAR(50)  NULL,
    ADD COLUMN IF NOT EXISTS actual_model          VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS fallback_reason       TEXT         NULL,
    ADD COLUMN IF NOT EXISTS attempt_count         INTEGER      NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS request_duration_ms   INTEGER      NULL;

-- Verification queries (read-only — uncomment after applying):
-- SELECT enum_range(NULL::answer_source_type);
-- SELECT column_name, data_type, is_nullable, column_default
--   FROM information_schema.columns
--   WHERE table_name = 'chat_messages'
--   ORDER BY ordinal_position;
```

---

## 3. Downgrade SQL — 002_ai_failover_columns_down.sql

```sql
-- WARNING: Removes the 6 new columns. ENUM values are intentionally NOT removed.
ALTER TABLE chat_messages
    DROP COLUMN IF EXISTS answer_mode,
    DROP COLUMN IF EXISTS actual_provider,
    DROP COLUMN IF EXISTS actual_model,
    DROP COLUMN IF EXISTS fallback_reason,
    DROP COLUMN IF EXISTS attempt_count,
    DROP COLUMN IF EXISTS request_duration_ms;

-- ENUM values AI_GUIDANCE, OPENAI_UNVERIFIED, XKIRO_UNVERIFIED are NOT removed.
-- PostgreSQL cannot remove ENUM values without dropping and recreating the type.
-- See 002_ai_failover_columns_down.sql for the manual 4-step procedure.
```

---

## 4. ORM and API Changes

### `backend/app/models/chat.py`
- `PG_ENUM` extended from 5 to 8 values: added `"AI_GUIDANCE"`, `"OPENAI_UNVERIFIED"`, `"XKIRO_UNVERIFIED"`. `create_type=False` preserved.
- 6 new mapped columns added after `model_used`:
  - `answer_mode: Mapped[Optional[str]]` — `String(30)`, nullable
  - `actual_provider: Mapped[Optional[str]]` — `String(50)`, nullable
  - `actual_model: Mapped[Optional[str]]` — `String(100)`, nullable
  - `fallback_reason: Mapped[Optional[str]]` — `Text`, nullable
  - `attempt_count: Mapped[int]` — `Integer`, `default=0`, `server_default="0"`, not null
  - `request_duration_ms: Mapped[Optional[int]]` — `Integer`, nullable

### `backend/app/services/rag_service.py`
- Added module-level `_NEW_ENUM_VALUES_AVAILABLE: bool = getattr(settings, 'AI_NEW_ENUM_ENABLED', False)` after imports.
- `_source_type_for_general_ai()` updated with feature-flag branching:
  - Pre-migration (flag False): OPENAI/XKIRO → `SECONDARY_AI_FALLBACK`; GEMINI → `GEMINI_UNVERIFIED`
  - Post-migration (flag True): OPENAI → `OPENAI_UNVERIFIED`; XKIRO → `XKIRO_UNVERIFIED`; GEMINI → `AI_GUIDANCE`
  - `UNAVAILABLE` → `NO_RELIABLE_INFORMATION` in both branches
- `answer_question()` return dict now includes `"request_duration_ms": ai_result.get("latency_ms")`.

### `backend/app/api/v1/chat.py`
- `ChatMessage(...)` constructor in `send_chat_message()` now passes all 6 new fields from `rag_result`.
- `_assert_session_ownership()` and all `set_rls_context` calls are unchanged.

### `backend/app/schemas/chat.py`
- `ChatMessageResponse` now includes 6 optional fields with safe defaults:
  ```python
  answer_mode: Optional[str] = None
  actual_provider: Optional[str] = None
  actual_model: Optional[str] = None
  fallback_reason: Optional[str] = None
  attempt_count: int = 0
  request_duration_ms: Optional[int] = None
  ```

### `backend/app/core/config.py`
- Added `AI_NEW_ENUM_ENABLED: bool = False` near `AI_GENERAL_ANSWERING_ENABLED`. Controls when new ENUM values are written to the database.

---

## 5. Frontend Changes

### `apps/user-frontend/src/services/chat-service.ts`
- `ChatMessageData.answer_source_type` union extended with `"AI_GUIDANCE" | "OPENAI_UNVERIFIED" | "XKIRO_UNVERIFIED"`.
- 6 new optional fields added: `answer_mode?`, `actual_provider?`, `actual_model?`, `fallback_reason?`, `attempt_count?`, `request_duration_ms?`.

### `apps/user-frontend/src/components/chat/VerificationBadge.tsx`
- `VerificationBadgeProps.sourceType` union extended with 3 new values.
- Three new display cases added with amber/yellow styling (`#F59E0B`):
  - `AI_GUIDANCE` → `<Sparkles>` icon + "AI Guidance — Not verified by college"
  - `OPENAI_UNVERIFIED` → `<RefreshCcw>` icon + "OpenAI AI Guidance — Not verified by college"
  - `XKIRO_UNVERIFIED` → `<RefreshCcw>` icon + "xKiro AI Guidance — Not verified by college"
- Existing default branch (`HelpCircle` / "No Verified Information Available") preserved as ultimate fallback.

### Admin frontend
- `apps/admin-frontend/src/app/college-admin/analytics/page.tsx`: Mock `badge_distribution` extended with `AI_GUIDANCE: 0`, `OPENAI_UNVERIFIED: 0`, `XKIRO_UNVERIFIED: 0`; 3 new display tiles added.
- `apps/admin-frontend/src/app/super-admin/analytics/page.tsx`: 3 new tier description cards added to Citation Grounding Tier Distribution section.
- `apps/admin-frontend/src/types/college-admin.ts`: `badge_distribution` is typed `Record<string, number>` — already accepts new keys without change.

---

## 6. Config Changes

| Setting | Default | Purpose |
|---------|---------|---------|
| `AI_NEW_ENUM_ENABLED` | `False` | Gates writing new ENUM values to the database. Set to `True` only after `002_ai_failover_columns.sql` is confirmed applied. |

---

## 7. Test Results

### Phase 2 tests — `tests/test_phase2_metadata.py`
```
9 passed in 10.71s
```
| Test | Result |
|------|--------|
| test_old_enum_values_still_valid | ✅ PASSED |
| test_safe_proxy_pre_migration | ✅ PASSED |
| test_new_enum_post_migration | ✅ PASSED |
| test_all_six_metadata_fields_persisted | ✅ PASSED |
| test_request_duration_ms_from_latency | ✅ PASSED |
| test_actual_provider_model_recorded_after_failover | ✅ PASSED |
| test_existing_chat_history_loads | ✅ PASSED |
| test_tenant_isolation_unaffected | ✅ PASSED |
| test_rls_insert_preserved | ✅ PASSED |

### Pre-existing tests — `tests/test_ai_answering.py`
```
32 passed in 13.79s
```

### Pre-existing tests — `tests/test_rag_security_and_citations.py`
```
5 passed in 8.79s
```

### Pre-existing tests — `tests/test_multi_tenant_isolation.py`
```
3 passed in 10.03s
```

**Total: 49 tests, 0 failures, 0 errors.**

---

## 8. Compatibility Matrix

| Scenario | Pre-migration (AI_NEW_ENUM_ENABLED=False) | Post-migration (AI_NEW_ENUM_ENABLED=True) |
|----------|------------------------------------------|------------------------------------------|
| Gemini General AI | `GEMINI_UNVERIFIED` | `AI_GUIDANCE` |
| OpenAI General AI | `SECONDARY_AI_FALLBACK` | `OPENAI_UNVERIFIED` |
| xKiro General AI | `SECONDARY_AI_FALLBACK` | `XKIRO_UNVERIFIED` |
| OFFICIAL_WEBSITE chunks | `OFFICIAL_WEBSITE` | `OFFICIAL_WEBSITE` (unchanged) |
| ADMIN_VERIFIED chunks | `ADMIN_VERIFIED` | `ADMIN_VERIFIED` (unchanged) |
| All providers fail | `NO_RELIABLE_INFORMATION` | `NO_RELIABLE_INFORMATION` (unchanged) |
| Existing rows in chat_messages | Load without error (new columns NULL/0) | Load without error |
| Old API clients (no new fields) | Unaffected (fields have defaults) | Unaffected |

---

## 9. Telemetry Table Discrepancy

### Finding
`backend/migrations/001_initial_schema.sql` creates a table named **`provider_events`** (Entity 19). The ORM model `AIProviderEvent` in `backend/app/models/ai.py` maps to **`ai_provider_events`** (`__tablename__ = "ai_provider_events"`). These two names differ.

### Impact
Every call to `ai_provider_service._log_telemetry()` attempts to INSERT into `ai_provider_events`. Since the actual table in the database is `provider_events`, these inserts fail with a "relation does not exist" error. The `except Exception` clause at line ~270 of `ai_provider_service.py` catches and logs the error silently:
```python
except Exception as exc:
    logger.warning("Failed to record AI telemetry event: %s", exc)
```
Consequence: **all AI telemetry is currently silently lost**. No crash, no user-visible error, but zero operational telemetry is being persisted.

### Proposed Fix (requires separate documented proposal — not executed here)
Two options:
1. **Rename the table** (migration): `ALTER TABLE provider_events RENAME TO ai_provider_events;`
2. **Change the ORM** (no migration needed): change `__tablename__ = "ai_provider_events"` to `__tablename__ = "provider_events"` in `backend/app/models/ai.py`.

Option 2 is simpler and reversible. Option 1 is cleaner long-term. Both require a separate migration and review cycle. Neither was executed in this phase.

---

## 10. Explicit Confirmation

**No live database writes or migrations were executed.**

- `002_ai_failover_columns.sql` was created but not executed.
- `002_ai_failover_columns_down.sql` was created but not executed.
- No Alembic commands were run.
- No connection to production Supabase was made for any writes.
- No RLS policies, roles, memberships, college IDs, embeddings, or knowledge_chunks were modified.
- No existing records were deleted or modified.
- No secrets or API keys were printed.
