# Phase 3A.2 — Live Supabase Connection Report

## Result

CONNECTION SUCCESSFUL using the application-role URL only.

This was a read-only verification using the repository's normal configuration mechanism (`backend/app/core/config.py` -> `Settings()` -> `settings.DATABASE_APP_ROLE_URL`).

## Safety controls applied

- `.env` was not modified.
- The application-role URL was used; the admin `DATABASE_URL` was not used as a fallback.
- No migrations, DDL, DML, or policy changes were executed.
- No secrets, passwords, or full connection strings were printed.
- Only safe SELECT queries were run.

## 1) Runtime config and environment loading

### Evidence

- `backend/app/core/config.py` loads the repository-level `.env` via `SettingsConfigDict(env_file=...)`.
- `settings.DATABASE_APP_ROLE_URL` was successfully resolved by the application configuration path.
- The configured app-role host was validated as a Supabase host and the username resolved to `college_app_user` without exposing the password.

### Sanitized status

- `.env` loaded: YES
- `DATABASE_APP_ROLE_URL` present: YES
- App-role URL used for live connection: YES
- Admin fallback used: NO

## 2) Live connection verification

### Sanitized connection metadata

- Host: `db.mefdzpqoestdwcyhnbxt.supabase.co`
- Database: `postgres`
- Role / session user: `college_app_user`

### Query results

1. `SELECT 1` -> `1`
2. `SELECT current_user, session_user` -> `college_app_user`, `college_app_user`
3. `SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user` ->
   - `rolname`: `college_app_user`
   - `rolsuper`: `false`
   - `rolbypassrls`: `false`

This confirms the live runtime role is a non-superuser, non-BYPASSRLS role and matches the intended app runtime identity.

## 3) RLS status from live catalog

The following tenant-owned tables were inspected in `pg_class` and showed RLS enabled:

- `chat_messages` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `chat_sessions` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `college_memberships` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `documents` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `extracted_facts` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `knowledge_chunks` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `knowledge_reviews` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `notification_logs` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `users` — `relrowsecurity = true`, `relforcerowsecurity = false`
- `website_pages` — `relrowsecurity = true`, `relforcerowsecurity = false`

This indicates that the application tables are protected by row-level security, with no forced row-level security flag set.

## 4) Live RLS policy inventory (sanitized)

The following live policy patterns were observed via `pg_policies` for the tenant-scoped tables:

- `chat_messages`
  - `p_chat_messages_super_admin` uses `is_platform_super_admin()`
  - `p_chat_messages_tenant` restricts access to rows where the session matches `chat_sessions.college_id = current_app_tenant()`
- `chat_sessions`
  - `p_chat_sessions_tenant` restricts access to `(college_id = current_app_tenant()) OR is_platform_super_admin()`
- `college_memberships`
  - read policy is permissive for membership lookup; write policy is scoped to tenant or super-admin
- `documents`
  - tenant isolation via `college_id = current_app_tenant()` or super-admin
- `extracted_facts`
  - `p_facts_super_admin_all` plus `p_facts_tenant_isolation` via `college_id = current_app_tenant()`
- `knowledge_chunks`
  - isolation via `college_id = current_app_tenant()`, with explicit public-published conditions and super-admin exception
- `knowledge_reviews`
  - super-admin exception plus isolation via matching `knowledge_chunks.college_id`
- `notification_logs`
  - super-admin exception plus tenant isolation via `college_id = current_app_tenant()` or null
- `users`
  - `SELECT` policy is open to general read, `UPDATE` is limited to the authenticated user or super-admin, `DELETE` is super-admin only
- `website_pages`
  - tenant isolation via `college_id = current_app_tenant()` or super-admin

## 5) Database identity and expected project match

The live connection resolved to the Supabase host:

- `db.mefdzpqoestdwcyhnbxt.supabase.co`

This corresponds to the active Supabase project configured for the repository and matches the app-role configuration in the project-level `.env` and `backend/app/core/config.py`.

## 6) Connection outcome

Status: PASS

A clean read-only connection to the actual Supabase database was successfully established using the application-role URL, and safe SELECT queries executed as expected.

## 7) What this confirms

- The repository's app configuration is loading correctly.
- The live runtime role is `college_app_user`.
- The live role is not a superuser and does not have `BYPASSRLS`.
- Tenant-owned tables are protected by RLS in the connected database.
- Policies are enforcing tenant scoping using `current_app_tenant()` and super-admin gating where required.

## 8) Remaining limitations

This phase only established a read-only connection and verified the immediate connection metadata, role, and RLS state. It does not prove all cross-tenant behaviors, worker context, or every policy edge case. For those, additional read-only queries and targeted application-level validation would still be required.

## 9) Final note

This report is based on actual live database evidence and not repository assumptions alone. The live connection is valid and the app-role database access is functioning as expected for the current Supabase project.
