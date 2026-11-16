# Phase 3A.3 — Live RLS Policy Security Review

## Objective

Review the exact live PostgreSQL RLS policy expressions for the tenant-owned tables and verify whether the live app-role security model still enforces tenant isolation in actual Supabase/PostgreSQL. This review was performed using a read-only app-role connection only.

## Safety status

- Read-only inspection only.
- No INSERT, UPDATE, DELETE, DDL, migrations, seeds, policy changes, ownership changes, or grants were executed.
- The application-role URL was used; no admin DB fallback was used.
- No credentials or connection secrets were printed.

## Executive summary

The live database is reachable via the intended app-role account and RLS is enabled on all tenant-owned tables. However, the live policy set is not fully tenant-safe for multi-tenant production behavior.

Two critical issues are currently visible from live evidence:

1. `users` has a permissive `SELECT true` policy, so app-role sessions can read all user rows in the database.
2. `college_memberships` also has `SELECT true`, so a tenant-scoped session can read membership rows outside its tenant if any such rows exist.
3. `chat_sessions` is scoped by `college_id` only; it does not enforce `user_id = current_app_user_id()`. A session can read other users' chat sessions within the same college.

Because of these issues, the live database is not production-ready for strict multi-tenant isolation and the final recommendation is NO-GO.

## 1. Live policy inventory

### Database identity and role

Read-only app-role connection succeeded as:

- `current_user = college_app_user`
- `session_user = college_app_user`
- `rolsuper = false`
- `rolbypassrls = false`

### Table RLS status

These tenant tables currently show RLS enabled:

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

### Exact live policy expressions from `pg_policies`

The exact expressions observed live were:

- `chat_messages`
  - `p_chat_messages_super_admin`: `is_platform_super_admin()`
  - `p_chat_messages_tenant`: `(EXISTS ( SELECT 1 FROM chat_sessions cs WHERE ((cs.id = chat_messages.session_id) AND (cs.college_id = current_app_tenant()))))`
- `chat_sessions`
  - `p_chat_sessions_tenant`: `((college_id = current_app_tenant()) OR is_platform_super_admin())`
- `college_memberships`
  - `p_memberships_read`: `true`
  - `p_memberships_write`: `((college_id = current_app_tenant()) OR is_platform_super_admin())`
- `documents`
  - `p_documents_tenant_isolation`: `((college_id = current_app_tenant()) OR is_platform_super_admin())`
- `extracted_facts`
  - `p_facts_super_admin_all`: `is_platform_super_admin()`
  - `p_facts_tenant_isolation`: `(college_id = current_app_tenant())`
- `knowledge_chunks`
  - `p_chunks_tenant_isolation`: `(is_platform_super_admin() OR (college_id = current_app_tenant()) OR ((status = 'PUBLISHED'::knowledge_status) AND (is_active = true) AND (current_app_tenant() IS NOT NULL) AND (college_id = current_app_tenant())))`
- `knowledge_reviews`
  - `p_reviews_super_admin_all`: `is_platform_super_admin()`
  - `p_reviews_tenant_isolation`: `(EXISTS ( SELECT 1 FROM knowledge_chunks kc WHERE ((kc.id = knowledge_reviews.chunk_id) AND (kc.college_id = current_app_tenant()))))`
- `notification_logs`
  - `p_notif_logs_super_admin_all`: `is_platform_super_admin()`
  - `p_notif_logs_tenant_isolation`: `((college_id = current_app_tenant()) OR (college_id IS NULL))`
- `users`
  - `p_users_delete`: `is_platform_super_admin()`
  - `p_users_insert`: `true`
  - `p_users_read`: `true`
  - `p_users_update`: `((id = current_app_user_id()) OR is_platform_super_admin())`
- `website_pages`
  - `p_pages_tenant_isolation`: `((college_id = current_app_tenant()) OR is_platform_super_admin())`

### Important combined behavior

PostgreSQL permissive RLS policies are combined with OR. That means the effective access for a table is the union of all active permissive policies.

This is critical for the findings below:

- `users` effective read policy is effectively `true`. That means any session that can access the table can read all rows, regardless of tenant or user.
- `college_memberships` effective read policy is effectively `true` for `SELECT`, regardless of tenant.
- `chat_sessions` is effectively tenant-scoped by `college_id` only, not user-scoped.
- `notification_logs` allows tenant-scoped reads plus global null-college rows.

## 2. Four concerning policies

### A. `users` general `SELECT` policy

Policy: `p_users_read` is `true`.

Who can read rows?
- Any app-role session with access to `users` can read all rows. This is not tenant-scoped.

Who can insert, update, and delete?
- Insert: `WITH CHECK true` — any app-role session can insert a new user row.
- Update: `((id = current_app_user_id()) OR is_platform_super_admin())`
- Delete: `is_platform_super_admin()` only

Can one college access another college's data?
- Yes, in principle, because the read policy is not tenant-bound.

Is the behavior intentional and safe?
- No. This is not safe for a multi-tenant system.

Live evidence:
- Under an AIT-scoped app-role session, `SELECT count(*) FROM users` returned `3`.
- `SELECT count(*) FROM users WHERE id IS NOT NULL AND id <> current_app_user_id()` returned `2`.
- This proves the app-role session can read other users in the same database outside the current user row.

Status: FAIL

### B. `college_memberships` permissive read policy

Policy: `p_memberships_read` is `true`.

Who can read rows?
- Any app-role session can read all membership rows in the table.

Who can insert, update, and delete?
- Insert/UPDATE/DELETE are gated only by `((college_id = current_app_tenant()) OR is_platform_super_admin())` for writes; read is unrestricted.

Can one college access another college's data?
- Yes, if any cross-college membership rows exist. The current live dataset does not contain such rows, but the policy itself still permits it.

Is the behavior intentional and safe?
- No. Membership records are highly sensitive tenant metadata and should not be globally readable.

Live evidence:
- Current live data: under an AIT-app context, `SELECT count(*) FROM college_memberships WHERE college_id = 'Rcti-id'` returned `0` because there were no current RCTI membership rows visible.
- That does not make the policy safe; it only means the current dataset is not exposing the leak at this moment.

Status: FAIL

### C. `knowledge_chunks` public-published conditions

Policy: `p_chunks_tenant_isolation` includes:

`(is_platform_super_admin() OR (college_id = current_app_tenant()) OR ((status = 'PUBLISHED'::knowledge_status) AND (is_active = true) AND (current_app_tenant() IS NOT NULL) AND (college_id = current_app_tenant())))`

Who can read rows?
- Super-admins can read all rows.
- Same-college rows are readable.
- Published rows that also match the current tenant are readable.

Who can insert, update, and delete?
- The policy also allows write operations where the row matches `is_platform_super_admin() OR (college_id = current_app_tenant())` in `WITH CHECK`.

Can one college access another college's data?
- Not via the published-and-same-college expression; a row must match the current college context.

Is the behavior intentional and safe?
- The policy is tenant-aware and currently safe as written for same-college published content.
- The `OR college_id = current_app_tenant()` makes the published condition effectively redundant, but it is not a cross-tenant leak.

Status: PASS

### D. `notification_logs` `college_id IS NULL` access

Policy: `((college_id = current_app_tenant()) OR (college_id IS NULL))`

Who can read rows?
- Same-college rows or rows with `college_id IS NULL`.

Who can insert, update, and delete?
- The same policy is used for ALL operations, so rows with `college_id IS NULL` are readable and writable under the same logic.

Can one college access another college's data?
- Not if the other college's rows have non-null `college_id`.
- However, any tenant-scoped session can read rows with `college_id IS NULL`, which may be intended for global/system-level logs but is a broader scope than tenant-specific logs.

Is the behavior intentional and safe?
- It is only safe if `college_id IS NULL` is intentionally reserved for global operational logs that are non-sensitive and not user-level data.
- Current live data had `0` such rows, so no leak was visible right now.

Status: PASS (current-data safe), but risk remains unless null-college rows are explicitly intended to be global operational logs.

## 3. Table ownership and privileges

Table owner inspection showed:

- All tenant-owned tables are owned by `postgres`.
- `college_app_user` does not own any protected table.
- `college_app_user` inherits direct table privileges via grants.

Granted privileges observed for the app-role connection:

- `college_app_user` has `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on the protected tenant tables.
- No runtime role had `rolbypassrls = true`.
- No protected table had `relforcerowsecurity = true`.

This means the design relies on standard table RLS enforcement rather than forced row security, which is acceptable when the app role is not an elevated admin and the policies are correct.

Status: PASS for ownership/privilege posture, but not enough to approve the policy set overall.

## 4. Tenant helper functions

Live helper function definitions:

- `current_app_tenant()`:
  - `RETURN NULLIF(current_setting('app.current_college_id', true), '')::UUID;`
- `current_app_user_id()`:
  - `RETURN NULLIF(current_setting('app.current_user_id', true), '')::UUID;`
- `is_platform_super_admin()`:
  - `RETURN COALESCE(current_setting('app.is_super_admin', true) = 'true', FALSE);`

These are safe in design because:

- Missing tenant context returns `NULL` for `current_app_tenant()` and `current_app_user_id()`.
- `is_platform_super_admin()` resolves to `FALSE` when the setting is absent or invalid.
- The functions do not trust client input as a privileged override; they read transaction-local settings only.
- No `search_path` or `SECURITY DEFINER` pattern was observed in the live definitions.

Status: PASS

## 5. Read-only isolation checks

### AIT cannot read RCTI records

Query used: set `app.current_college_id = AIT` and then read rows where `college_id = RCTI` on `documents`, `chat_sessions`, `knowledge_chunks`, and `website_pages`.

Evidence:
- `documents`: `0`
- `chat_sessions`: `0`
- `knowledge_chunks`: `0`
- `website_pages`: `0`

Status: PASS

### RCTI cannot read AIT records

Same test reversed with `app.current_college_id = RCTI` and AIT-specific college rows.

Evidence:
- `documents`: `0`
- `chat_sessions`: `0`
- `knowledge_chunks`: `0`
- `website_pages`: `0`

Status: PASS

### Missing tenant context does not expose tenant-owned records

Query: clear the tenant GUC and read tenant-owned tables where `college_id IS NOT NULL`.

Evidence:
- `documents`: `0`
- `chat_sessions`: `0`
- `knowledge_chunks`: `0`
- `website_pages`: `0`

Status: PASS

### User cannot access another user's chat session

Live policy for `chat_sessions` is:

`((college_id = current_app_tenant()) OR is_platform_super_admin())`

This does not include `user_id = current_app_user_id()`.

Live evidence under an AIT app-user context:
- `SELECT count(*) FROM chat_sessions` returned `18`
- `SELECT count(*) FROM chat_sessions WHERE user_id IS NOT NULL AND user_id <> current_app_user_id()` returned `17`
- `SELECT user_id, count(*) FROM chat_sessions WHERE user_id IS NOT NULL GROUP BY user_id` showed a single `user_id` owning `17` rows.

This proves the database does not enforce per-user access to `chat_sessions` within the same college.

Status: FAIL

### Published knowledge retrieval remains tenant-scoped

Live evaluation of `knowledge_chunks` with same-college published context is tenant-scoped and returned no cross-tenant rows.

Status: PASS

## 6. Final security verdict

### Check status summary

| Check | Status |
| --- | --- |
| Live app-role connection success | PASS |
| `college_app_user` is runtime role | PASS |
| `rolsuper = false` | PASS |
| `rolbypassrls = false` | PASS |
| RLS enabled on tenant tables | PASS |
| `users` read policy safe | FAIL |
| `college_memberships` read policy safe | FAIL |
| `knowledge_chunks` published access safe | PASS |
| `notification_logs` null-college access safe | PASS (current data only) |
| AIT cannot read RCTI records | PASS |
| RCTI cannot read AIT records | PASS |
| Missing tenant context hides tenant data | PASS |
| User cannot access another user’s chat session | FAIL |
| Published knowledge retrieval remains tenant-scoped | PASS |
| Final production recommendation | NO-GO |

## 7. Critical risks identified

1. `users` has a global SELECT policy. This is a direct cross-user data exposure issue.
2. `college_memberships` has a global SELECT policy. This is a direct cross-college data exposure risk.
3. `chat_sessions` is only college-scoped and not user-scoped, so one user within a college can read another user’s chat sessions.
4. These issues are visible in the live database, not just in the repository code.

## 8. Final GO / NO-GO recommendation

NO-GO for production approval.

Reason:
- The live app-role connection is valid and RLS is active.
- Cross-tenant data isolation is working for AIT/RCTI test data in several core tables.
- However, the policy set still allows global reads for `users` and `college_memberships`, and `chat_sessions` is not user-specific.
- Those are material multi-tenant security issues and must be fixed before any provider failover or production rollout.

This review does not claim production readiness. The live database proves the app-role path works, but the live policy implementation still fails the strict tenant-isolation requirement for production.
