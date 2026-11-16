# Schema Changes Required — AI Answering + Multi-Provider Failover

> **DBA Review Required Before Applying**
> Do NOT run these migrations automatically. Review and apply via controlled Alembic migration.

---

## 1. `answer_source_type` PostgreSQL ENUM — New Values Needed

The existing PostgreSQL `answer_source_type` ENUM (defined in `chat_messages` table) contains:

```sql
'OFFICIAL_WEBSITE', 'ADMIN_VERIFIED', 'GEMINI_UNVERIFIED', 'SECONDARY_AI_FALLBACK', 'NO_RELIABLE_INFORMATION'
```

The plan calls for three new values:
- `AI_GUIDANCE` — for answers in General AI mode (not college-specific)
- `OPENAI_UNVERIFIED` — for OpenAI-generated answers
- `XKIRO_UNVERIFIED` — for xKiro-generated answers

### Migration SQL

```sql
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'AI_GUIDANCE';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'OPENAI_UNVERIFIED';
ALTER TYPE answer_source_type ADD VALUE IF NOT EXISTS 'XKIRO_UNVERIFIED';
```

### Safe-proxy approach (used in code until migration runs)

Until this migration is applied, the Python code maps:
- General AI (GEMINI) → `GEMINI_UNVERIFIED`
- General AI (OPENAI) → `SECONDARY_AI_FALLBACK`
- General AI (XKIRO) → `SECONDARY_AI_FALLBACK`

---

## 2. `chat_messages` Table — New Optional Columns

The `ChatMessage` ORM model and DB table are missing these fields that the new
richer result dict includes. All columns are nullable/have defaults, so they can
be added without breaking existing rows.

| Column | Type | Default | Purpose |
|---|---|---|---|
| `answer_mode` | `VARCHAR(30)` | `NULL` | `COLLEGE_KNOWLEDGE`, `GENERAL_AI`, `MIXED` |
| `actual_provider` | `VARCHAR(50)` | `NULL` | Actual provider used: `GEMINI`, `OPENAI`, `XKIRO`, `OFFLINE_GROUNDED`, `UNAVAILABLE` |
| `actual_model` | `VARCHAR(100)` | `NULL` | Specific model identifier used (e.g. `gemini-1.5-flash`) |
| `fallback_reason` | `TEXT` | `NULL` | Why failover occurred (if any) |
| `attempt_count` | `INTEGER` | `0` | Total generation attempts made |
| `request_duration_ms` | `INTEGER` | `NULL` | End-to-end AI request duration in milliseconds |

### Migration SQL

```sql
ALTER TABLE chat_messages
    ADD COLUMN IF NOT EXISTS answer_mode VARCHAR(30) NULL,
    ADD COLUMN IF NOT EXISTS actual_provider VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS actual_model VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS fallback_reason TEXT NULL,
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS request_duration_ms INTEGER NULL;
```

### Code approach (pre-migration)

The richer fields are computed and returned in the in-memory service result dict.
They are NOT written to the ORM `ChatMessage` model until the migration adds the
columns. The existing columns (`model_used`, `answer_source_type`, `is_verified`,
`token_count`) carry forward the most critical information.

After migration, the ORM model and `chat.py` endpoint can be updated to persist
the additional columns.

---

## 3. No Embedding or Vector Schema Changes

Embedding dimensions, vector schemas, `knowledge_chunks` table, and all RLS
policies remain unchanged. No action required.

---

## 4. `ai_provider_events` Table — No Changes Required

The existing `ai_provider_events` table (id, config_id, event_type, latency_ms,
prompt_tokens, completion_tokens, error_message, created_at) is sufficient for
the new telemetry. No migration needed.
