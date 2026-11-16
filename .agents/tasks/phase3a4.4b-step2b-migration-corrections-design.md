# Phase 3A.4.4B — Step 2B: Migration Corrections Design and Security Review

## Executive decision: READY FOR STEP 3 REVIEW

The migration-chain blockers have a concrete, fail-closed correction design. The key changes are to defer four policies that depend on `auth.uid()` until signed application context is available, remove migration 019's temporary broad access in favor of a disconnected `NOLOGIN` runtime role, replace migration 018's placeholder credential and broad grants, and install final ownership/tenant policies only after migration 021's HMAC verifier exists.

This is a design deliverable only. All SQL below is illustrative and was **not executed**. No migration, application code, configuration, database, role, policy, credential, test fixture, or container was changed. “READY FOR STEP 3 REVIEW” is not approval to edit files, provision an environment, or run migrations.

## 1. Scope and evidence

This review uses the repository migrations 001–022, the application RLS-context setter and the previously recorded Step 2 / Step 2A findings. Relevant sources include [017_row_level_security_policies.sql](../../database/migrations/017_row_level_security_policies.sql), [018_create_application_role.sql](../../database/migrations/018_create_application_role.sql), [019_complete_rls_policies.sql](../../database/migrations/019_complete_rls_policies.sql), [020_revoke_anon_grants.sql](../../database/migrations/020_revoke_anon_grants.sql), [021_phase3a42_security_onboarding.sql](../../database/migrations/021_phase3a42_security_onboarding.sql), [022_minimize_auth_lookup.sql](../../database/migrations/022_minimize_auth_lookup.sql), [session.py](../../backend/app/database/session.py), [chat.py](../../backend/app/api/v1/chat.py), and [feedback.py](../../backend/app/api/v1/feedback.py).

The currently preserved local PostgreSQL container is not modified or used in this design phase. The Step 2 report records that the vanilla PostgreSQL image lacks Supabase's `auth.uid()`, `anon`, and `authenticated` objects; the Step 2A plan recommends a separate local Supabase-compatible stack for a later approved execution.

## 2. Migration dependency map

Execute only in numeric order after a separate approval and target verification. The “correction point” column describes proposed changes; it is not permission to make them.

| Migration | Dependency and purpose | Design correction / gate |
|---|---|---|
| 001 `extensions` | Required extensions and common enum types. | Verify extension versions and existing enum definitions on the selected disposable target. |
| 002 `create_colleges` | Colleges table; depends on 001. | No correction identified for this design. |
| 003 `create_users_and_memberships` | Users and college memberships; depends on 001–002. | No correction identified for this design. |
| 004 `create_website_tables` | Sources, crawl jobs/events, pages; depends on colleges and 001. | No correction identified for this design. |
| 005 `create_document_tables` | Documents, pages, paragraphs; depends on colleges/users and 001. | No correction identified for this design. |
| 006 `create_knowledge_tables` | Facts, vector chunks, reviews; depends on colleges/users and pgvector. | Verify pgvector compatibility before execution. |
| 007 `create_chat_tables` | Chat sessions and messages; depends on colleges/users. | Add a 24-hour visitor-token expiry field in an approved migration before final visitor policies are installed. |
| 008 `create_ai_and_audit_tables` | Provider configuration/events and audit logs; depends on colleges/users. | Review each runtime grant individually; audit records should be append-only. |
| 009 `create_feedback_and_support` | Feedback and tickets; depends on chat messages, colleges/users and status types. | Final policies must distinguish authenticated ownership from token-authorized anonymous submission and guest create-only tickets. |
| 010 `create_indexes` | Indexes for objects from 002–009. | Verify same-named indexes by definition, not name alone. |
| 011 `prepare_rls` | Initial RLS policies and unsigned GUC-reading helper functions; depends on tables from 002–009. | Keep the application disconnected. Migration 021 must replace unsigned helpers before the runtime role can log in. |
| 012 `college_onboarding_and_registration` | Registration, reviews, invitations, onboarding, notification logs and initial policies; depends on 002–003 and 011. | Verify destructive/data assumptions before any nonempty-database test. |
| 013 `crawler_engine` | Crawl additions; depends on 004. | Keep separate from migrations using new enum values. |
| 014 `document_processing_and_ocr` | Document/OCR additions; depends on 005. | Keep separate from migrations using new enum values. |
| 015 `knowledge_and_rag_enhancements` | Chunk metadata/index additions; depends on 006. | No additional correction identified. |
| 016 `analytics_support_and_multilingual` | Ticket replies, notifications, preferences and feedback fields; depends on 003, 007 and 009. | Establish exact column-level runtime grants for mutable ticket/notification fields. |
| 017 `row_level_security_policies` | Enables RLS and adds ticket, reply, notification, feedback, content, page/event and document policies; depends on 011 and 002–016. | Remove/defer its five `auth.uid()`-dependent policies. Keep affected tables RLS-enabled with no policy (default deny) until 021 installs signed-context policies. |
| 018 `create_application_role` | Creates `college_app_user` and currently grants broad privileges; depends on prior objects and helpers. | Create `NOLOGIN`, no password; correct target database; use individually reviewed grants; remove broad default function execution. |
| 019 `complete_rls_policies` | Adds user helper and policies for users, memberships, chat messages, facts, reviews, notification logs and chunks; depends on 017–018. | Remove broad `USING (true)` policies. Defer final user/membership/chat policies until signed helpers exist; app remains disconnected through 021. |
| 020 `revoke_anon_grants` | Revokes grants and defaults from Supabase roles; depends on roles supplied by Supabase. | Preserve all REVOKEs. Run on actual Supabase-compatible target; do not silently skip or synthesize the roles in a purported Supabase test. |
| 021 `phase3a42_security_onboarding` | Creates signed-context verifier and helpers, onboarding functions, hashes invitation tokens, and installs final user/membership/chat policies; depends on prior schema, role and pgcrypto. | Add final replacements for the four deferred policy groups; add visitor-token expiry and bind the visitor capability safely to the verified request. |
| 022 `minimize_auth_lookup` | Recreates the authentication lookup and restricts execution; depends on the function from 021 and role from 018. | Retain owner preservation, fixed search path and PUBLIC revocation; verify only fields used by login remain in its result. |

### Ordering and critical dependencies

1. Migrations 001–016 create the types, relations and columns used by RLS.
2. Migration 011 installs preliminary helpers and policies. Their GUC inputs are not authenticated; the application must not connect during this state.
3. Migration 017 must not call `auth.uid()` in a non-Supabase environment. The proposed correction defers its four affected policy sets rather than replacing `auth.uid()` with an unsigned GUC.
4. Migration 018 creates a non-login role. Migration 019 must not leave the temporary broad user/membership policies in place for any application session.
5. Migration 020 requires Supabase-provided `anon` and `authenticated` roles. Keep the statements; the recommended future target is a separate Supabase CLI local stack.
6. Migration 021 installs the HMAC verifier and signed helpers. Only after it commits can final application-identity policies safely be created.
7. Migration 021 currently does not replace the five policy expressions from 017. It must do so in the same transaction that installs the signed helpers and final policies.
8. Migration 022 must follow 021 because it replaces the lookup function created there.

## 3. Migration 017 — authenticated policy design

### Five `auth.uid()` dependencies

| Table / policy | Current `auth.uid()` use | Proposed identity source |
|---|---|---|
| `support_tickets` | Student ownership in the all-operations policy. | `public.current_app_user_id()` validated by the 021 HMAC verifier. |
| `support_ticket_replies` | Student ticket ownership in SELECT and ticket-owner check in INSERT. | Signed current user plus an RLS-checked parent ticket. |
| `in_app_notifications` | Notification owner in the all-operations policy. | Signed current user; college membership alone does not grant access to another person's notifications. |
| `feedback` | Feedback owner in the all-operations policy. | Signed user for authenticated submissions; verified visitor-token capability for anonymous submissions. |

Supabase `auth.uid()` reflects Supabase Auth identity. The backend uses custom application JWTs and its own signed database context; it does not use Supabase Auth for application login. Replacing `auth.uid()` with `current_setting('app.current_user_id')` directly would trust caller-settable state and is not acceptable. The application's [session.py](../../backend/app/database/session.py) signs user, tenant, admin and expiry values, and migration 021 verifies them.

### Safe installation sequence

In the corrected 017, keep RLS enabled but do not create the affected support, reply, notification and feedback policies. With no applicable policy, PostgreSQL denies access. In 021, after creating/replacing the signed helpers, atomically install the final per-operation policies below. Other 017 policies may remain, but the app stays disconnected until 021 has replaced unsigned context helpers.

### Final operation matrix

Predicates below are design contracts. They use signed helper results, not raw GUC values. All super-admin paths require `public.is_platform_super_admin()` to validate the signed context and account for a non-null verified user.

| Table / operation | `USING` (existing rows) | `WITH CHECK` (new row / resulting row) |
|---|---|---|
| `support_tickets` SELECT | Super-admin; or authenticated owner (`user_id = current_app_user_id()`); or active college admin for `college_id = current_app_tenant()`. | N/A |
| `support_tickets` INSERT | N/A | Super-admin; or authenticated creation with `user_id = current_app_user_id()` and `college_id = current_app_tenant()`; or anonymous guest creation only when signed context has no user, `user_id IS NULL`, tenant matches, and the tenant is approved and active. |
| `support_tickets` UPDATE | Super-admin or active college admin in the ticket's tenant. | Same authorization and tenant; do not permit changing ticket identity/tenant columns. Enforce mutable-column grants or an immutable-column trigger. Students and guests cannot update. |
| `support_tickets` DELETE | No policy. Physical deletion is denied; the application uses status changes. | N/A |
| `support_ticket_replies` SELECT | Super-admin; active college admin in parent ticket tenant; or authenticated ticket owner when `is_internal = FALSE`. A guest-created ticket has no guest read/reply capability. | N/A |
| `support_ticket_replies` INSERT | N/A | Staff may insert for a ticket in their authorized tenant with `sender_user_id = current_app_user_id()` and server-consistent role; only staff may set `is_internal`. A ticket owner may insert only a non-internal reply with themselves as sender. Guests may not reply. |
| `support_ticket_replies` UPDATE / DELETE | No policy. Replies are append-only. | No policy. |
| `in_app_notifications` SELECT | `user_id = current_app_user_id()` or verified super-admin. College-admin status alone does not expose all tenant users' notifications. | N/A |
| `in_app_notifications` INSERT | No direct table policy/grant; route through a narrowly scoped security-definer ticket-notification function. | Function derives recipient(s) and allowed event from an authorized ticket transition; it must not accept arbitrary recipient/message/token content. |
| `in_app_notifications` UPDATE | Owner only. | Owner still matches verified current user; grant only `is_read` for normal users. Administrative changes use a separately reviewed path. |
| `in_app_notifications` DELETE | No policy. | N/A |
| `feedback` SELECT | Super-admin or active college admin for the feedback tenant. | N/A |
| `feedback` INSERT, authenticated | N/A | Signed user owns the parent session, the message belongs to that session, and both rows match the signed tenant. Ignore/reject client-supplied tenant/user values that do not match. |
| `feedback` INSERT, anonymous | N/A | Signed context has no user; parent session has no user; session tenant matches; submitted message belongs to it; stored token hash matches the supplied bearer token; and the token has not expired. |
| `feedback` UPDATE / DELETE | No policy. Feedback is append-only. | No policy. |

Illustrative SQL only — not executed:

```sql
-- Defer these policies in 017; create final policies only after signed helpers
-- exist in 021. Separate per-command policies make INSERT checks explicit.
CREATE POLICY p_support_ticket_owner_read ON public.support_tickets
    FOR SELECT USING (
        public.is_platform_super_admin()
        OR user_id = public.current_app_user_id()
        OR (
            college_id = public.current_app_tenant()
            AND public.is_current_college_admin()
        )
    );

CREATE POLICY p_support_ticket_insert ON public.support_tickets
    FOR INSERT WITH CHECK (
        public.is_platform_super_admin()
        OR (
            public.current_app_user_id() IS NOT NULL
            AND user_id = public.current_app_user_id()
            AND college_id = public.current_app_tenant()
        )
        OR (
            public.current_app_user_id() IS NULL
            AND user_id IS NULL
            AND college_id = public.current_app_tenant()
            AND EXISTS (
                SELECT 1 FROM public.colleges AS c
                WHERE c.id = college_id
                  AND c.status = 'APPROVED'
                  AND c.is_active
            )
        )
    );
```

The snippet is incomplete by design: the college-admin UPDATE, replies, notification function and feedback policies must be added explicitly using the matrix; do not replace them with a permissive `FOR ALL` policy.

## 4. Migration 018 — role lifecycle and privileges

### Corrected role lifecycle

1. Create `college_app_user` as `NOLOGIN`, without a password, with `NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS`.
2. If the role already exists, fail if any required attribute, ownership or membership check is wrong; do not silently accept it.
3. Grant CONNECT to the actual selected database, not the literal database `postgres`. Use a safely quoted identifier, e.g. a `format('%I', current_database())` block.
4. Grant `USAGE` on `public`; explicitly revoke `CREATE` from the runtime role. Keep application objects owned by the migration/owner role.
5. Grant per-table DML and per-function EXECUTE from the reviewed allow-lists below. Do not grant all privileges on every table, sequence or function.
6. Remove broad default DML and EXECUTE grants. Default privileges are creator-role-specific; review each object creator and use explicit grants in later migrations.
7. Before enabling login, verify no ownership, privileged role membership, `BYPASSRLS`, superuser attribute, or unintended function/table grant. RLS tests can run via a trusted test harness using `SET ROLE` while the role remains `NOLOGIN`.
8. Only after security tests pass and a separate approval is given may an operator enable LOGIN and set a random test-only password through a protected interactive mechanism. No password is embedded in migration SQL or this report.

Illustrative SQL only — not executed:

```sql
CREATE ROLE college_app_user
    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;

DO $grant_target$
BEGIN
    EXECUTE format(
        'GRANT CONNECT ON DATABASE %I TO college_app_user',
        current_database()
    );
END
$grant_target$;

GRANT USAGE ON SCHEMA public TO college_app_user;
REVOKE CREATE ON SCHEMA public FROM college_app_user;
-- No blanket GRANT on ALL TABLES / ALL SEQUENCES / ALL FUNCTIONS.
```

The block is illustrative, not a complete role migration. It omits idempotent attribute validation and the object-by-object grants required below.

### Candidate object-level grant matrix

RLS policies authorize rows; SQL grants authorize operation classes. Both are required. The table below is a minimum design candidate based on the migration schema and inspected API/repository operations; finalize any operation against its actual call sites before implementation.

| Object | Candidate runtime grant | Guardrail |
|---|---|---|
| `colleges` | SELECT, UPDATE | Registration creation through the reviewed registration function; no direct DELETE. |
| `users` | SELECT, INSERT, UPDATE | Authentication lookup function for login; no direct DELETE; prohibit self role/active/verification changes. |
| `college_memberships` | SELECT, INSERT, UPDATE, DELETE | Writes restricted to approved super-admin path; tenant-scoped reads. |
| `website_sources` | SELECT, INSERT, UPDATE, DELETE | Tenant-scoped; delete only through admin workflow. |
| `crawl_jobs` | SELECT, INSERT, UPDATE | Tenant-scoped; no direct DELETE unless an audited worker path proves necessary. |
| `crawl_events` | SELECT, INSERT | Append-only; no UPDATE/DELETE. |
| `website_pages` | SELECT, INSERT, UPDATE, DELETE | Tenant-scoped crawler refresh/admin lifecycle. |
| `documents` | SELECT, INSERT, UPDATE, DELETE | Tenant-scoped; uploaded-object lifecycle must remain coordinated. |
| `document_pages` | SELECT, INSERT, UPDATE, DELETE | Access inherited from owning document; worker lifecycle. |
| `document_paragraphs` | SELECT, INSERT, UPDATE, DELETE | Access inherited from owning document; worker lifecycle. |
| `extracted_facts` | SELECT, INSERT, UPDATE, DELETE | Tenant-scoped; admin review/edit path. |
| `knowledge_chunks` | SELECT, INSERT, UPDATE, DELETE | Tenant-scoped; published reads must still require matching tenant. |
| `knowledge_reviews` | SELECT, INSERT | Append-only review history; no UPDATE/DELETE. |
| `chat_sessions` | SELECT, INSERT, UPDATE | Update for rename/soft-delete only; no physical DELETE. Restrict tenant, owner, token hash and creation fields from mutation. |
| `chat_messages` | SELECT, INSERT | Append-only; ownership inherited from session; no UPDATE/DELETE. |
| `ai_provider_configs` | SELECT, INSERT, UPDATE, DELETE | Restrict to super-admin management policies; never expose secrets in responses/logs. |
| `ai_provider_events` | SELECT, INSERT | Append-only event history. |
| `audit_logs` | SELECT, INSERT | Append-only; no UPDATE/DELETE. |
| `feedback` | SELECT, INSERT | Tenant/admin reporting reads; no UPDATE/DELETE. |
| `support_tickets` | SELECT, INSERT, UPDATE | UPDATE should be column-limited to workflow fields; no DELETE. |
| `support_ticket_replies` | SELECT, INSERT | Append-only; internal flag controlled by server-side staff authorization. |
| `in_app_notifications` | SELECT, UPDATE | UPDATE only `is_read`; no direct INSERT/DELETE. Use constrained function for notification creation. |
| `college_registrations` | SELECT, UPDATE | Public insertion/additional-info submission through reviewed definer functions; no direct INSERT/DELETE. Limit reviewable columns. |
| `registration_reviews` | SELECT, INSERT | Immutable history; no UPDATE/DELETE. |
| `college_admin_invitations` | SELECT, INSERT, UPDATE | Token hash only; no plaintext token reads; status transitions controlled by authorization. |
| `college_onboarding_progress` | SELECT, INSERT, UPDATE | Tenant-scoped; no direct DELETE. |
| `notification_logs` | SELECT, INSERT, UPDATE | Update only delivery-state/error fields; never store invitation tokens or credentials in content/metadata. |
| `auth_private.rls_context_keys` | No runtime privilege | Private schema/table inaccessible to runtime role and PUBLIC. |

Migration 001–022 defines UUID defaults and no application sequences. The proposed runtime sequence grant is therefore **none** unless a separate schema review discovers a required sequence. Do not keep migration 018's blanket `USAGE, SELECT ON ALL SEQUENCES` as a precaution.

### Function execution allow-list

Revoke PUBLIC execution from sensitive functions and grant only to the caller that needs them. Candidate runtime functions from 021–022 are:

- Signed RLS accessors: `current_app_user_id()`, `current_app_tenant()`, `is_platform_super_admin()`, `is_current_college_admin()`, and the constrained `user_belongs_to_tenant(uuid, uuid)`.
- Login: `lookup_user_by_email_for_auth(text)`.
- Invitation flow: `lookup_college_invitation_by_token(text)` and `accept_college_admin_invitation(text,text,text,uuid)`.
- Registration flow: `submit_public_college_registration(jsonb)`, `check_public_registration_availability(text,text)`, `get_public_registration_status(text)`, and `submit_public_registration_information(text,text,jsonb)`.
- A new notification function only if its authorization and content contract is approved.

Do not grant runtime execution on `auth_private.is_request_context_valid()` or trigger-only `prevent_user_privilege_self_change()`. Neither belongs in a blanket/default EXECUTE grant. Functions invoked by policies still need explicit execution rights for the runtime role, but private key lookup remains encapsulated in the definer verifier. Set a safe default search path and schema-qualify referenced objects.

`user_belongs_to_tenant` is security-definer and takes caller-supplied IDs. Its design should return false unless the signed caller is an authorized admin for the current tenant (or a verified super-admin), and the requested tenant is the caller's signed tenant (or super-admin path). This avoids turning a broadly executable helper into a cross-tenant membership-existence oracle.

## 5. Migrations 019–022 — policy transitions and function review

### Intermediate broad policies and replacements

| Migration 019 policy | Intermediate exposure | Migration 021 action / required correction |
|---|---|---|
| `p_users_read`, `FOR SELECT USING (true)` | Any database session with table SELECT can read all users. | 021 replaces with self, same-tenant admin and super-admin reads. Keep app disconnected through the transition. |
| `p_users_insert`, `WITH CHECK (true)` | Permits arbitrary user-row insertion, including privileged roles. | 021 replaces with self-only `STUDENT`, unverified, active registration; privileged account creation remains controlled. |
| `p_users_update` / `p_users_delete` | Self/super-admin update; super-admin delete. | 021 replaces user policies and adds the privilege-change trigger. Keep field-level grant and trigger checks. |
| `p_memberships_read`, `USING (true)` | Exposes all membership rows. | 021 replaces with self, same-tenant active college admin and super-admin read. |
| `p_memberships_write`, tenant/super-admin `FOR ALL` | Intermediate tenant-context writes; not enough to establish the actor's admin authorization. | 021 replaces with super-admin-only writes. Any planned college-admin membership writes need a separately constrained policy/operation. |
| `p_chat_messages_tenant` / `p_chat_messages_super_admin` | Tenant-only message checks, no session-user ownership or guest-token requirement. | 021 replaces with session ownership and guest-token checks. Add expiry and test session isolation. |
| Facts, reviews, notification-log and knowledge-chunk policies | Tenant-scoped policies, with chunks corrected from the broad NULL-tenant branch. | 021 does not replace these policies; they rely on helper names whose definitions are replaced by signed versions. Validate every policy against the signed helper contract. |
| Policies created in 017 for tickets, replies, notifications and feedback | Contain `auth.uid()` and broad `FOR ALL`/operation behavior. | 021 currently does not replace them. Add final signed-context policies as described in Section 3. |
| Other 011 policies | Use helper names created before signed-context verification. | Their behavior changes when 021 replaces the helper functions; app must remain disconnected until the replacement commits. |

The broad 019 policies are not a safe operating state. A `NOLOGIN` runtime role is necessary but not sufficient by itself: any other role capable of connecting as the application role or exercising these policies must remain disabled. Run the entire chain in a maintenance window on an isolated target, with no application, worker, PostgREST client or pooler connected.

### Migration 021 findings and visitor ownership

- The HMAC verifier validates user ID, tenant ID, super-admin flag, email-verification flag and a short expiry; the helper functions validate those signed values before returning identity.
- The visitor token is currently stored as a hash on `chat_sessions`, which is appropriate, but migration 021 adds no expiry column and its chat policies do not enforce a lifetime.
- The backend currently creates a random token and checks its hash for anonymous chat ownership. The agreed design is an absolute **24-hour lifetime** from session/token creation; at `expires_at <= statement_timestamp()` access is denied.
- Add `visitor_token_expires_at` (or an equivalent explicit timestamp), set it at session creation to creation time plus 24 hours, and require it in both session and message predicates. Do not extend expiry on activity.
- The raw visitor token is a bearer capability, not identity. Only its hash is stored; the application must supply the token only for the matching session. Add expiry and cross-session tests. A follow-up design may bind the token digest to an HMAC-signed visitor context; if adopted, change the backend setter and SQL verifier together. A raw tenant/user/admin GUC must never become trusted because a visitor token is present.
- Current `feedback.py` does not accept a visitor token or establish the required chat context. The anonymous-feedback rule chosen for this design is: anonymous feedback is allowed only with the matching, unexpired visitor token for the chat session whose message is rated. This requires a later approved application change.
- Guest support-ticket creation remains permitted, but is create-only: no anonymous ticket reads, updates, or replies. The route must validate the active college and establish signed tenant-only context before insert.
- Notification creation occurs after support-ticket transactions in the existing flow, while signed RLS GUCs are transaction-local. The application must keep related writes in one transaction or re-establish verified context before invoking the constrained notification function.

### Migration 022 authentication lookup

Migration 021 first creates `lookup_user_by_email_for_auth(text)` as `SETOF public.users`; migration 022 replaces it with a narrow table result and:

- Captures and restores the original owner when dropping/recreating the function.
- Uses `SECURITY DEFINER` and `SET search_path = pg_catalog`; referenced user table is schema-qualified.
- Revokes all execution from PUBLIC and grants EXECUTE to `college_app_user`.
- Returns `id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, and `is_active`.

The password hash is needed because this backend performs password verification locally; it must stay within the authentication service and never enter an API response, log or error. `role`, `is_verified` and `is_active` support authorization/account checks. `id` is needed for identity. Before finalizing the projection, trace whether `email` and `full_name` are consumed by the login path; remove either if not. No profile, token, membership, reset, or verification-secret fields should be returned. Keep the stable owner, fixed search path, PUBLIC revocation and explicit runtime grant. Do not use `CASCADE` when dropping the old function; fail if unexpected dependencies exist.

## 6. Illustrative SQL changes (not executed)

The following fragments show intended constraints, not migration-ready files:

```sql
-- Example anonymous feedback authorization contract. Implement only after
-- visitor-token expiry and application context wiring are approved.
CREATE POLICY p_feedback_guest_insert ON public.feedback
    FOR INSERT WITH CHECK (
        public.current_app_user_id() IS NULL
        AND college_id = public.current_app_tenant()
        AND EXISTS (
            SELECT 1
              FROM public.chat_messages AS message
              JOIN public.chat_sessions AS session
                ON session.id = message.session_id
             WHERE message.id = feedback.message_id
               AND session.id = feedback.session_id
               AND session.college_id = feedback.college_id
               AND session.user_id IS NULL
               AND session.visitor_token_hash IS NOT NULL
               AND session.visitor_token_expires_at > statement_timestamp()
               AND session.visitor_token_hash = encode(
                   public.digest(
                       COALESCE(current_setting('app.chat_visitor_token', true), ''),
                       'sha256'
                   ),
                   'hex'
               )
        )
    );
```

This fragment is illustrative only. It assumes the proposed expiry column and the existing bearer-token GUC; it does not itself solve application route context or token-signing changes. It must be tested with actual matching fixtures and reviewed for subquery RLS interactions before use.

## 7. Security test matrix

Use synthetic fixtures only. Every negative test must first prove its target row exists and is visible to an authorized control principal; an empty result without a matching fixture is not isolation evidence. Run as the `NOLOGIN` runtime role via a trusted harness, with each test setting a valid signed context. No test may use an owner/superuser connection for the operation under test.

### Fixtures

- Colleges `A` and `B`, both approved/active.
- Students `A1` and `A2` in college A, and `B1` in college B.
- College admins `AdminA` and `AdminB`; one verified platform `Super`.
- A ticket for each student plus one guest-created ticket in A; public and internal replies on each ticket.
- Notifications belonging to A1, A2 and B1.
- Authenticated and guest chat sessions in both colleges, each with at least one message and distinct random visitor tokens.
- Feedback rows linked to the above messages.
- All IDs, email addresses and contents are synthetic and non-production.

| Test | Acting context and operation | Expected positive / negative result |
|---|---|---|
| Tenant fixture control | Super reads both colleges' seeded tickets, sessions, messages, feedback and notifications. | Confirms all target fixtures exist before denial assertions. |
| Student own ticket | A1 selects their A ticket. | Own ticket is visible. |
| Same-college other user | A1 selects A2's ticket. | No row/permission; control query confirms ticket exists. |
| Cross-college ticket | A1 selects B1's ticket. | No row/permission; control query confirms ticket exists. |
| Student ticket mutation | A1 updates ticket status/assignee or deletes it. | Denied; student has no staff-update policy and no DELETE policy. |
| Guest ticket creation | Anonymous signed tenant-A context inserts a ticket with `user_id IS NULL`. | Insert succeeds only for active approved A. |
| Guest ticket read/update/reply | Same guest token/context attempts to read, update or reply to the guest ticket. | Denied; create-only rule. |
| Invalid/inactive guest tenant | Anonymous context uses B/unknown/inactive tenant for guest ticket insert. | Denied. |
| Ticket owner public reply | A1 reads and inserts a public reply on A1's ticket. | Allowed; sender identity must be A1. |
| Ticket internal reply | A1 reads an internal reply or inserts one. | Denied; existing internal fixture proves the read denial. |
| Other owner's reply | A1 reads or replies to A2's ticket. | Denied even though both belong to A. |
| Staff replies | AdminA reads internal/public replies and inserts an internal note on A's ticket. | Allowed; AdminA cannot access B's ticket/replies. |
| Super-admin ticket access | Super reads/updates A and B ticket workflows. | Allowed. Attempt to forge super-admin GUC without a valid signature is denied. |
| Ticket immutability | AdminA attempts to change ticket `id`, `college_id` or `user_id`. | Denied by column grants/immutable-field enforcement; existing row remains in A with its original owner. |
| Notification ownership | A1 reads own notification and attempts to read A2/B1 notifications. | Own allowed; both others denied despite A2 sharing the college. |
| Notification update | A1 changes `is_read`; then attempts to change recipient, college, message or title. | `is_read` update allowed; protected-field changes denied. |
| Notification creation | Student or admin attempts direct INSERT for an arbitrary recipient. | Denied; direct insert unavailable. The constrained ticket-event function only permits derived recipient/event combinations. |
| Authenticated feedback | A1 submits feedback for a message in A1's session. | Allowed. Attempt to spoof `user_id`, tenant, session or unrelated message is denied. |
| Anonymous feedback matching token | Guest submits feedback for a message in its own session with its own token before expiry. | Allowed. |
| Anonymous feedback wrong/missing token | Guest submits against the same message with no token or a different session's token. | Denied. |
| Anonymous feedback expired token | Matching guest token at/after the 24-hour expiry boundary. | Denied; test just before boundary succeeds. |
| Feedback reporting | AdminA reads A feedback; attempts B feedback. Super reads both. | AdminA sees only A; super sees both. |
| Authenticated chat ownership | A1 reads/updates own session and messages; attempts A2 and B1 sessions. | Own allowed; other users/tenants denied with populated fixtures. |
| Anonymous chat token isolation | Guest token T-A1 accesses its session; token T-A1 is used against another guest session. | Matching token allowed before expiry; cross-session token denied. |
| Visitor-token expiry | Guest accesses session/messages before 24h and at/after expiry. | Before boundary allowed; at/after boundary denied; activity does not extend expiry. |
| Message immutability | User attempts to update/delete a chat message or move it to another session. | Denied. |
| Forged signed context | Runtime sets arbitrary user, tenant, super-admin or email-verification GUC without valid HMAC, alters signed value, or replays expired context. | Helpers return NULL/FALSE and protected queries/writes fail closed. |
| Tenant membership helper | Runtime asks helper about another tenant or arbitrary user without authorized context. | False/denied; same-tenant authorized admin checks only its permitted tenant. |
| Runtime role attributes | Inspect role, ownership and memberships; attempt `SET ROLE` to privileged roles, `BYPASSRLS`, schema CREATE and private-key reads. | No privileged membership/ownership; role attributes false; all prohibited actions fail. |
| Function boundary | Runtime calls private verifier directly or invokes any non-allow-listed definer function. | Execute denied. Approved functions execute only for the intended purpose. |
| Authentication lookup projection | Runtime calls auth lookup and inspects returned column names/values. | Only verified login-required fields; no unrelated profile/security columns. Password hash stays inside login flow. |
| Login/password verification | Correct password, wrong password, inactive account, unverified account and role-bearing account fixtures exercise actual auth service. | Existing success/rejection and status/authorization behavior preserved; no hash in API, logs or errors. |
| Token/hash leakage | Capture API responses and application logs for invite/chat flows using synthetic tokens. | No plaintext invitation token/password hash in response/logs; chat token is returned only at intended session creation channel; database stores only its hash. |

## 8. Transaction, fail-fast and rollback strategy

1. Use a separate Supabase-compatible disposable stack, verified immediately before execution. Keep the existing PostgreSQL container/volume untouched.
2. Keep the application, workers, PostgREST client and connection pools disconnected for the entire chain. The runtime role is `NOLOGIN`; do not provision its password or signing key yet.
3. Execute migrations 001–020 in numeric order, one migration per transaction. For files without their own `BEGIN`/`COMMIT`, use a reviewed per-file transaction wrapper only if the complete SQL has been confirmed transaction-safe. Migrations 021 and 022 already contain explicit transactions; do not nest an outer transaction around them.
4. Use fail-fast execution (`ON_ERROR_STOP`) and record filename, start/end time, result and SQLSTATE. Stop immediately on the first failure; never skip or patch SQL in flight.
5. Do not run a single encompassing transaction over 001–022. It obscures the rollback boundary, and 021/022 already define their own transactions. Do not assume a `psql` session's autocommit gives file atomicity.
6. On failure, stop the chain, preserve the error/ledger and do not continue on a partial schema. Review the cause and obtain approval for any correction. For a fresh isolated validation, the safest reset is a separately approved disposable database/container rebuild, not ad hoc reversal of partially applied DDL.
7. Migration 021 has a transaction, but performs destructive drops of invitation plaintext and initial-admin password-hash columns after transforming invitation tokens. In any nonempty test fixture, require a backup/restore point and verify counts/hash uniqueness before commit. No production data is permitted.
8. After all migrations, verify functions, owners/search paths, grants, default privileges, RLS states/policies, and role attributes. Then run the security matrix while the role remains NOLOGIN. Only a separate approval can authorize test-only login credentials and signing-key provisioning.
9. No application connection or real email/database integration test is part of this design phase.

## 9. Risks and remaining implementation checks

- **Supabase equivalence:** a test-only shim for `auth`/roles is not an actual Supabase Auth/PostgREST compatibility test. The next phase should use a separate local Supabase CLI stack and identify its exact PostgreSQL/pgvector versions before approving the chain.
- **Policy behavior:** 021's current policy set omits the five 017 `auth.uid()` dependencies. Leaving them in place is incompatible with custom application identity even if Supabase supplies `auth.uid()`.
- **App/database alignment:** feedback needs visitor-token and tenant context; guest ticket creation needs signed tenant context; notification writes need context after transaction boundaries. These require companion application changes, not just SQL.
- **Visitor-token schema:** migration 021 has a hash but no expiry. The proposed 24-hour absolute expiry must be added and wired into token creation, chat session/message RLS, feedback RLS and tests.
- **Notification function:** a narrow event-based function is proposed, but allowed event types and recipient derivation must be confirmed against support-ticket flows. Do not grant unrestricted INSERT or accept arbitrary secret-bearing text.
- **Column-level permissions:** the candidate matrix is deliberately conservative, but Step 3 must trace every service/repository operation and validate RLS policy interactions before writing grants. In particular, prevent mutation of tenant, owner, visitor hash and append-only history fields.
- **Role boundary:** `NOINHERIT` alone is not sufficient if privileged role memberships or ownership exist. Validate membership paths and object ownership, and do not use the runtime role as a migration owner.
- **Lookup projection:** migration 022 currently returns seven fields. Trace actual login consumers to decide whether `email` and `full_name` are strictly required; never expose `hashed_password` outside local verification.
- **Transactions:** 001–020 lack file-wide transactions, while 021–022 contain explicit ones. Step 3 must review each file for transaction compatibility and use independent fail-fast boundaries.
- **Migration 021 data handling:** invitation-token hashing and dropped columns are not meaningfully validated on an empty database. A controlled synthetic-fixture test is required; no real records.
- **No SQL review can validate runtime outcome:** this design has not created a schema, run RLS tests, or established migration success.

## 10. Approval checklist for Step 3

- [ ] Approve a separate local Supabase-compatible test stack; explicitly distinguish it from the preserved vanilla PostgreSQL container.
- [ ] Approve the proposed changes to migrations 017, 018, 019, 021 and any necessary 022 projection adjustment.
- [ ] Approve the 24-hour absolute anonymous chat-token expiry and matching-token requirement for anonymous feedback.
- [ ] Approve guest support tickets as insert-only, with no anonymous read/update/reply operation.
- [ ] Approve the precise allowed notification event types, recipient derivation and narrow function interface.
- [ ] Approve application changes for feedback token/context, guest-ticket context and notification transaction/context handling.
- [ ] Complete repository call-site review for every table and function grant before implementing the candidate matrix.
- [ ] Approve a per-migration transaction/fail-fast runbook and recovery/rebuild process.
- [ ] Confirm synthetic-only fixtures and no production credentials/data.
- [ ] Keep runtime role NOLOGIN and do not provision any test signing key/password until migration/security validation is separately approved.
- [ ] Require explicit review of the diff and report before any SQL execution; execution is a later approval gate.

## 11. Changes and execution confirmation

- Project files changed in Step 2B: none, except this requested report.
- Migration files edited or executed: none.
- Application code, RLS, roles, credentials, signing keys or test data created/changed: none.
- Supabase or production connection: none.
- Existing `college-chatbot-pg17-test` container and volume: preserved and not modified.

## Final decision

**READY FOR STEP 3 REVIEW**

This decision means the correction design is ready for human review. It does not authorize implementation, environment provisioning, credential creation, or migration execution, and it does not claim that migrations or PostgreSQL security tests have passed.
