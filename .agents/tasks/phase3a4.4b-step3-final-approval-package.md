# Phase 3A.4.4B — Step 3: Final Implementation Approval Package

## Executive decision: READY FOR IMPLEMENTATION APPROVAL

The proposed implementation is specified below against the actual migrations and inspected backend call sites. It addresses the migration blockers, PostgreSQL's permissive-policy OR behavior, the existing signed-context implementation, the current visitor-token setter, and the database operations in repositories/services.

This is a planning-only approval package. No migration or application file was edited; no SQL was executed; no database, container, role, credential, key, or test data was created or changed. “READY FOR IMPLEMENTATION APPROVAL” means the design is ready for human review, not that implementation, provisioning, or migration execution is authorized.

## 1. Scope, evidence and decision boundary

The review read migrations 011–022 and the application authentication, tenant, chat, feedback, support, notification, document, crawler, knowledge, onboarding, audit and AI-provider persistence paths. Relevant files include:

- Migrations: [011_prepare_rls.sql](../../database/migrations/011_prepare_rls.sql), [012_college_onboarding_and_registration.sql](../../database/migrations/012_college_onboarding_and_registration.sql), [017_row_level_security_policies.sql](../../database/migrations/017_row_level_security_policies.sql), [018_create_application_role.sql](../../database/migrations/018_create_application_role.sql), [019_complete_rls_policies.sql](../../database/migrations/019_complete_rls_policies.sql), [020_revoke_anon_grants.sql](../../database/migrations/020_revoke_anon_grants.sql), [021_phase3a42_security_onboarding.sql](../../database/migrations/021_phase3a42_security_onboarding.sql), and [022_minimize_auth_lookup.sql](../../database/migrations/022_minimize_auth_lookup.sql).
- Context/auth: [session.py](../../backend/app/database/session.py), [auth.py](../../backend/app/dependencies/auth.py), [tenant.py](../../backend/app/dependencies/tenant.py), [college_admin.py](../../backend/app/api/v1/college_admin.py), [auth_service.py](../../backend/app/services/auth_service.py), and [user_repository.py](../../backend/app/repositories/user_repository.py).
- Feature paths: [chat.py](../../backend/app/api/v1/chat.py), [feedback.py](../../backend/app/api/v1/feedback.py), [support.py](../../backend/app/api/v1/support.py), [colleges.py](../../backend/app/api/v1/colleges.py), [users.py](../../backend/app/api/v1/users.py), [analytics.py](../../backend/app/api/v1/analytics.py), [support_service.py](../../backend/app/services/support_service.py), [in_app_notification_service.py](../../backend/app/services/in_app_notification_service.py), [document_service.py](../../backend/app/services/document_service.py), [crawler_service.py](../../backend/app/services/crawler_service.py), [knowledge_service.py](../../backend/app/services/knowledge_service.py), and [rag_service.py](../../backend/app/services/rag_service.py).

Step 2 reports that no migration was executed in the preserved vanilla PostgreSQL test container. No production/deployment migration history was inspected; do not infer that the migrations are unapplied anywhere else.

### Approval decision to make before editing

Confirm whether migrations 001–022 have been applied in **any** shared, staging, or production environment:

- If confirmed unapplied everywhere and released as a new chain, update the named migrations below and validate a fresh disposable Supabase-compatible stack.
- If any migration has been applied or released, do not rewrite that historical migration for deployment. Keep the approved history immutable and implement equivalent changes in a new forward migration (proposed `023_phase3a44_rls_context_privileges.sql`) after a separate compatibility/data review. The requested in-place edits may be used only in an explicitly disposable, resettable branch.

The migration-history answer is a required human approval item. Production access is not requested or permitted to obtain it.

## 2. Exact file/change list

### Migration files

| File | Exact proposed change |
|---|---|
| `017_row_level_security_policies.sql` | Keep RLS enabled on all current application tables. Stop creating policies that call `auth.uid()` for `support_tickets`, `support_ticket_replies`, `in_app_notifications`, and `feedback`; remove/defer those policy definitions so these tables remain default-deny until signed helpers exist. Enable RLS on `ai_provider_configs`, `ai_provider_events`, and `audit_logs`, which currently have no RLS in 011/017. Retain the tenant/content policy work only as a non-final stage; correct the `knowledge_chunks` NULL-tenant public-read branch or defer its final policy to 021. |
| `018_create_application_role.sql` | Create or validate `college_app_user` with `NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION`, no embedded password, and no ownership/membership in privileged roles. Replace the hard-coded CONNECT target `postgres` with the actual current database. Remove blanket grants on all tables/sequences/functions and broad default DML/EXECUTE. Apply the per-object grants in Section 5 only. Keep the role non-login throughout the migration chain. |
| `019_complete_rls_policies.sql` | Remove the unsigned `current_app_user_id()` implementation and its grant. Do not create the broad `p_users_read USING (true)`, `p_users_insert WITH CHECK (true)`, `p_memberships_read USING (true)`, or intermediate chat-message policies. Keep those RLS tables default-deny until 021. Retain/rewrite facts/reviews/chunks/log policies as explicit operation policies that depend on the helper names later replaced by signed versions. Replace the `notification_logs` tenant-or-NULL policy; `college_id IS NULL` must not make platform logs visible/writable to every tenant. |
| `021_phase3a42_security_onboarding.sql` | Replace HMAC context v1 with the signed context contract in Section 6, including a signed visitor-token digest and signed context purposes (`USER`, `VISITOR`, `WORKER`, and `PUBLIC_TICKET`). Add an absolute `visitor_token_expires_at` column and enforce the 24-hour lifetime. Install the final policies in Section 4, explicitly dropping all legacy permissive policies on those tables before creating replacements. Enable/secure AI and audit policies if not added in 017. Restrict security-definer search paths to `pg_catalog` where all referenced objects can be schema-qualified, preserve function ownership intentionally, and revoke PUBLIC execution. Retain token hashing and plaintext-token/password-column removal. |
| `022_minimize_auth_lookup.sql` | Keep the function result fields unchanged: actual `AuthUserLookup` and login callers consume `id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, and `is_active`. Retain original-owner preservation, `SECURITY DEFINER`, `SET search_path = pg_catalog`, fully qualified `public.users`, PUBLIC revocation, and explicit runtime-role EXECUTE. Add/retain a focused test that the function's result is exactly those seven columns and that the hash never leaves local verification. Do not use `CASCADE`. |

Migration 021 is not currently sufficient as the final-policy migration: it replaces user, membership and chat policies but does not replace the five `auth.uid()` references from 017, does not add visitor expiry, and does not sign the visitor capability. The exact omissions must be corrected before any runtime login is enabled.

### Backend files that must change with the SQL

| File | Required change |
|---|---|
| `backend/app/database/session.py` | Replace v1 signing payload with the agreed versioned payload and sign tenant, user, admin flag, email-verification flag, request expiry, context purpose, and visitor-token SHA-256 digest. Replace the raw `set_chat_visitor_token()` setter with a single operation that writes the digest and signature atomically. Add a dedicated worker-context setter/guard rather than treating every tenant-only session as an administrator. Refresh signed context after every explicit commit before further RLS-protected queries. |
| `backend/app/dependencies/tenant.py` | Replace the raw `set_config('app.current_college_id', ...)` with `set_rls_context()` after membership/tenant validation. The raw update currently invalidates the v1 signature. |
| `backend/app/api/v1/college_admin.py` | Replace all three raw `set_config('app.current_college_id', ...)` calls in `get_authorized_college()` with a fresh signed context after college authorization. Ensure context is re-established after commits if that request issues another database operation. |
| `backend/app/api/v1/colleges.py` | The current college-update endpoint accepts a college ID without validating College Admin membership and does not bind tenant context. Validate membership and bind signed context before update. The create endpoint directly inserts a `College` for any authenticated user, whereas the onboarding RPC creates a pending registration. Human approval must choose to route this endpoint through the registration workflow or restrict creation to Super Admin; do not preserve unrestricted direct tenant creation. |
| `backend/app/api/v1/users.py`, `backend/app/repositories/user_repository.py`, `backend/app/services/auth_service.py` | Match column grants to actual profile/preferences updates, Super Admin role/active updates, password reset and email verification. Avoid generic unrestricted UPDATE for privileged/password/token fields; use narrowly authorized functions for credential and administrative changes. `get_by_id()` and `list_users()` currently load full ORM rows, so assess explicit projections or document backend-only access to sensitive columns; response schemas must continue excluding password hashes and tokens. |
| `backend/app/dependencies/auth.py` | Keep authentication context user-only until tenant authorization has succeeded. Preserve the existing account-active check. Ensure any tenant context is installed only through the signed setter. |
| `backend/app/models/chat.py` | Add a non-null/nullable-as-designed `visitor_token_expires_at` field matching the approved migration and ensure guest session creation sets it once to creation time plus 24 hours. |
| `backend/app/api/v1/chat.py` | Bind visitor-token digest into the signed context before reads/writes; remove raw visitor GUC setting. Keep the plaintext token only in the initial anonymous session-creation response and only store its hash. Enforce expiry in the route as a UX guard as well as in RLS. |
| `backend/app/schemas/chat.py` | Preserve the one-time `visitor_token` output only for session creation; do not add the token/hash to read/update responses. Add expiry response information only if explicitly approved; it is not needed for authorization. |
| `backend/app/api/v1/feedback.py` and `backend/app/schemas/support_and_analytics.py` | Require an authorized tenant/session context. For anonymous feedback accept the existing chat visitor token in a request header, sign its digest, and ensure the message belongs to the same session and tenant. Require/provide a college identifier for context, then verify it against the row through RLS; reject mismatches. Authenticated feedback must match the verified user and the message's session. Set context before protected queries. Admin listing must establish the validated college/super-admin context before selecting feedback. |
| `backend/app/api/v1/support.py` | Validate that requested college is active and approved before guest create; set signed tenant context. For college-admin list/detail/reply/update, validate membership and bind the authorized tenant (the current query parameter alone is not authorization). For students, retain owner-only access. |
| `backend/app/services/support_service.py` | Preserve current business rules: guest ticket create only; students create/reply to own tickets and cannot write internal replies; staff updates status/priority/assignee/resolution. Remove mid-operation commits that clear transaction-local context before the follow-up notification. Use constrained notification events. |
| `backend/app/services/in_app_notification_service.py` | Replace unrestricted `create_notification(user_id,title,message,...)` direct insert with an event-specific database function that derives recipient/content from a ticket and verified actor. Keep direct owner-only reads and `is_read` updates; no direct arbitrary recipient insert. Avoid committing inside a parent ticket transaction. |
| `backend/app/services/document_service.py` | Pass the authenticated actor through the upload flow when it opens a tenant session. Use a user/admin context for request-triggered writes and a worker context for asynchronous processing. Preserve tenant scoping for processing and page replacement. |
| `backend/app/services/crawler_service.py`, `backend/app/services/knowledge_service.py`, `backend/app/tasks/document_tasks.py`, `backend/app/tasks/knowledge_tasks.py` | Use the approved signed worker context for background writes. Do not rely on unsigned tenant-only context or claim a worker identity from a request parameter. |
| `backend/app/repositories/registration_repository.py` and `backend/app/services/notification_service.py` | Route `notification_logs` writes through a constrained recording function or a separately approved signed service context. The caller must pass the transport-confirmed status; no secret-bearing email body/token is written to the log. Preserve the existing redacted invitation `audit_content`, which intentionally excludes the invitation URL/token. |
| `backend/app/repositories/college_admin_repository.py`, `backend/app/services/rag_service.py`, `backend/app/repositories/super_admin_repository.py` | Move college chat analytics to a database function/view returning only approved aggregates; keep raw user/guest message bodies owner-only (or super-admin-only). RAG may read only active `APPROVED`/`PUBLISHED` chunks in the same tenant; admin/worker lifecycle writes must be separately authorized. |
| `backend/app/api/v1/analytics.py` | Validate/resolve college membership and establish signed tenant context for college analytics. Its college-scoped routes currently resolve membership but do not set tenant context themselves. |

No application files are changed in this phase.

## 3. Before/after RLS policy inventory

All policies created without `AS RESTRICTIVE` are permissive in PostgreSQL. Multiple applicable permissive policies for the same command combine with **OR**, not AND. A new narrow policy does not constrain an old broad one. Every legacy permissive policy listed below must be explicitly dropped or deliberately retained with a documented equivalent predicate. Avoid `FOR ALL` for resources with different read/write rules; use command-specific policies and explicit `WITH CHECK`.

| Table | Existing policy/policies and issue | Required disposition and final intent |
|---|---|---|
| `colleges` | 011 `p_colleges_public_read` allows active/approved rows. 011 `p_colleges_admin_all` allows all commands when tenant matches or super-admin; it does not itself require an admin for writes. `colleges.py` also has direct create/update paths; update does not validate membership. | Retain approved/active SELECT for application college discovery. Replace `p_colleges_admin_all` with explicit SELECT/UPDATE policies requiring a validated college admin for tenant changes; INSERT only for super-admin or controlled registration workflow; no DELETE grant/policy unless a real endpoint is approved. Add a trigger or approved function to protect `status` and `is_active`, because college-admin and super-admin share one SQL role. |
| `users` | 019 `p_users_read` is `USING (true)`; `p_users_insert` is `WITH CHECK (true)`. `p_users_update` is self/super; `p_users_delete` is super. 021 drops/replaces these and creates `p_users_read`, `p_users_college_admin_read`, insert/update/delete. | Drop all 019 and any stale legacy policy names. Keep 021 self/super SELECT plus same-tenant admin SELECT; their permissive OR is acceptable because each branch is independently constrained. Keep student-self INSERT with exact role/active/verification checks; self profile UPDATE and super-admin updates with trigger protection. No DELETE policy/grant until an application delete operation exists. Restrict direct UPDATE to ordinary profile fields; use narrowly authorized functions/triggers for password/reset/verification and role/active changes. |
| `college_memberships` | 019 `p_memberships_read USING (true)` exposes all memberships; `p_memberships_write FOR ALL` lets any tenant-context session write. 021 replaces read/write. | Drop both broad policies. Keep self, same-tenant active-admin, super-admin SELECT. Writes super-admin only; invitation acceptance uses its constrained definer. No direct DELETE grant because no route/repository delete was found. |
| `website_sources` | 011 `p_sources_tenant_isolation FOR ALL`. | Replace with admin SELECT/INSERT/UPDATE/DELETE in validated tenant; crawler worker SELECT as needed. DELETE is required by `CollegeAdminRepository.delete_website_source`. |
| `crawl_jobs` | 011 `p_crawl_jobs_tenant_isolation FOR ALL`. | Replace with tenant admin SELECT/INSERT/UPDATE and signed worker SELECT/UPDATE; no direct DELETE. |
| `crawl_events` | 017 `p_events_tenant_isolation FOR ALL` via parent job. | Replace with tenant admin SELECT/INSERT and worker INSERT; no UPDATE/DELETE. Parent job must itself be visible/authorized. |
| `website_pages` | 017 `p_pages_tenant_isolation FOR ALL`. | Replace with admin/worker tenant SELECT/INSERT/UPDATE; no direct DELETE was found. |
| `documents` | 011 `p_documents_tenant_isolation FOR ALL`. | Replace with tenant-admin SELECT/INSERT/UPDATE/DELETE and worker SELECT/UPDATE. Delete is used by the admin repository; immutable college/owner columns must not be changed. |
| `document_pages` | 017 `p_doc_pages_tenant_isolation FOR ALL` via parent document. | Replace with admin SELECT, worker SELECT/INSERT/DELETE for reprocessing; do not permit cross-tenant parent reassignment. |
| `document_paragraphs` | RLS enabled by 011; no policy found. There is a model relationship with delete-orphan, but no direct paragraph insert/query path was found. | Keep default-deny and grant no access until actual ORM cascade SQL is traced. If document deletion requires child access, add only the exact required `SELECT`/`DELETE` policy/grant after an ORM test. |
| `extracted_facts` | 019 `p_facts_tenant_isolation FOR ALL` plus `p_facts_super_admin_all FOR ALL`; both permissive, so their predicates OR. | Replace with admin/worker SELECT/INSERT/UPDATE/DELETE limited to their operational workflow; super-admin access. No student access. |
| `knowledge_chunks` | 011 creates `p_chunks_tenant_isolation`; 017 drops/recreates it but its `current_app_tenant() IS NULL` branch allows published rows without a tenant. 019 drops/recreates it again. | Ensure the broad 017 version is never final. Final SELECT: super-admin, same-tenant admin/worker, or same-tenant active `APPROVED`/`PUBLISHED` chunk required by RAG. INSERT/UPDATE only authorized admin/worker; no DELETE grant absent a caller. |
| `knowledge_reviews` | 019 `p_reviews_tenant_isolation FOR ALL` plus `p_reviews_super_admin_all FOR ALL`; policies OR. | Keep admin SELECT/INSERT only and super-admin SELECT/INSERT. Append-only; no UPDATE/DELETE. Parent chunk tenant must match. |
| `chat_sessions` | 011 `p_chat_sessions_tenant FOR ALL` is tenant-only. 021 drops/replaces this named policy with user ownership, guest hash and super-admin predicates. | Drop/recreate explicit SELECT/INSERT/UPDATE policies. Add admin analytics only through an aggregate function, not raw conversation SELECT. Visitor reads/writes require a verified signed token digest, same-session hash and unexpired timestamp. No physical DELETE; API soft-deletes by `is_active`. |
| `chat_messages` | 019 creates `p_chat_messages_tenant FOR ALL` and `p_chat_messages_super_admin FOR ALL`. 021 replaces only the tenant policy; the super-admin policy remains and ORs with it. | Explicitly drop both legacy policies and install the final owner/visitor/super-admin policies; do not leave a second permissive policy accidentally broadening access. SELECT/INSERT only; no UPDATE/DELETE. |
| `feedback` | 017 `p_feedback_tenant_isolation FOR ALL` permits all tenant-context reads/writes and references `auth.uid()`. 021 does not replace it. | Drop it. SELECT admin/super-admin only. INSERT authenticated owner with same-session message, or anonymous matching visitor digest with same-session message and valid expiry. No UPDATE/DELETE. |
| `support_tickets` | 017 `p_support_tickets_tenant_isolation FOR ALL` ORs tenant, super-admin and `auth.uid()` ownership; no 021 replacement. | Drop it. SELECT owner/admin/super; INSERT authenticated owner or guest create-only for active approved college; UPDATE active college admin/super only; no DELETE. Restrict mutable columns to workflow fields. |
| `support_ticket_replies` | 017 SELECT policy `p_ticket_replies_student_read` and INSERT policy `p_ticket_replies_staff_insert`. The INSERT policy does not validate sender identity/role or `is_internal`; college context alone can insert. | Drop both and install exact SELECT/INSERT checks. Owner reads public replies only; staff in tenant and super read internal/public. Student inserts only own non-internal reply; staff sender must match signed actor; guests cannot read/reply. Append-only. |
| `in_app_notifications` | 017 `p_notifications_user_isolation FOR ALL` allows any row with matching user, tenant **or** super-admin; college context exposes all tenant notifications. No 021 replacement. | Drop it. Owner SELECT and `is_read`-only UPDATE; super-admin oversight if needed. No direct INSERT/DELETE. New event-specific function only. |
| `college_registrations` | 012 `p_registrations_super_admin FOR ALL`; public registration functions in 021 are security-definer. | Retain super-admin direct SELECT/UPDATE; no direct public INSERT. The registration RPC handles public intake/status without granting table access. Ensure function execution is explicit and PUBLIC revoked. |
| `registration_reviews` | 012 `p_reviews_super_admin FOR ALL`; public registration definer writes initial history. | Retain super-admin SELECT/INSERT, append-only. Definer functions write registration events; no direct UPDATE/DELETE. |
| `college_admin_invitations` | 012 `p_invitations_tenant_isolation FOR ALL` allows any signed tenant context, not necessarily an active admin. 021 has no replacement. | Replace with active college-admin/super-admin SELECT/INSERT/UPDATE policies. Acceptance remains through `accept_college_admin_invitation`; plaintext token is never a column. No direct DELETE. |
| `college_onboarding_progress` | 012 `p_onboarding_tenant_isolation FOR ALL` allows tenant-context access without requiring admin. | Replace with same-tenant active admin/super SELECT/INSERT/UPDATE. No DELETE. |
| `notification_logs` | 019 `p_notif_logs_tenant_isolation FOR ALL` permits matching tenant **or any `college_id IS NULL`**; `p_notif_logs_super_admin_all FOR ALL` is a second permissive policy. | Drop both. Super-admin SELECT only; INSERT via constrained recording function for approved notification events; no direct UPDATE/DELETE. Never persist invitation tokens or credentials. |
| `ai_provider_configs` | No RLS enablement/policy in 011–021; migration 018 grants blanket DML. | Enable RLS; super-admin SELECT/INSERT/UPDATE only. No DELETE grant because no delete repository/endpoint exists. Protect provider secrets at schema/API level. |
| `ai_provider_events` | No RLS enablement/policy; runtime records telemetry and super-admin analytics reads it. | Enable RLS; valid signed request/worker INSERT; super-admin SELECT; no UPDATE/DELETE. Avoid exposing prompt/message content in telemetry. |
| `audit_logs` | No RLS enablement/policy; super-admin routes/repositories read/insert, registration approval inserts. | Enable RLS; super-admin SELECT; INSERT only when signed actor matches event actor and is authorized. Append-only; no UPDATE/DELETE. |

### Permissive OR implications that must be tested

- The old `p_users_read USING (true)` would continue to expose all users even if a narrow self-read policy were added. It must be dropped.
- Old `p_memberships_read USING (true)` similarly defeats a new tenant-scoped membership policy.
- `p_chat_messages_super_admin` remains an independent OR branch unless explicitly dropped; the final migration drops both old message policies and creates one final policy set.
- `p_facts_*`, `p_reviews_*`, and `p_notif_logs_*` each currently have multiple permissive policies. The target does not rely on a new restrictive policy to cancel them; old policies are removed and final operations are explicit.
- `FOR ALL` grants the same row predicate to SELECT/INSERT/UPDATE/DELETE (with `USING` serving as the default check predicate when `WITH CHECK` is omitted). The final policy set is command-specific.
- Table privileges are evaluated before RLS. A policy cannot grant an operation absent SQL privilege; a SQL grant cannot override an RLS denial.

## 4. Final guest-ticket, feedback and notification contracts

### Guest support ticket

- Ticket creation is allowed for authenticated users and anonymous guests only for an active, approved college.
- The backend validates the requested college and installs signed tenant context before insert. `college_id` in the request is not authority by itself.
- Authenticated insert requires `user_id = verified current user` and tenant equality. Guest insert requires signed context purpose `PUBLIC_TICKET`, `user_id IS NULL`, matching active college, and validated request fields.
- Guest access is create-only: no list/detail, update, reply, or notification ownership token is added.
- Student reads/replies are owner-only; student reply is always public, regardless of request `is_internal`.
- College admin reads/replies/updates are restricted to the verified membership tenant; `SUPER_ADMIN` is separately verified.
- Staff may create internal replies; sender ID/role are derived from verified user state, not trusted from the request.
- Staff updates are limited to `status`, `priority`, `assigned_to_user_id`, `resolution_notes`, and `updated_at`; tenant, owner, ticket ID and creation data are immutable.
- Existing `/support` paths currently do not establish this tenant context. The route/service changes in Section 2 are required for database compatibility.

### Anonymous feedback

- Keep the selected behavior: feedback from an anonymous visitor requires the **same, unexpired 24-hour visitor token** that owns the matching chat session.
- The endpoint accepts the bearer token only in a header; it does not return it, store it, or log it.
- The endpoint establishes signed context with tenant, request purpose and the token digest. RLS verifies the message's session, session tenant, `user_id IS NULL`, saved hash, and expiry.
- Authenticated feedback requires signed user ownership of the session and message; caller-supplied `user_id`, `session_id` or `college_id` must match database relations.
- Feedback is append-only. Reports are visible to same-tenant college admins and super-admins, not ordinary students.
- Current `feedback.py` accepts no visitor-token header and does not set tenant context; this implementation dependency is a hard acceptance item.

### In-app notifications

- Current direct creation accepts arbitrary recipient, title, body, type and link, and commits independently. Replace it with a narrow `create_support_ticket_notification(ticket_id, event_type)` function.
- Approved event types: `TICKET_CREATED` only when the verified actor is the ticket owner; `STAFF_REPLY` only for an authorized same-tenant staff reply that is public and the ticket has a registered owner. A guest ticket has no recipient notification.
- The function derives the target user and college from the ticket and verified actor; it does not accept a caller-selected recipient or internal-note content. Use a fixed server-side template and ticket ID/link. Reject internal-reply notification.
- Insert the ticket/reply and notification in one transaction so the verified transaction-local context is still active. Direct INSERT privilege on `in_app_notifications` is revoked.
- Read is owner-only. UPDATE is limited to `is_read`; no direct delete.

### Email notification audit log

- Runtime call sites insert `NotificationLog` directly through `NotificationService`; super-admin API reads these logs. The new design routes inserts through a narrow `record_notification_delivery` function with approved event types and recipient/college checks against the associated registration/invitation record.
- Transport status is supplied only after the email transport returns its documented acceptance result; absent provider/rejection/timeout remains a failure state. Database code cannot independently prove provider delivery, so mocked/provider contract tests and a clear “accepted” semantic remain required.
- Store redacted audit content. The existing invitation dispatcher already provides audit text that omits its token-bearing URL; preserve that behavior. Never log the body or metadata containing invitation plaintext, SMTP credentials or complete sensitive links.
- Super-admin SELECT only; no direct app table INSERT/UPDATE/DELETE. The precise event allow-list and status-error retention must be explicitly approved.

## 5. Final role, table and function privilege matrix

### Role and schema boundary

| Principal/object | Required state |
|---|---|
| `college_app_user` | `NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS NOREPLICATION`; no password until separately approved after tests. |
| Runtime ownership/membership | Owns no application table/schema/function; has no membership path to `postgres`, `supabase_admin`, migration owner, or another privileged role. `NOINHERIT` is not a substitute for checking memberships and SET ROLE paths. |
| `public` schema | Runtime `USAGE`, no `CREATE`. Do not assume revoking CREATE removes existing object ownership. |
| `auth_private` schema/table | No runtime schema/table access; HMAC key read only by verifier owner. |
| Database CONNECT | Grant CONNECT to the actual test database. Audit ACLs on the selected Supabase database(s); PostgreSQL's default PUBLIC CONNECT may make the grant non-exclusive. Do not change shared database ACLs without explicit approval. |
| RLS/table ownership | Runtime role is not table owner and has no `BYPASSRLS`. Do not run request queries as a superuser/table owner. Test as `SET ROLE college_app_user` from a trusted harness. |
| Sequences | No sequence objects/defaults were found in migrations 001–022; grant no sequence privilege unless a later call-site/schema review finds an actual required sequence. |

### Table grants from actual repository/service operations

The following is the runtime SQL privilege allow-list before row policies. RLS narrows each operation by actor, tenant and request purpose. Fields that establish identity, tenant or append-only history need column-level restrictions or a controlled function.

| Table | Observed backend operations | Proposed runtime SQL privilege |
|---|---|---|
| `colleges` | SELECT, INSERT and UPDATE in tenant/super-admin repositories and registration approval. | SELECT; INSERT only through approved registration/super-admin function or policy; UPDATE only `name`, `official_domain`, `logo_url`, `contact_email`, and `contact_phone` for authorized tenant admins. Protect `status` and `is_active` with a signed-context trigger or narrow Super Admin function. No DELETE. |
| `users` | SELECT by ID/list, INSERT self-registration, UPDATE profile/preferences, password-reset/verification state, and Super Admin role/active fields. | SELECT, INSERT; direct UPDATE only `full_name`, `preferred_language`, and `preferences`. Password/reset/verification and role/active changes use dedicated verified functions/triggers. Keep auth lookup through its definer. No DELETE. |
| `college_memberships` | SELECT by user/pair/college; INSERT through membership and super-admin repositories; UPDATE assignment role/primary status. | SELECT, INSERT, UPDATE; no DELETE route found. Writes super-admin/approved invitation path only. |
| `website_sources` | SELECT, INSERT, UPDATE, DELETE in `CollegeAdminRepository`. | SELECT, INSERT, UPDATE, DELETE; tenant admin policies, worker SELECT. |
| `crawl_jobs` | SELECT, INSERT, UPDATE through admin repository and crawler. | SELECT, INSERT, UPDATE; tenant admin/worker policies; no DELETE. |
| `crawl_events` | SELECT/INSERT in admin repository and crawler. | SELECT, INSERT; append-only. |
| `website_pages` | SELECT/INSERT/UPDATE in crawler and knowledge ingestion. | SELECT, INSERT, UPDATE; no DELETE caller found. |
| `documents` | SELECT/INSERT/UPDATE/DELETE in admin repository and processing service. | SELECT, INSERT, UPDATE, DELETE; tenant/admin/worker policies; immutable college/document identity. |
| `document_pages` | SELECT/INSERT and DELETE-before-reprocess in document processing. | SELECT, INSERT, DELETE; tenant/worker policies; no UPDATE caller found. |
| `document_paragraphs` | No direct CRUD caller found; ORM delete-orphan relationship may touch rows on document deletion. | No grant by default. Confirm actual ORM cascade SQL before granting SELECT/DELETE. |
| `extracted_facts` | SELECT/INSERT/UPDATE/DELETE in college admin repository. | SELECT, INSERT, UPDATE, DELETE; active tenant admin only. |
| `knowledge_chunks` | SELECT/INSERT/UPDATE in ingestion, retrieval and review; no direct DELETE call found. | SELECT, INSERT, UPDATE; no DELETE. RAG reads only same-tenant active approved/published rows; writes admin/worker only. |
| `knowledge_reviews` | SELECT/INSERT in review/publish workflows. | SELECT, INSERT; append-only. |
| `chat_sessions` | SELECT/INSERT/UPDATE; DELETE endpoint is a soft-delete (`is_active = false`). | SELECT, INSERT, UPDATE; no DELETE. Restrict updates to title/is_active/approved metadata; tenant/user/token/expiry immutable. |
| `chat_messages` | SELECT/INSERT for conversation history, analytics and chat turns. | SELECT, INSERT; no UPDATE/DELETE. Raw content owner/guest-session scoped; aggregate-only college analytics. |
| `ai_provider_configs` | SELECT/INSERT/UPDATE in `SuperAdminRepository`; no delete endpoint found. | SELECT, INSERT, UPDATE; super-admin only; no DELETE. |
| `ai_provider_events` | INSERT telemetry and SELECT analytics. | SELECT, INSERT; super-admin SELECT, valid signed request/worker INSERT; no UPDATE/DELETE. |
| `audit_logs` | INSERT from registration approval/super-admin workflows; SELECT in super-admin repository. | SELECT, INSERT; super-admin read and actor-verified insert; append-only. |
| `feedback` | SELECT in admin reports; INSERT in chat feedback route. | SELECT, INSERT; admin/super read; same-session owner or visitor-token insert; no UPDATE/DELETE. |
| `support_tickets` | SELECT/INSERT/UPDATE; no physical delete path found. | SELECT, INSERT, UPDATE; owner/admin/super read, guest create-only, staff-only updates; no DELETE. |
| `support_ticket_replies` | SELECT/INSERT via support service. | SELECT, INSERT; owner/public versus staff/internal access; append-only. |
| `in_app_notifications` | SELECT, INSERT, UPDATE `is_read`; mark-read and mark-all-read. | SELECT, UPDATE on `is_read` only; no direct INSERT/DELETE. Insert through approved function. |
| `college_registrations` | SELECT/UPDATE in approval workflow; public intake and additional-info submission use 021 functions. | SELECT, UPDATE; super-admin direct operations; no direct INSERT/DELETE. |
| `registration_reviews` | SELECT/INSERT in registration workflow and onboarding functions. | SELECT, INSERT; append-only. |
| `college_admin_invitations` | SELECT/INSERT/UPDATE for list/create/revoke/resend; acceptance uses definer function. | SELECT, INSERT, UPDATE; no DELETE. Never SELECT plaintext token; hash excluded from API schema. |
| `college_onboarding_progress` | SELECT/INSERT/UPDATE in registration repository. | SELECT, INSERT, UPDATE; same-tenant active admin/super; no DELETE. |
| `notification_logs` | INSERT from notification service; SELECT in super-admin notification log endpoint; delivery status is set before insert. | SELECT, INSERT only through recorder function; super-admin read; no direct UPDATE/DELETE. |

This matrix intentionally does not grant DELETE to membership, user, chat, message, review, feedback, ticket, reply, notification, config, provider-event, audit or registration-history tables where no backend deletion call exists. Confirm ORM cascades and raw SQL during implementation before freezing the final SQL grants.

The shared `college_app_user` role cannot receive a column privilege “only when the current request is super-admin.” RLS controls rows, not which columns change. Do not retain a table-level `GRANT UPDATE` alongside the column grants: the table-level grant would nullify their intended restriction. For sensitive state transitions (college status/activation, user role/activation, password hash/reset token/email verification), use explicit signed-context checks in a trigger or narrow SECURITY DEFINER function; do not treat a column grant plus an HTTP route check as the database authorization boundary.

### Function execution allow-list

| Function group | Runtime execution |
|---|---|
| `public.current_app_user_id()`, `public.current_app_tenant()`, `public.is_platform_super_admin()`, `public.is_current_college_admin()` | Explicit EXECUTE for runtime role because policies use them; PUBLIC revoked. Helpers return only verified signed context. |
| `public.user_belongs_to_tenant(uuid,uuid)` | Prefer removal in favor of a scoped helper or retain only if it rejects arbitrary out-of-tenant probes and requires valid admin/super context. Explicit runtime EXECUTE only if a final policy uses it. |
| `auth_private.is_request_context_valid()` and key table | No runtime EXECUTE/table access. Invoked only by trusted helper functions. |
| `public.lookup_user_by_email_for_auth(text)` | Runtime EXECUTE only; PUBLIC revoked; owner/search path/projection as in 022. |
| User credential/admin transitions | Replace generic ORM updates for password/reset/verification and Super Admin role/active fields with narrowly scoped SECURITY DEFINER functions or signed-context-checked triggers. Runtime EXECUTE only for approved functions; PUBLIC revoked; fixed search path, explicit owner, and positive/negative authorization tests. Profile updates remain column-limited direct UPDATEs. |
| College protected fields | Protect `status` and `is_active` through a trigger checking verified Super Admin context or a narrow SECURITY DEFINER function. Do not rely on an HTTP role check or a shared-role column grant. |
| Invitation functions (`lookup_college_invitation_by_token`, `accept_college_admin_invitation`) | Runtime EXECUTE only; PUBLIC revoked; fixed path; token is an input capability and only its hash is stored. |
| Registration functions (`submit_public_college_registration`, `check_public_registration_availability`, `get_public_registration_status`, `submit_public_registration_information`) | Runtime EXECUTE only; PUBLIC/anon/authenticated revoked; expose only intended result fields. |
| `create_support_ticket_notification(uuid,text)` and `record_notification_delivery(...)` | Add only after the exact event contracts in Section 4 are approved; EXECUTE only for runtime role; fixed search path; no arbitrary recipient/secret payload. |
| Trigger-only `prevent_user_privilege_self_change()` | No direct app EXECUTE grant required; trigger invocation is installed by trusted migration owner. |
| Extension routines | Grant only exact routines required by final policies. Prefer the verified visitor-hash helper so RLS does not need to expose a raw visitor GUC or broadly grant digest functions. |

Remove migration 018's blanket/default `EXECUTE` grant. PostgreSQL's PUBLIC function execution default and owner-specific `ALTER DEFAULT PRIVILEGES` must be explicitly audited; a schema default changes only functions created by that specific owner.

## 6. Visitor-token authorization design

### Token lifecycle and signed context

1. On guest session creation, generate a cryptographically random one-time bearer token in the backend.
2. Store only lowercase hex SHA-256 of UTF-8 token in `chat_sessions.visitor_token_hash`; set `visitor_token_expires_at = created_at + 24 hours` once. Never slide/extend the expiry.
3. Return the plaintext token only in the new anonymous session creation response. Do not return it on history, message, update, feedback, support or list responses. Do not log request headers containing it.
4. On subsequent guest requests, read the token from `X-Chat-Visitor-Token`, hash it in the backend, and include only the digest in a signed HMAC context. Do not write plaintext token to a database setting or row.
5. HMAC version 2 payload must cover the normalized user ID, tenant ID, super-admin bit, email-verification bit, issued/expiry times, request purpose (`USER`, `VISITOR`, `WORKER`, or `PUBLIC_TICKET`), and visitor-token digest. Every context field used by policies must be signed. The database validates the signature and expiry before returning a helper result.
6. Expose a narrow `public.current_verified_visitor_token_hash()` helper that returns a digest only when the full context HMAC is valid and request purpose is `VISITOR`; PUBLIC is revoked and runtime receives explicit EXECUTE. The raw `app.chat_visitor_token` GUC is removed.
7. RLS compares the helper result with `chat_sessions.visitor_token_hash`, checks the requested session/message relationship and requires `visitor_token_expires_at > statement_timestamp()`. A token from another session fails even if the tenant matches. At the exact expiry boundary, access is denied.
8. Authenticated contexts have no visitor digest and cannot use guest rows as an alternate identity path. Super-admin access remains based on verified signed user/admin claims, not a token.
9. A direct SQL caller may set arbitrary GUCs but cannot mint a valid context signature without the key. A request purpose or digest written to a raw GUC without a matching signature returns NULL/denied.

The existing `set_chat_visitor_token()` does only `set_config('app.chat_visitor_token', token, true)` after `set_rls_context()` has signed a v1 payload that excludes the token. This is not sufficient. The token digest and all authorization context must be set atomically under one signature.

### Worker/request purpose

The current `tenant_session(college_id, user_id=None)` is used by crawlers and background document tasks, but can also be used by document upload initiated by an authenticated request. Signed context v2 must distinguish:

- `USER`: authenticated user; role and tenant derived from verified user/membership path.
- `VISITOR`: anonymous chat/feedback capability, with signed visitor digest.
- `WORKER`: only internal task code, bound to the tenant and task/object it is authorized to process.
- `PUBLIC_TICKET`: anonymous ticket creation only; it carries no user identity or row-read capability and is accepted only by the insert policy after the backend validates an active approved college.

Do not let an HTTP request select `WORKER` or pass arbitrary worker tenant identity. Worker context should be created by an internal API called only by trusted task dispatch after validating the job/document tenant. The upload path should carry the authenticated actor rather than mislabeling a user operation as a worker.

## 7. Backend/database compatibility requirements

- Recommended future target: a separate local Supabase CLI stack, verified for PostgreSQL and pgvector versions and Supabase `auth`, `anon`, and `authenticated` roles. Migration 020's REVOKEs remain present and are executed; they are not silently skipped.
- The app uses custom JWT auth, not Supabase Auth. Supabase `auth.uid()` must not be treated as application identity, even when it exists in the local stack.
- `get_current_user()` sets signed user context with no tenant. `require_college_tenant_access()` and college-admin `get_authorized_college()` currently change the tenant using raw `set_config`; after 021's HMAC replacement this invalidates the signature and makes `current_app_tenant()` return NULL. Both must call the signed setter after validating membership.
- `colleges.py` currently permits authenticated direct tenant insertion and an update by college ID without checking that a College Admin belongs to that tenant. The final schema must not authorize these paths by trusting the caller-supplied UUID; route through the approved registration flow or restrict creation to Super Admin, and validate membership for updates.
- `users.py` has actual preference updates and Super Admin role/active updates; `AuthService` updates password and verification state. A table-wide UPDATE grant plus only an HTTP role check is insufficient because all requests share `college_app_user`. Use column-specific profile updates and narrow trusted functions/triggers for credential/privilege fields.
- `get_optional_current_user()` returns `None` for anonymous callers without setting a context. Anonymous chat, feedback, public ticket and registration paths must explicitly establish only the approved context for their operation.
- `get_authorized_college()` establishes a tenant only after checking the College Admin membership; preserve that order. Super-admin context must remain separately verified.
- `support.py` currently does not establish a tenant for ticket list/detail/reply/update; college-admin supplied `college_id` is compared in service code but is not independently validated by a tenant dependency. Add route-level membership/context checks.
- `feedback.py` currently reads the message/session before setting matching tenant context and accepts no guest token. Set user/visitor context first and make RLS validate both relations.
- `SupportService` commits after ticket/reply changes and then calls notification creation, whose service separately commits. Transaction-local context is lost at those boundaries. Keep atomic work in one transaction or rebind verified context before each new transaction; event-specific function is preferred.
- `in_app_notification_service.create_notification()` currently accepts arbitrary recipient/content. Reduce the contract to event-specific support-ticket notifications and grant no direct INSERT.
- College analytics in `CollegeAdminRepository` and analytics routes count/query `ChatMessage` rows and join `ChatSession`; the current 021 user/guest policy does not give College Admins access, and analytics routes do not establish tenant context. Do not solve this by exposing raw message bodies to all college administrators. Use a verified aggregate function/view with only approved aggregates, establish signed tenant context, and keep direct chat content owner-scoped.
- RAG queries `KnowledgeChunk` for same-college active `PUBLISHED` chunks and fallback `APPROVED`/`PUBLISHED` active chunks. Student SELECT must be limited to those states and same signed tenant; ingestion/review writes require admin/worker context.
- `DocumentProcessingService`, `WebsiteCrawlerService`, `KnowledgeService` and task modules use tenant sessions. They need a signed worker context for background operations; document upload additionally needs actor propagation. Every explicit commit starts a new transaction and clears transaction-local context.
- `notification_logs` is read by the super-admin endpoint and directly inserted by `NotificationService`. A constrained recorder must accommodate public registration and invitation delivery while avoiding general tenant access and secret-bearing content.
- Invitation response schema excludes the invitation-token hash. Resend rotates hash and plaintext token is passed to the intended mail transport; preserve one-time delivery only and redacted audit content.
- Authentication lookup 022 returns seven actual fields. Current tests in `backend/tests/test_auth_lookup.py` verify the narrow mock result/login behavior and hash omission, but do not validate PostgreSQL function ownership, grants or catalog result shape.

## 8. Migration execution and recovery runbook

This is the future runbook for a separately approved phase; it is not executed here.

1. Confirm migration-history status through an approved non-production inventory. Decide in-place corrections versus a forward-only corrective migration as specified in Section 1.
2. Provision/approve a **separate disposable Supabase-compatible local stack**. Preserve `college-chatbot-pg17-test` and its volume. Do not connect to production or the Windows PostgreSQL service.
3. Positively verify container/stack identity, database, host binding, PostgreSQL version, pgvector version, extensions, roles, schemas and volume. Abort on any mismatch.
4. Ensure only the trusted migration administrator can connect. Runtime role is `NOLOGIN`; no backend, worker, PostgREST client or pooler is connected during migration.
5. Review each SQL file in full and establish transaction compatibility. Run one migration per transaction with fail-fast behavior. Migrations 021 and 022 contain their own transactions and must not be nested in an outer transaction. For migrations without explicit transactions, use a per-file transaction only after reviewing all statements.
6. Execute numeric order 001–022 (or approved forward-migration path), with `ON_ERROR_STOP`; capture filename, start/end time, status and SQLSTATE. Stop on first failure; never skip or patch SQL in flight.
7. Migration 021 includes irreversible/destructive operations: hash invitation tokens, set hash NOT NULL, drop plaintext `invitation_token`, and drop `college_registrations.initial_admin_password_hash`. For any nonempty test fixture, require a pre-migration snapshot and verify token count/hash uniqueness and no required password-hash dependency before commit. No production data is used.
8. Migration 022 drops/recreates a function to change result shape; preserve owner, do not use CASCADE, and fail if dependencies are unexpected.
9. On failure, stop and retain the ledger. Do not continue on a partial schema or run an improvised rollback. For disposable validation, use a separately approved fresh database/container rebuild; document cleanup, never automatically destroy resources.
10. After migration success, verify owners, search paths, PUBLIC/anon/authenticated grants, role attributes/memberships, default privileges, RLS enabled/forced state, every policy name/command/predicate, function grants, and absence of unexpected ownership/BYPASSRLS.
11. Run the synthetic security matrix in Section 9 with the runtime role (still NOLOGIN via test harness). Only after tests pass and separate approval may test-only credentials/key be provisioned and runtime login be enabled.

Do not put a migration-history table into the chain unless a separate migration plan explicitly approves one.

## 9. Complete security acceptance checklist

Use synthetic fixtures: two approved colleges A/B, two users in A (A1/A2), one user in B (B1), AdminA/AdminB, verified Super, one ticket/session/message/feedback/notification per relevant owner, public and internal replies, guest ticket, and separate guest sessions with distinct random tokens. For every denial, first prove the protected fixture exists through an authorized control context. Empty-result tests without matching fixtures do not demonstrate isolation.

| Area | Positive test | Negative test / expected denial |
|---|---|---|
| Auth lookup | Login function returns exactly seven consumed fields; valid password verifies; account status and role appear as before. | Attempt broad `SELECT` through function/API; no unrelated columns. Hash absent from API response, logs and errors. PUBLIC execution denied. |
| Users | A1 reads self; AdminA reads A1/A2; Super reads all. Self-registration creates only self `STUDENT`, active/unverified. | A1 cannot read A2/B1 or alter role/active/verified; arbitrary role insert denied; old `USING(true)` policy absent; no direct delete. |
| Memberships | User reads own membership; AdminA reads A memberships; Super creates/updates assignment. | A1 cannot enumerate memberships; AdminA cannot read/write B; membership user/college tampering denied; no direct delete. |
| Colleges | Anyone using app can read only active/approved college directory rows; authorized admin updates permitted profile fields. | Pending/suspended rows not publicly returned; college admin cannot change status/active/slug or other tenant; unauthorized insert/delete denied. |
| Website/crawler | AdminA manages A sources/jobs/pages; worker for A updates A job/page and writes events; AdminA reads A crawl history. | A worker/admin cannot operate on B job/source/page; student cannot write; event rows append-only. |
| Documents | AdminA creates/updates/deletes A document; worker replaces A pages; AdminA reads authorized page text. | Cross-college document/page access denied; tenant/document IDs immutable; unauthorized page delete/reassignment denied. ORM paragraph cascade is explicitly checked. |
| Facts/chunks/reviews | AdminA creates/edits/reviews/publishes A content; worker ingests A; student RAG reads same-tenant active APPROVED/PUBLISHED chunks. | Student cannot read pending/rejected/inactive chunks or write facts/chunks/reviews; AdminA cannot touch B; published content with NULL tenant is not visible. |
| Chat users | A1 reads/writes own session and messages; guest reads/writes only its own session before expiry; Super reads per policy. | A1 cannot read A2/B1; guest token T1 cannot read session T2; message cannot be moved; no update/delete of immutable message; context without HMAC denied. |
| Visitor context | Correct token digest signed for matching session succeeds before 24h; expiry timestamp is stored once and stable. | Raw `set_config` token/digest without valid HMAC, altered user/tenant/purpose/signature, empty token, cross-session token, and exact/after expiry all deny. Tenant/user/admin GUC forgery never authenticates. |
| Chat analytics | AdminA obtains approved aggregate counts for A via restricted function/view; Super obtains platform aggregate. | AdminA cannot select raw message text, prompts, or B aggregate; student cannot call admin aggregate. |
| Feedback | A1 submits for own message/session; guest submits with matching token for own message/session; AdminA reads A feedback; Super reads both. | Mismatched message/session/tenant/user, missing/wrong/expired visitor token, A1 reading A2/B feedback, and any update/delete are denied. |
| Support tickets | A1 sees own ticket and public replies; AdminA manages A tickets and reads internal notes; Super manages both. Guest submits a ticket to active A. | A1 cannot see A2/B tickets, internal replies, or write internal note; guest cannot list/read/update/reply; invalid/inactive college denied; tenant/owner transfer denied. |
| Notifications | User reads own and marks `is_read`; support ticket creation/public staff reply produces only the intended derived notification. | User cannot read another user's notification in same tenant or B; cannot modify recipient/body/college; no direct insert/delete; internal reply emits no student notification. |
| Registration/invitation | Public registration and status operations work through limited functions; super-admin reviews; invitation acceptance uses one-time hash and creates the intended membership. | Direct table access denied to anonymous/ordinary roles; expired/revoked/reused token fails; plaintext token/password hash absent from rows, responses and logs. |
| Email logs | Approved event recorder stores the transport outcome and redacted audit data; Super reads logs. | Other tenant cannot read logs; arbitrary event/recipient/status or secret-bearing content rejected; no direct table insert/update/delete. |
| AI config/telemetry | Super manages config; signed requests/workers append telemetry; Super reads metrics. | Non-super cannot read config/secrets or telemetry; no telemetry update/delete; request content not stored without approval. |
| Audit log | Super reads; authorized privileged action writes an actor-matched row. | Ordinary actor cannot forge another `actor_user_id`; all update/delete denied; no RLS bypass. |
| Runtime role | Catalog confirms no owner, no privileged membership, no SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS/REPLICATION; all needed explicit grants exist. | `SET ROLE` to privileged principal, `CREATE` in public, private-key read, non-allow-listed function execution and cross-tenant table access fail. |
| Supabase roles | `anon`/`authenticated` exist on the real local Supabase stack; 020 REVOKEs work and no application table DML grants remain. | Their direct PostgREST table/function attempts are denied; do not substitute a shim and call it Supabase validation. |

Existing mocked Python tests are useful for service behavior but do not prove RLS. Add/extend tests in `backend/tests/test_auth_lookup.py`, `test_multi_tenant_isolation.py`, `test_chat_rls_and_telemetry.py`, `test_analytics_and_support.py`, and `test_phase3a4_authz.py`; add a real PostgreSQL policy integration suite against the approved local Supabase stack. Do not run tests in this planning phase.

## 10. Explicit human approval decisions

Approve or amend each proposal before implementation:

1. Confirm migration deployment/history status and choose in-place updates only for an unreleased chain, otherwise an additive forward migration.
2. Approve 24-hour absolute anonymous chat-token expiry and require the matching token for anonymous feedback.
3. Confirm guest tickets remain create-only with no anonymous access token.
4. Approve HMAC v2 context fields and distinct `USER` / `VISITOR` / `WORKER` / `PUBLIC_TICKET` purposes; approve which task runner may mint a worker context and how it is tied to a tenant/job.
5. Approve aggregate-only college chat analytics instead of raw prompt/message visibility to college administrators.
6. Approve whether `/colleges` direct registration is routed through onboarding or restricted to Super Admin, and require tenant-membership validation for college updates.
7. Approve user column/function privileges for profile updates, password reset, email verification, and Super Admin role/active changes.
8. Confirm whether `EDITOR`/`VIEWER` membership roles need database/API capabilities distinct from the current `ADMIN` membership check.
9. Approve ticket notification events `TICKET_CREATED` (owner confirmation) and `STAFF_REPLY` (public replies only), with function-derived recipients and content.
10. Approve the `record_notification_delivery` event allow-list and audit retention/redaction rules for public registration, approval and invitations.
11. Approve the table/function privilege allow-list, including no deletion where no backend delete path exists, and require ORM cascade verification for `document_paragraphs`.
12. Approve the separate local Supabase CLI environment for later execution; preserve the existing vanilla PostgreSQL test container/volume.
13. Approve synthetic-only fixtures and the fail-fast per-migration runbook; require a fresh disposable rebuild after failure rather than continuing a partial chain.
14. Confirm no application login, runtime credentials, signing key or migration execution is authorized until a later explicit implementation/provisioning approval.

## 11. Completion and safety confirmation

- This report is the only file created for Step 3.
- No migration or application file was modified.
- No SQL/migration, test, database connection, role/policy change, container operation, credential/key creation, `.env` read, or seed script was run.
- No production Supabase, Windows PostgreSQL service, or existing data directory was accessed.
- No real AIT/RCTI data was used.

## Final decision

**READY FOR IMPLEMENTATION APPROVAL**

The specification is ready for human approval. The migration-history question and the explicit decisions in Section 10 must be answered before implementation; this status does not authorize file changes, environment provisioning, credential creation, or migration execution.
