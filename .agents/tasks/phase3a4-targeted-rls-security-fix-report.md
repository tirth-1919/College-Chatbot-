# Phase 3A.4 — Targeted RLS Security Fix Report

## Executive decision

**NO-GO for production approval.** Repository changes and the proposed SQL patch are prepared, and focused unit tests pass. However, the SQL has not been run against an isolated PostgreSQL database, so policy behavior, helper-function ownership/grants, and database-backed registration/chat flows remain unverified. Do not deploy the code or apply the SQL to production based on mocked tests alone.

The latest available live evidence is the read-only Phase 3A.3 audit. It showed the three confirmed defects still present at that time. The live database was not queried again during this implementation.

## Original defects and root causes

| Finding | Root cause in the available live evidence | Severity | Status |
|---|---|---:|---|
| `users` rows were globally readable | Permissive `p_users_read` used `USING (true)`; permissive policies combine with OR. | Critical | STILL OPEN in the live snapshot; proposed fix NOT VERIFIED |
| College memberships were globally readable | Permissive `p_memberships_read` used `USING (true)`. | Critical | STILL OPEN in the live snapshot; proposed fix NOT VERIFIED |
| Chat sessions were not private to their owner | `p_chat_sessions_tenant` checked college or platform-admin context, but not `user_id`. | High | STILL OPEN in the live snapshot; proposed fix NOT VERIFIED |
| User writes could create privileged accounts | Live `p_users_insert` used `WITH CHECK (true)`. | High | Proposed fix NOT VERIFIED |

Phase 3A.3 recorded that the live app-role connection was `college_app_user`, without superuser or `BYPASSRLS` privileges, and that protected tables were owned by `postgres` with RLS enabled. Those facts do not validate this new patch or establish the current live state.

## Repository changes

The repository changes implement application-side safeguards and prepare the database changes; they do not themselves replace live RLS policies.

- `backend/app/database/session.py` — transaction-local RLS context includes narrowly-scoped onboarding and email-verification flags.
- `backend/app/dependencies/auth.py` — sets the verified subject before self-row lookup and sets super-admin context from the database user role.
- `backend/app/services/auth_service.py` and `backend/app/schemas/auth.py` — reject privileged public registration while retaining student registration and normal authentication flows.
- `backend/app/repositories/user_repository.py` — uses the proposed narrow exact-email lookup function for email-based authentication.
- `backend/app/repositories/registration_repository.py` — uses the proposed invitation-token lookup function and establishes validated invitation context before provisioning.
- `backend/app/api/v1/colleges.py` — retains pending-college admin onboarding with scoped context and removes public admin-identity lookup.
- `backend/app/api/v1/memberships.py` — validates college access before listing memberships.
- `backend/app/api/v1/chat.py` — validates tenant context and enforces authenticated user ownership in session access paths.
- `backend/tests/test_phase3a4_authz.py` and `backend/tests/test_chat_rls_and_telemetry.py` — focused registration, ownership, context, message, and fallback regression coverage.

The complete proposed database patch and its rollback are in [phase3a4-targeted-rls-security-fix.sql](./phase3a4-targeted-rls-security-fix.sql). It is a proposal, not an applied migration.

## Proposed SQL behavior review

The proposed patch:

- Replaces `p_users_read` with self-read or trusted platform-admin access.
- Replaces `p_users_insert` with student self-registration, constrained pending-admin provisioning, or trusted platform-admin insertion.
- Retains self/platform-admin user updates, adds a trigger blocking self role and activation changes, and restricts self-verification changes to authorized flows.
- Replaces membership reads with self, validated same-college admin, or trusted platform-admin access; makes ordinary membership writes unavailable except scoped onboarding/invitation insertion.
- Replaces the chat-session policy with user-and-college ownership checks, preserving anonymous sessions within their selected college and trusted platform-admin access.
- Aligns the chat-message tenant policy with its parent session; the existing separate platform-admin chat-message policy is left intact.
- Adds exact-email and exact-invitation-token lookup functions for unauthenticated authentication flows, and helper functions with fixed `search_path` and narrowly granted execution.

Review caveat: these `SECURITY DEFINER` functions must be created by an appropriately trusted table owner, and their owner, ACLs, behavior, and interaction with the actual schema must be validated on an isolated PostgreSQL instance before deployment. The invitation provisioning helper also relies on the application setting transaction-local context only after validating the invitation token. The app-role credential must remain backend-only; a database credential holder can set custom GUCs directly.

No claim is made that the SQL syntax or semantics have passed PostgreSQL validation.

## Acceptance criteria and evidence

| Acceptance criterion | Status | Evidence / limitation |
|---|---|---|
| No unrestricted `users` SELECT policy remains | NOT VERIFIED | The patch replaces the policy, but it was not applied or tested on PostgreSQL. |
| No unrestricted `college_memberships` SELECT policy remains | NOT VERIFIED | The patch replaces the policy, but it was not applied or tested on PostgreSQL. |
| Chat sessions enforce both user and tenant ownership | PARTIALLY FIXED | Application ownership checks are covered by unit tests; the live RLS policy remains unmodified and the proposed policy is not DB-tested. |
| Unauthorized user/membership/session writes are rejected | NOT VERIFIED | Trigger and policy checks require isolated PostgreSQL tests, including role escalation and cross-tenant mutation attempts. |
| Super-admin access remains trusted and functional | NOT VERIFIED | Application context derives the role from the loaded user row; SQL helper ownership and policy behavior were not database-tested. |
| Public registration cannot request a privileged role | PASS (unit test) | Privileged public registration is rejected by focused tests. |
| Registration, login, reset, verification, and invitation flows work with RLS | NOT VERIFIED | No isolated DB was available; authentication helper functions are not in the live schema from the available evidence. |
| Chat messages and assistant fallback remain functional | PASS (mocked regression tests) | Focused chat tests passed; this does not prove live RLS or database insertion behavior. |
| AIT/RCTI cross-tenant and cross-user isolation passes | NOT VERIFIED | No isolated policy test or production write test was performed. |
| Existing production data was left unchanged | PASS for this task | No production SQL, DML, migration, seed, or policy change was executed. |
| Isolated PostgreSQL policy validation passes | BLOCKED | No isolated test database was available; no PostgreSQL policy tests were run. |

## Tests and checks executed

- `backend/tests/test_phase3a4_authz.py` and `backend/tests/test_chat_rls_and_telemetry.py`: **18 passed**.
- `backend/tests/test_auth_endpoints.py` and `backend/tests/test_auth_security.py`: **8 passed**.
- Combined relevant test result: **26 passed**. These are unit/mocked tests, not database integration tests.
- `py_compile` on changed Python implementation and test files: **passed**.
- Pylance syntax checks on changed Python files: **no syntax errors reported**.
- Pylance signature compatibility for `set_rls_context`: **21 call sites compatible**.
- Isolated PostgreSQL policy tests: **BLOCKED / not run**.
- Production database changes: **not run**.

## Remaining risks and production blockers

1. The live database may have changed since the Phase 3A.3 snapshot; its current policies were not re-read for this task.
2. No isolated PostgreSQL instance was available to test the SQL, RLS policy combination, helper-function privileges, triggers, transaction-local context, or real inserts and updates.
3. The changed application code now calls `lookup_user_by_email_for_auth` and `lookup_college_invitation_by_token`; these functions are only in the proposed SQL patch. Deploying the code without a compatible database rollout will break those authentication paths.
4. Mocked tests do not establish AIT/RCTI isolation, cross-user chat privacy, or denied writes at the database layer.
5. Authentication, college onboarding, and invitation acceptance must be regression-tested against a disposable database initialized from the actual schema and the proposed patch.

## Deployment instructions

**Do not apply the proposed SQL to production now.** First provision an isolated PostgreSQL database with the production-equivalent schema, role grants, RLS enabled, and representative test identities. Apply the patch only there; run the required cross-tenant, cross-user, registration, invitation, chat-message, update/delete denial, and trusted-super-admin tests. Review function owners and effective privileges as well as all permissive policies combined by OR.

After isolated validation, obtain explicit approval before any live database change. Plan a coordinated application/database rollout: the application now depends on the two lookup functions, while policy tightening may affect older application versions. Confirm a tested, compatible deployment order and rollback window before touching production. Never use an admin connection for application traffic, and do not deploy the changed application against a database where the required functions are absent.

Until those checks pass and production changes are explicitly approved, the recommendation remains **NO-GO**.
