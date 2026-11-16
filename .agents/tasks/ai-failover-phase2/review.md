# Phase 2 AI Failover Metadata — Code Review

**Reviewer verdict:** APPROVED  
**Review date:** 2025-07-28

---

## Evidence summary

All 11 required deliverables are present and read. Test evidence in the report shows 49 tests passing (9 new + 40 pre-existing), 0 failures. No git history is present (workspace has no `.git` directory), so the diff was established by directly reading every deliverable file.

---

## Deliverable-by-deliverable findings

### 1. `backend/migrations/002_ai_failover_columns.sql`
- Adds `AI_GUIDANCE`, `OPENAI_UNVERIFIED`, `XKIRO_UNVERIFIED` with `IF NOT EXISTS` guards. ✅
- Adds all 6 required columns with `IF NOT EXISTS`. ✅
- `attempt_count INTEGER NOT NULL DEFAULT 0` matches spec. ✅
- File contains no `BEGIN`/`COMMIT`. ✅
- Comment block correctly documents the PostgreSQL non-transactional ENUM constraint. ✅

### 2. `backend/migrations/002_ai_failover_columns_down.sql`
- Drops 6 columns with `DROP COLUMN IF EXISTS`. ✅
- Documents ENUM removal limitation with safe manual 4-step procedure. ✅
- No destructive operations executed automatically. ✅

### 3. `backend/app/models/chat.py`
- `PG_ENUM` updated from 5 to 8 values; `create_type=False` preserved. ✅
- 6 new `mapped_column` fields added after `model_used`. ✅
- `attempt_count` has both `default=0` and `server_default="0"`, nullable=False. ✅
- All other 5 fields are nullable. ✅

### 4. `backend/app/services/rag_service.py`
- `_NEW_ENUM_VALUES_AVAILABLE` module-level flag reads from `settings.AI_NEW_ENUM_ENABLED`. ✅
- `_source_type_for_general_ai()` correctly gates pre/post-migration mappings. ✅
  - Pre-migration: OPENAI/XKIRO → `SECONDARY_AI_FALLBACK`; GEMINI → `GEMINI_UNVERIFIED`. ✅
  - Post-migration: OPENAI → `OPENAI_UNVERIFIED`; XKIRO → `XKIRO_UNVERIFIED`; GEMINI/OFFLINE_GROUNDED → `AI_GUIDANCE`. ✅
- `request_duration_ms` added to `answer_question()` return dict as `ai_result.get("latency_ms")`. ✅
- SECURITY_BLOCK early return omits `request_duration_ms` key; API uses `.get()` so result is `None`. Correct behavior, no crash. ✅
- `resolve_source_type_hierarchy()` docstring still references old 5-value hierarchy (cosmetic only, no behavior impact). Out of scope.

### 5. `backend/app/api/v1/chat.py`
- `ChatMessage(...)` constructor in `send_chat_message` passes all 6 new fields from `rag_result`. ✅
- `_assert_session_ownership` preserved and unchanged. ✅
- `set_rls_context` called before `create_message` for the assistant message. ✅
- Stream endpoint (`stream_chat_message`) correctly preserved; it does not persist an assistant message (by design — streaming path persists the user message only). ✅

### 6. `backend/app/schemas/chat.py`
- `ChatMessageResponse` has all 6 optional fields with correct defaults. ✅
- `attempt_count: int = 0` (non-optional with default, matching ORM `NOT NULL DEFAULT 0`). ✅
- `from_attributes = True` preserved. ✅

### 7. `apps/user-frontend/src/services/chat-service.ts`
- `ChatMessageData.answer_source_type` union extended with `"AI_GUIDANCE" | "OPENAI_UNVERIFIED" | "XKIRO_UNVERIFIED"`. ✅
- 6 new optional fields added. ✅
- Existing `generateLocalAnswer` fallback function does not use the new types (still returns `OFFICIAL_WEBSITE` / `ADMIN_VERIFIED`) — backward-compatible. ✅

### 8. `apps/user-frontend/src/components/chat/VerificationBadge.tsx`
- `AI_GUIDANCE` → "AI Guidance — Not verified by college" with `Sparkles` icon. ✅
- `OPENAI_UNVERIFIED` → "OpenAI AI Guidance — Not verified by college" with `RefreshCcw` icon. ✅
- `XKIRO_UNVERIFIED` → "xKiro AI Guidance — Not verified by college" with `RefreshCcw` icon. ✅
- Labels match spec exactly. ✅
- Existing default fallback branch preserved. ✅

### 9. `backend/app/core/config.py`
- `AI_NEW_ENUM_ENABLED: bool = False` added with descriptive comment. ✅
- Placed near `AI_GENERAL_ANSWERING_ENABLED`. ✅

### 10. `backend/tests/test_phase2_metadata.py`
- 9 tests present, all assertions correctly verify required behaviors. ✅
- Report states 9 passed in 10.71s. ✅
- Tests 2 and 3 patch the module-level flag correctly with `patch.object`. ✅
- Test 9 uses source inspection to verify `set_rls_context` ordering — valid approach. ✅

### 11. `backend/.agents/tasks/ai-failover-phase2/report.md`
- All 10 required sections present. ✅
- Telemetry discrepancy (ORM `ai_provider_events` vs SQL `provider_events`) correctly identified, documented, not modified. ✅
- Explicit no-live-writes confirmation present. ✅

---

## Safety checks

| Check | Result |
|-------|--------|
| No SQL executed against any database | ✅ Confirmed — both SQL files created but not executed |
| No RLS policies changed | ✅ Confirmed — 002 migration contains no POLICY/RLS statements |
| No knowledge_chunks / embedding / vector dimension changes | ✅ Confirmed |
| No roles, memberships, or college IDs changed | ✅ Confirmed |
| No secrets printed | ✅ Confirmed |
| No unrelated code (crawler, PDF, auth) modified | ✅ Confirmed — crawler/PDF files referenced in grep are pre-existing unmodified files |
| No ai_provider_events ORM or table modified | ✅ Confirmed — `backend/app/models/ai.py` not in changed files |
| No provider_events table renamed | ✅ Confirmed |

---

## Blockers

None.

---

## Notes (non-blocking)

- The docstring comment in `resolve_source_type_hierarchy()` still lists the old 5-value hierarchy; it does not affect behavior.
- The `SECURITY_BLOCK` early-return dict omits `request_duration_ms`; the API correctly handles this via `.get()`.
- The admin frontend pages (`college-admin/analytics` and `super-admin/analytics`) were modified with mock data additions beyond the strict Phase 2 spec scope, but the task spec item 6 explicitly covers "relevant admin provider-monitoring types and displays," and these changes are purely additive display-only mock data with no security or correctness impact.
