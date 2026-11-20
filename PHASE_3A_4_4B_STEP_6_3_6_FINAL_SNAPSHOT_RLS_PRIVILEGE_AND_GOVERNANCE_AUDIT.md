# Phase 3A.4.4B — Step 6.3.6: Final Technical Accuracy Correction and Gate A Readiness Review
*(Incorporating Step 6.3.6.1 Final Minor Corrections and Database Remediation Transition)*

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Database Migration Specialist, PostgreSQL RLS Specialist, Independent Technical Auditor  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Target Predecessor Document:** [Step 6.3.5 Final Residual Technical and Governance Corrections](./PHASE_3A_4_4B_STEP_6_3_5_FINAL_RESIDUAL_TECHNICAL_AND_GOVERNANCE_CORRECTIONS.md)  
**Deliverable Document:** `PHASE_3A_4_4B_STEP_6_3_6_FINAL_SNAPSHOT_RLS_PRIVILEGE_AND_GOVERNANCE_AUDIT.md`

---

## 1. Executive Verdict

```
================================================================================
FINAL DOCUMENTATION VERDICT:
READY FOR FORMAL HUMAN GATE A DECISIONS
================================================================================
```

This report represents the definitive, strictly read-only technical accuracy review and Gate A readiness audit for Phase 3A.4.4B, updated with Step 6.3.6.1 corrections. It eliminates technical inaccuracies regarding PostgreSQL snapshot isolation, function volatility, privilege escalation test fixtures, RLS bypass mechanics, connection pooling semantics, and driver URL handling. It consolidates the decision register into a single canonical source of truth, maps specialist advice domains to decision authorities, establishes clear package status accounting, and sets the boundary conditions for diagnosing the unresolved PostgreSQL authentication lookup failure.

### Critical Governance Declarations

1. **Documentation Accuracy Only:** The verdict `READY FOR FORMAL HUMAN GATE A DECISIONS` certifies that documentation-level errors have been corrected and the decision package is ready for human review. **Gate A is NOT approved or complete.**
2. **All 22 Decisions Remain Pending:** Zero decisions in D-01 through D-22 are approved by this document. Every decision remains **`[PENDING HUMAN DECISION]`**.
3. **Delegation of Authority Not Established:** Because Evidence Package 6 is missing, no technical reviewer or specialist possesses authority to approve decisions on behalf of the Project Owner.
4. **Implementation Strictly Prohibited (Gate B):** Zero implementation authorization is granted. Modifying code, migrations, or configurations remains strictly prohibited.
5. **Database Validation Strictly Prohibited (Gate C):** Zero database validation has occurred. Executing SQL queries, running migrations, or connecting to live databases remains strictly prohibited.
6. **Authentication Error Unresolved:** The error `public.lookup_user_by_email_for_auth(unknown) does not exist` has not been fixed.
7. **Production Deployment Strictly Prohibited:** Production release remains unapproved.

---

## 2. Files Inspected

The following repository artifacts were inspected statically as text without opening network sockets or executing code:

1. `database/migrations/010_create_indexes.sql` lines 25–45 [VERIFIED STATICALLY]
2. `database/migrations/011_prepare_rls.sql` lines 60–75 [VERIFIED STATICALLY]
3. `database/migrations/017_row_level_security_policies.sql` lines 1–154 [VERIFIED STATICALLY]
4. `database/migrations/018_create_application_role.sql` lines 1–45 [VERIFIED STATICALLY]
5. `database/migrations/019_complete_rls_policies.sql` lines 1–280 [VERIFIED STATICALLY]
6. `database/migrations/021_phase3a42_security_onboarding.sql` lines 20–85, 85–102, 360–530, 670–725 [VERIFIED STATICALLY]
7. `database/migrations/022_minimize_auth_lookup.sql` lines 1–53 [VERIFIED STATICALLY]
8. `backend/app/database/connection.py` lines 1–85 [VERIFIED STATICALLY]
9. `backend/app/database/session.py` lines 80–145 [VERIFIED STATICALLY]
10. `backend/app/repositories/user_repository.py` lines 35–65 [VERIFIED STATICALLY]
11. `backend/app/services/auth_service.py` lines 65–85 [VERIFIED STATICALLY]
12. `backend/app/api/v1/auth.py` lines 65–80 [VERIFIED STATICALLY]
13. `backend/app/core/config.py` lines 100–120, 140–150, 190–210 [VERIFIED STATICALLY]
14. `tests/config.py` lines 25–45 [VERIFIED STATICALLY]
15. `PHASE_3A_4_4B_STEP_6_3_5_FINAL_RESIDUAL_TECHNICAL_AND_GOVERNANCE_CORRECTIONS.md` [VERIFIED STATICALLY]

---

## 3. Corrections Made to Predecessor Documents

```
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| #  | Topic / Claim              | Prior Formulation                           | Corrected Formulation in Step 6.3.6 / 6.3.6.1               | Traceability & Evidence Level |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 1  | D-10 Function Volatility & | Claimed every subsequent statement in READ  | Corrected: A STABLE function executes using the calling     | PostgreSQL Documentation:     |
|    | Snapshot Isolation         | COMMITTED immediately sees key revocation.  | query's snapshot. A revocation committed after the calling  | Function Volatility Categories|
|    |                            |                                             | query's snapshot is NOT visible to that function execution. | & Transaction Isolation;      |
|    |                            |                                             | REPEATABLE READ transactions retain transaction snapshot.   | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 2  | D-09 Privilege Escalation  | Proposed tests using real administrative    | Corrected: Real administrative roles (postgres,             | PostgreSQL Security Best      |
|    | Test Fixtures              | roles (e.g. GRANT postgres TO ...).         | supabase_admin) must never be used in negative fixtures.    | Practices;                    |
|    |                            |                                             | All tests restructured using synthetic test roles.          | [PROPOSED]                    |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 3  | D-09 Exact Routine Name    | Used abbreviated notation:                  | Corrected: Specified verbatim schema-qualified routine name:| 021 migration line 21;        |
|    | Traceability               | auth_priv.is_req_ctx_valid()                | auth_private.is_request_context_valid()                     | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 4  | D-09 RLS Bypass & Policy   | Stated table owners bypass RLS unless       | Corrected: Superusers and roles with BYPASSRLS bypass RLS   | PostgreSQL Documentation:     |
|    | Synthesis Realities        | FORCE RLS applies; asserted fixed row counts| even when FORCE RLS is set. Outcome depends on all active   | Row Security Policies;        |
|    |                            | without live policy and grant proof.        | permissive (OR) and restrictive (AND) policies. Labeled     | 021 migration lines 403–525;  |
|    |                            |                                             | exact row counts as conditional test expectations.          | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 5  | D-06 session_user Identity | Contained blanket statements prohibiting    | Corrected: Evaluates session_user neutrally according to    | connection.py lines 34–65;    |
|    | Recommendation             | session_user from RLS or identity designs.  | connection and pooling architecture; must not be assumed to | [VERIFIED STATICALLY]         |
|    |                            |                                             | identify HTTP application users; requires empirical testing.|                               |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 6  | D-16 Redis & Driver URL    | Equated application URL validator support   | Corrected: Separated client-supported schemes from Celery   | config.py lines 144–146;      |
|    | Validation Paths           | with driver support; implied rediss:// is   | broker/backend supported schemes. Verified repository       | celery_app.py lines 5–15;     |
|    |                            | configured in the repository.               | defines redis://. Marked runtime TLS behavior unverified.   | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 7  | D-22 PostgreSQL 17 Role    | Described membership without distinguishing | Corrected: Detailed per-membership INHERIT and SET options  | PostgreSQL 17 pg_auth_members;|
|    | Membership Semantics       | per-membership options from role NOINHERIT. | in PG 17; college_auth_user receives EXECUTE via membership | [PROPOSED] / [PENDING DECISION|
|    |                            |                                             | with INHERIT TRUE, SET FALSE. Marked PROPOSED & PENDING.    |                               |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 8  | D-05 Qualified Operator &  | Made categorical claims regarding operator  | Corrected: Avoided categorical claims; qualified search path| 021 migration lines 135–720;  |
|    | search_path Risk           | resolution in pg_catalog.                   | risks for custom types, cross-type operators, and unqualified| parse_oper.c;                 |
|    |                            |                                             | calls; noted exploitability requires live CREATE on public. | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 9  | Evidence Package Narrative | Described all six evidence packages as      | Corrected: Accurately stated six outstanding packages:      | Packages 1–6 audit;           |
|    | Consistency                | "missing".                                  | four missing and two incomplete.                            | [VERIFIED STATICALLY]         |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
| 10 | Specialist Traceability &  | Did not distinguish business authority from | Corrected: Mapped specialist domains to technical advice    | Package 6 missing;            |
|    | Approval Authority         | specialist technical advice; noted missing  | in a consolidated matrix; affirmed Project Owner approval   | [PENDING OWNER DECISION]      |
|    |                            | delegation of authority document.           | is mandatory; marked delegated authority NOT ESTABLISHED.   |                               |
+----+----------------------------+---------------------------------------------+-------------------------------------------------------------+-------------------------------+
```

---

## 4. Remaining Technical Uncertainties

The following technical items cannot be resolved from static repository source code and are cataloged as uncertainties requiring runtime verification during Gate C:

1. **Live Database Catalog State:** Whether migrations `001` through `022` were applied in hosted Supabase, staging, or production remains unknown [NOT VERIFIED — DATABASE VALIDATION REQUIRED].
2. **Schema `public` Namespace Privileges:** Whether any non-superuser role possesses `CREATE` privilege in schema `public` (`pg_namespace.nspacl`) remains uninspected [NOT VERIFIED — DATABASE VALIDATION REQUIRED].
3. **Function Ownership in Live Catalog:** Whether `pg_proc.proowner` for definer functions in the live database is assigned to superuser roles (`postgres`, `supabase_admin`) or capability roles remains unknown [NOT VERIFIED — DATABASE VALIDATION REQUIRED].
4. **Runtime Role Attributes:** Whether `college_app_user` in the target cluster possesses unexpected attributes (e.g. `rolsuper` or `rolbypassrls`) remains unknown [NOT VERIFIED — DATABASE VALIDATION REQUIRED].
5. **Exact RLS Filtering Counts:** True row return counts under asyncpg cannot be proven without executing tests against seeded synthetic records in an isolated database [NOT VERIFIED — DATABASE VALIDATION REQUIRED].
6. **Authentication Function Signature & State:** Whether `public.lookup_user_by_email_for_auth(text)` is present in the live target catalog with matching parameter and return types remains unverified [NOT VERIFIED — DATABASE VALIDATION REQUIRED].

---

## 5. Canonical D-01 through D-22 Decision Register

Every decision remains **`[PENDING HUMAN DECISION]`**. Zero decisions are approved.

```
Status Legend:
[REC] = Recommended Technical Position
[EVI] = Repository Evidence Available
[UNV] = Database Evidence Unverified
[DEP] = Unresolved Dependencies
[PO]  = Project Owner Approval Required
[SPE] = Specialist Advice Domain
[BLK] = Blocks Gate A
```

---

### D-01: Migration History and Branch Selection
- **[REC]:** Branch B (Forward-Only Corrective Migration `023_...`) is the conservative default while history is unknown. Branch A may be considered only if written attestation proves 001–022 were never applied in any environment.
- **[EVI]:** Migrations 001–022 present in repository; CI runs in-memory SQLite; manual SQL Editor instructions in README.
- **[UNV]:** Live database migration execution history (`schema_migrations`) is unverified.
- **[PO]:** Yes. Must formally authorize Branch B forward remediation.
- **[SPE]:** Database Release Engineer (Technical Advice).
- **[DEP]:** Authoritative written deployment ledger (Package 1).
- **[BLK]:** **YES**.

---

### D-02: Shared vs. Tenant-Isolated Worker Architecture
- **[REC]:** Mandatory database job claims and unprivileged worker role; operational choice between dedicated worker processes vs. shared pool with subprocess sandboxing.
- **[EVI]:** Shared Celery queue and Redis URL in `celery_app.py`; PyMuPDF document extraction in `document_tasks.py`.
- **[UNV]:** Worker queue memory footprint and performance under isolated execution unverified.
- **[PO]:** Yes. Budget and infrastructure complexity trade-off sign-off.
- **[SPE]:** Security Architect & Worker Platform Engineer (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3).
- **[BLK]:** **YES**.

---

### D-03: Worker Authentication and Claim Authorization
- **[REC]:** Worker connects with authenticated login principal, assumes `NOLOGIN` capability role `college_worker_role`, and calls `claim_job()` to obtain time-bounded cryptographic lease token bound to tenant.
- **[EVI]:** Tasks currently receive raw `college_id` via Celery JSON kwargs; session sets ambient GUC without database validation.
- **[UNV]:** Claim function and lease verification logic do not exist in live database catalog.
- **[PO]:** No (Technical architecture; delegated authority not established).
- **[SPE]:** Database Security Architect (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3).
- **[BLK]:** **YES**.

---

### D-04: Job Lease, Heartbeat, Retry, Duplicate, and Crash Handling
- **[REC]:** 5-minute initial lease, 60-second heartbeat, max 3 retries with exponential backoff, 1-hour hard dead-letter timeout, idempotent database upserts.
- **[EVI]:** `crawl_jobs` and `documents` have basic status columns, but lack lease expiration, heartbeat timestamps, and dead-letter queues.
- **[UNV]:** Database schema columns for lease tracking unverified in live catalog.
- **[PO]:** Yes. Acceptance of job recovery latency SLA.
- **[SPE]:** Distributed Systems Engineer (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3).
- **[BLK]:** **YES**.

---

### D-05: SECURITY DEFINER Ownership, Grants, search_path, and RLS
- **[REC]:** Dedicated `NOLOGIN` definer capability roles; strict `SET search_path = pg_catalog`; fully schema-qualified references; revoke `PUBLIC` execute; zero superuser ownership.
- **[EVI]:** 13 active functions across migrations 021 and 022; 9 definer functions in 021 set `search_path = pg_catalog, public, auth_private`; 022 sets `pg_catalog`.
- **[UNV]:** Live catalog `pg_proc.proowner`, `proacl`, and `pg_namespace` ACLs remain unverified.
- **[PO]:** No.
- **[SPE]:** PostgreSQL Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-06: Identity Consumers: session_user, current_user, and Signed Context
- **[REC]:** Evaluate `session_user` as an identity source according to the actual database connection and pooling architecture. Do not assume it identifies the HTTP application user. Document and test the selected identity mechanism. Application audit logging must record validated `public.current_app_user_id()`.
- **[EVI]:** `session.py` sets HMAC GUCs; migration 021 checks signature; migration 021 trigger checks `current_user <> 'postgres'`. `session_user` is not referenced in repository SQL.
- **[UNV]:** Live database views, triggers, and procedures unverified for hidden `session_user` calls.
- **[PO]:** Yes (Auditing and identity architecture sign-off).
- **[SPE]:** Application Security Engineer & Database Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-07: Direct-Login Testing Requirement
- **[REC]:** Dedicated unprivileged test harness login (`college_test_harness`) executing `SET ROLE college_app_user` for RLS testing. Direct-login testing reserved for connection auth verification. Capability roles remain `NOLOGIN`.
- **[EVI]:** Tests currently run against SQLite in CI or connect via superuser in local scripts.
- **[UNV]:** Test harness credentials and role grants unverified in test catalog.
- **[PO]:** No.
- **[SPE]:** Security Test Engineer (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-08: PostgreSQL 17 Role-Membership Closure and Protected-Role Allowlist
- **[REC]:** Enforce protected-role allowlist; execute recursive cycle-safe CTE checking `set_option`, `inherit_option`, and `admin_option` in `pg_auth_members` to prove zero paths to superuser.
- **[EVI]:** Step 4 recursive query specification; migration 018 role creation.
- **[UNV]:** Live `pg_auth_members` catalog state unverified.
- **[PO]:** No.
- **[SPE]:** PostgreSQL Database Administrator (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-09: Unprivileged Negative-Test Principal
- **[REC]:** Multi-tiered negative test suite executed via an unprivileged test principal covering ACL denials, RLS policy enforcement, and privilege escalation vectors. Proposed conditional test expectations include:
  - Table ACL denials raising error `42501` (`insufficient_privilege`).
  - Cross-tenant `SELECT` returning zero rows (RLS `USING` clause filtering).
  - Cross-tenant `INSERT` raising error `42501` (RLS `WITH CHECK` clause violation).
  - Cross-tenant `UPDATE` affecting zero rows (`USING` clause filtering rows prior to evaluation).
  - Tenant-violating `UPDATE` raising error `42501` (`WITH CHECK` clause violation).
  - Unauthorized `ALTER ROLE ... SUPERUSER` or `SET ROLE` raising error `42501`.
  *Note:* Each outcome is a conditional test expectation, not a universally guaranteed invariant; actual runtime behavior depends on applicable permissive vs. restrictive policies, table ACL grants, role attributes (`rolsuper`, `rolbypassrls`), execution identity, and seeded test data. All expectations require empirical verification in the authorized disposable PostgreSQL/Supabase environment, preserving the architectural distinction between ACL denials and RLS row filtering.
- **[EVI]:** Existing tests test tenant switching within single connection; lack separate unprivileged login principal.
- **[UNV]:** Negative test fixtures unverified in database catalog.
- **[PO]:** No.
- **[SPE]:** QA / Security Test Engineer (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-10: Signing-Key Storage, Access, and Rotation
- **[REC]:** External secret store; dual-key schema (`ACTIVE` and `PREVIOUS`) in `auth_private.rls_context_keys`; overlap window derived from token TTL, deployment duration, and cache TTL; multi-instance cache invalidation; emergency `REVOKED` state.
- **[EVI]:** Migration 021 has unique partial index preventing dual active keys; `session.py` requires 32-byte secret.
- **[UNV]:** Contents of `auth_private.rls_context_keys` unverified in live catalog.
- **[PO]:** Yes. Key custody policy approval.
- **[SPE]:** Key Management Specialist & Application Security Engineer (Technical Advice).
- **[DEP]:** Key Management Runbook (Package 2).
- **[BLK]:** **YES**.

---

### D-11: Password-Reset Email Delivery Provider or Deferral
- **[REC]:** Formally defer and disable self-service password reset in production until a contracted transactional email provider with verified SPF/DKIM/DMARC is integrated.
- **[EVI]:** `email_transport.py` implements mock/logging transport; reset tokens are discarded or logged.
- **[UNV]:** N/A (application service layer).
- **[PO]:** Yes. Product decision to disable feature vs contract provider.
- **[SPE]:** Communications Privacy & Security Specialist (Technical Advice).
- **[DEP]:** None (service-level business contract).
- **[BLK]:** **YES**.

---

### D-12: Notification Email Retention and Data Minimization
- **[REC]:** Institutional 30-day retention schedule for notification delivery logs; automated scrubbing of recipient email addresses, tokens, and bodies after dispatch; Celery purge task.
- **[EVI]:** `notification.py` model; no automated pruning task in repository.
- **[UNV]:** Live notification table records unverified.
- **[PO]:** Yes. Written approval of 30-day retention schedule.
- **[SPE]:** Data Privacy & Compliance Officer (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.

---

### D-13: Public College Registration versus Super Admin-Only Registration
- **[REC]:** Public registration creates records in `college_registrations` with status `PENDING` only. Provisioning active tenants in `colleges` and creating admin accounts is strictly restricted to Super Admin approval.
- **[EVI]:** Public registration page in `apps/admin-frontend`; migration 021 defines `submit_public_college_registration()`.
- **[UNV]:** Registration table RLS policies unverified in live catalog.
- **[PO]:** Yes. Onboarding workflow business approval.
- **[SPE]:** Application Security Engineer (Technical Advice).
- **[DEP]:** Registration approval workflow specification.
- **[BLK]:** **YES**.

---

### D-14: EDITOR and VIEWER Permission Matrix
- **[REC]:** Fail-closed RBAC: `VIEWER` is strict read-only; `EDITOR` can upload documents and edit drafts but cannot publish knowledge chunks or delete documents; `COLLEGE_ADMIN` holds publish/delete authority.
- **[EVI]:** Role enums in migration 003 define basic roles; intermediate dashboard roles lack database-level grants.
- **[UNV]:** Enum types and table grants unverified in live catalog.
- **[PO]:** Yes. Product RBAC matrix sign-off.
- **[SPE]:** Application Security Architect (Technical Advice).
- **[DEP]:** Formal RBAC permission matrix document.
- **[BLK]:** **YES**.

---

### D-15: Audit Payload and AI Telemetry Allowlists and Redaction
- **[REC]:** Strict key allowlist for audit JSONB payloads; PII/credential scrubber; AI telemetry restricted to aggregate metrics (`tokens`, `latency_ms`) and error codes; raw prompts and stack traces prohibited.
- **[EVI]:** Migration 008 creates `audit_logs` and `ai_provider_events`; `_log_telemetry` logs API metrics.
- **[UNV]:** Live telemetry table rows unverified for unredacted data.
- **[PO]:** Yes. Telemetry data governance sign-off.
- **[SPE]:** AI Operations Lead & Privacy Officer (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.

---

### D-16: Creation of a New Disposable Supabase-Compatible Test Environment
- **[REC]:** Provision fresh, isolated local Supabase CLI stack on loopback interface; enforce fail-closed connection guards on all test URLs; strictly prohibit cloud connections.
- **[EVI]:** `tests/config.py` loads `.env` targeting remote cloud Supabase; Step 2 vanilla PostgreSQL container lacked Supabase `auth` schemas.
- **[UNV]:** Local Supabase test stack not yet provisioned.
- **[PO]:** No.
- **[SPE]:** DevOps / Platform Engineer & Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.

---

### D-17: Implementation Authorization and Separate Production Approval
- **[REC]:** Enforce strict 4-stage gate separation: Gate A (Design Approval) $\to$ Gate B (Test Implementation) $\to$ Gate C (Database Validation) $\to$ Production Approval.
- **[EVI]:** All audit reports record zero implementation authorization.
- **[UNV]:** N/A (governance control).
- **[PO]:** Yes. Formal delegation of authority sign-off.
- **[SPE]:** Lead System Architect (Technical Advice).
- **[DEP]:** Delegation of Authority Document (Package 6).
- **[BLK]:** **YES**.

---

### D-18: Application Identity Model and Supabase auth.uid() Boundary
- **[REC]:** Standardize on custom HMAC-signed application context (`public.current_app_user_id()`); deprecate and remove application dependencies on Supabase `auth.uid()`.
- **[EVI]:** FastAPI issues custom JWTs; migration 021 implements context functions.
- **[UNV]:** Live catalog unverified for lingering `auth.uid()` references.
- **[PO]:** No.
- **[SPE]:** Identity & Auth Architect (Technical Advice).
- **[DEP]:** Architectural Decision Record (ADR) sign-off.
- **[BLK]:** **YES**.

---

### D-19: Visitor Token Lifetime and Anonymous Feedback
- **[REC]:** 32-byte visitor bearer token; 24-hour absolute non-sliding expiration; matching token required for chat feedback; adopt `v2` context payload binding `visitor_token_hash`.
- **[EVI]:** `chat.py` generates visitor tokens; migration 021 checks `app.chat_visitor_token` GUC.
- **[UNV]:** Live chat session rows and token expiration state unverified.
- **[PO]:** Yes. Student user experience policy sign-off.
- **[SPE]:** Application Security Engineer (Technical Advice).
- **[DEP]:** Anonymous Chat API Specification.
- **[BLK]:** **YES**.

---

### D-20: Guest Support-Ticket Permissions
- **[REC]:** Guest support tickets are strictly create-only; zero database read/update/reply permissions; staff follow up exclusively via email.
- **[EVI]:** `support_service.py` allows unauthenticated creation; `SupportTicket` model permits nullable `user_id`.
- **[UNV]:** RLS policies on `support_tickets` unverified in live catalog.
- **[PO]:** Yes. Support workflow policy approval.
- **[SPE]:** Security Architect (Technical Advice).
- **[DEP]:** Support workflow policy document.
- **[BLK]:** **YES**.

---

### D-21: College Chat Analytics and Raw Conversation Access
- **[REC]:** College Admins receive aggregate metrics only; zero direct browse access to raw student chat logs or transcripts unless escalated to a ticket.
- **[EVI]:** `analytics_service.py` provides aggregated queries; `college-admin/analytics/page.tsx` displays charts.
- **[UNV]:** Analytics views and RLS policies unverified in live catalog.
- **[PO]:** Yes. Student privacy policy approval.
- **[SPE]:** Data Privacy Officer (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.

---

### D-22: Sensitive User-Column Access and Authentication Lookup Contract
- **[REC]:** Enforce minimal 7-field projection via `public.lookup_user_by_email_for_auth(CAST(:email AS text))`; introduce dedicated `college_auth_role` with exclusive `EXECUTE` and dedicated connection pool (`DATABASE_AUTH_ROLE_URL`); revoke `EXECUTE` from `college_app_user`.
- **[EVI]:** Migration 022 implements 7-field projection; `UserRepository` executes function; test logs show `lookup_user_by_email_for_auth(unknown) does not exist`.
- **[UNV]:** Live database function existence, parameter types, return projection, and catalog grants remain unverified.
- **[PO]:** Yes (Introducing dedicated connection pool and role impacts infrastructure).
- **[SPE]:** Application Security Engineer & Database Security Architect (Technical Advice).
- **[DEP]:** Dedicated Authentication Role Architecture Specification.
- **[BLK]:** **YES**.

---

## 6. Six Evidence-Package Status Table

Six outstanding evidence packages: four missing and two incomplete. The table below details the specific status and completion actions required for each package.

```
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| #  | Evidence Package Name                                         | Status       | Action Required to Complete                           |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 1  | Authoritative Migration History and Deployment Ledger         | MISSING      | Release Owner must submit certified environment audit.|
|    | (Required for D-01)                                           |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 2  | Key Management and Rotation Runbook                           | MISSING      | Key Management Specialist must author KMS custody doc.|
|    | (Required for D-10)                                           |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 3  | Worker Authentication and Isolation Architecture              | INCOMPLETE   | Worker Platform Lead must finalize queue routing/DDL. |
|    | (Required for D-02, D-03, D-04)                               |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 4  | Data Retention and Privacy Schedule                           | MISSING      | Data Privacy Officer must sign formal retention policy.|
|    | (Required for D-12, D-15, D-21)                               |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 5  | Local Disposable Supabase Stack Specification                 | INCOMPLETE   | DevOps must provide verified Compose manifest.        |
|    | (Required for D-05, D-06, D-07, D-08, D-09, D-16)            |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
| 6  | Delegation of Authority and Approval Ownership Document       | MISSING      | Corporate sign-off naming human authorizers for Gates.|
|    | (Required for D-17 and overall Gate A governance)             |              |                                                       |
+----+---------------------------------------------------------------+--------------+-------------------------------------------------------+
```

---

## 7. Consolidated Specialist Advice Traceability Matrix

The 13 technical specialist domains provide advisory technical evaluations only. Technical advice remains strictly distinct from business decision approval. In the absence of an executed Delegation of Authority document (Package 6), final decision authority resides exclusively with the Project Owner.

```
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| #  | Specialist Advice Domain             | Related Decisions   | Nature of Required Technical Advice                         | Human Decision Authority                                    |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 1  | Database Release Engineer            | D-01                | Evaluates forward-only migration feasibility (Branch B) vs  | Final approval authority not established; Project Owner or  |
|    |                                      |                     | rollback risks; verifies migration execution ledger drift.  | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 2  | Worker Platform Engineer             | D-02, D-04          | Evaluates process vs thread worker isolation, container     | Final approval authority not established; Project Owner or  |
|    |                                      |                     | sandbox limits, and lease heartbeat failure modes.          | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 3  | Database Security Architect          | D-03, D-05, D-22    | Reviews worker cryptographic claims, SECURITY DEFINER       | Final approval authority not established; Project Owner or  |
|    |                                      |                     | privilege model, search_path, and dedicated auth role DDL.  | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 4  | Distributed Systems Engineer         | D-04                | Advises on lease timeout SLAs, crash recovery, heartbeat    | Final approval authority not established; Project Owner or  |
|    |                                      |                     | cadence, Celery retry backoff, and dead-letter queues.      | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 5  | PostgreSQL Security Architect        | D-05, D-06, D-08,   | Analyzes schema ACLs, operator search_path resolution risks,| Final approval authority not established; Project Owner or  |
|    |                                      | D-16                | connection identity mechanics, and recursive role closure.  | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 6  | Application Security Engineer        | D-06, D-10, D-13,   | Reviews signed context generation, KMS rotation windows,    | Final approval authority not established; Project Owner or  |
|    |                                      | D-14, D-19, D-22    | public onboarding validation, RBAC, and auth contracts.     | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 7  | Security Test Engineer               | D-07, D-09          | Defines direct-login harness isolation, privilege-escalation| Final approval authority not established; Project Owner or  |
|    |                                      |                     | negative test cases, and ACL vs RLS error assertions.       | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 8  | PostgreSQL Database Administrator    | D-08, D-16          | Validates pg_auth_members recursive CTE, connection pool    | Final approval authority not established; Project Owner or  |
|    |                                      |                     | sizing, driver URL schemes, and catalog maintenance scripts.| formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 9  | Key Management Specialist            | D-10                | Evaluates external KMS integration, key lifecycle states    | Final approval authority not established; Project Owner or  |
|    |                                      |                     | (ACTIVE/PREVIOUS/REVOKED), secret storage, and overlap.     | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 10 | Communications Privacy Specialist    | D-11                | Advises on transactional email provider integration, SPF/   | Final approval authority not established; Project Owner or  |
|    |                                      |                     | DKIM/DMARC hygiene, and privacy risks of email delivery.    | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 11 | Data Privacy & Compliance Officer    | D-12, D-15, D-21    | Evaluates notification retention schedules, telemetry PII   | Final approval authority not established; Project Owner or  |
|    |                                      |                     | redaction allowlists, and student chat privacy governance.  | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 12 | DevOps / Platform Engineer           | D-16                | Specifies local disposable Supabase Docker Compose stack,   | Final approval authority not established; Project Owner or  |
|    |                                      |                     | loopback port binding, and test URL fail-closed guards.     | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
| 13 | Lead System Architect                | D-17, D-18          | Reviews 4-stage gate governance, custom application context | Final approval authority not established; Project Owner or  |
|    |                                      |                     | architecture, and retirement of direct auth.uid() coupling. | formally delegated authority must decide.                   |
+----+--------------------------------------+---------------------+-------------------------------------------------------------+-------------------------------------------------------------+
```

---

## 8. Gate A Readiness Matrix

```
+--------------------------------------------------------------------------------------------------------------------+
| CANONICAL GATE A READINESS MATRIX                                                                                  |
+--------------------------------------------------------------------------------------------------+-----------------+
| Evaluation Dimension                                                                             | Current Status  |
+--------------------------------------------------------------------------------------------------+-----------------+
| 1. Technical documentation and risk analyses consolidated and free of contradictions?             | COMPLETE        |
| 2. Erroneous role syntax (GRANT superuser) and inaccurate operator claims corrected?             | COMPLETE        |
| 3. Exact verbatim SECURITY DEFINER inventory established without abbreviations?                 | COMPLETE        |
| 4. Function volatility and STABLE calling-query snapshot realities accurately documented?        | COMPLETE        |
| 5. Identity layers (session_user vs current_user vs signed context vs JWT) disentangled?        | COMPLETE        |
| 6. Exact connection URL schemes and drivers traced to repository source?                         | COMPLETE        |
| 7. Canonical D-01–D-22 decision register established?                                            | COMPLETE        |
| 8. Documentation package ready to be presented to Project Owner and Technical Specialists?       | READY           |
+--------------------------------------------------------------------------------------------------+-----------------+
| 9. Have formal written decisions been executed by the Project Owner for the 14 owner decisions?  | PENDING         |
| 10. Have technical specialist advice sign-offs been formally collected across all 13 domains?    | PENDING         |
| 11. Have the six outstanding evidence packages (four missing and two incomplete) been completed? | PENDING         |
| 12. Has Evidence Package 6 (Delegation of Authority) established authorized decision-makers?    | PENDING         |
| 13. Can Gate A be certified as COMPLETE at this time?                                            | NOT COMPLETE    |
+--------------------------------------------------------------------------------------------------+-----------------+
```

---

## 9. Explicit Implementation and Production Authorization Status

```
================================================================================
EXPLICIT GOVERNANCE DIRECTIVE:
1. ZERO IMPLEMENTATION IS AUTHORIZED BY THIS DOCUMENT.
2. GATE B (IMPLEMENTATION) REMAINS STRICTLY NOT AUTHORIZED.
   - Modifying application code, SQL migrations, or configurations remains PROHIBITED.
   - Gate B authorization requires independent, written sign-off AFTER Gate A closure.
3. GATE C (ISOLATED DATABASE VALIDATION) REMAINS STRICTLY NOT VALIDATED.
   - Executing SQL, running migrations, or connecting to databases remains PROHIBITED.
   - Validation must occur exclusively inside an authorized local disposable Supabase stack.
4. PRODUCTION DEPLOYMENT REMAINS STRICTLY NOT APPROVED.
================================================================================
```

---

## 10. Next Phase — Controlled Diagnosis of the Authentication Failure

### The Known Runtime Error
During integration and test harness execution, user authentication fails with the following exact error reported by PostgreSQL:

```
public.lookup_user_by_email_for_auth(unknown) does not exist
```

The application calls the stored procedure `public.lookup_user_by_email_for_auth`, but PostgreSQL reports that it cannot resolve a matching function in the database catalog.

### Possible Root Causes (Unconfirmed)
Without live catalog inspection, the exact root cause cannot be confirmed. Five plausible technical explanations exist:
1. **Migration 021 or 022 Not Applied:** The target database may have only run migrations through `019` or `020`, meaning the function has never been created in that catalog.
2. **Absent or Divergent Function Signature:** The function may exist under a different parameter type (e.g. `varchar` vs `text`), in a different schema, or with a different parameter list.
3. **Environment and Database Target Drift:** The application test harness may be connecting to a database instance, branch, or test container that has a different migration ledger than the repository files.
4. **Insufficient Schema or Function Privileges:** The connecting database user (`college_app_user` or default connection role) may lack `USAGE` on schema `public` or `EXECUTE` on the function, causing PostgreSQL to hide the function or fail resolution.
5. **Contract Mismatch in Return Structure or Call Arguments:** The call parameters supplied by SQLAlchemy/asyncpg or the column expectations in `UserRepository` may not match the actual database definition.

### Critical Diagnostic Constraints
- **Exact Cause Not Established:** The true cause remains unproven until live catalog inspection occurs.
- **No Connections Made:** No database connection, query execution, or catalog query has been performed under this strictly read-only audit.
- **Error Not Fixed:** Step 6.3.6 and Step 6.3.6.1 have **not** fixed the authentication error.
- **Syntax vs. Existence:** Adding `CAST(:email AS text)` in SQLAlchemy clarifies query parameter typing, but it **cannot** create a non-existent database function or grant missing catalog privileges.
- **No Hosted Supabase Shortcuts:** Migrations must **never** be applied directly to hosted Supabase as a shortcut or diagnostic workaround.

---

## 11. Proposed Controlled Practical Remediation Sequence

The following 10-step sequence is proposed for diagnosing and remediating the authentication error. **This is a proposed plan only; no step requiring database access or code modification may be executed without formal authorization:**

1. **Obtain Authoritative Migration History:** Collect the certified migration execution history (`schema_migrations` or migration table) across all target environments (Evidence Package 1).
2. **Authorize Isolated Disposable Test Stack:** Secure formal approval to provision an isolated, local disposable Supabase-compatible container stack bound exclusively to loopback (`127.0.0.1`).
3. **Reproduce Baseline Migration State:** Apply migrations sequentially in the isolated test stack to reproduce the exact target database state.
4. **Inspect Live Catalog Objects:** Inspect `pg_proc`, `pg_namespace`, `pg_roles`, and `pg_shdescription` in the disposable stack to verify function existence, argument types, return columns, function ownership, and explicit `GRANT EXECUTE` rights.
5. **Reconcile Database Contract with Application Code:** Compare the live database contract against `UserRepository.get_user_for_auth_by_email`, `AuthService.authenticate_user`, and the FastAPI auth endpoints.
6. **Identify Exact Root Cause:** Determine definitively whether the issue is migration absence, parameter type casting, privilege revocation, or schema visibility.
7. **Formulate Minimal Forward-Only Remediation:** Author the smallest safe, forward-only SQL migration (e.g. `023_...`) to repair the function definition, grants, and search path if migration history remains ambiguous.
8. **Execute Isolated Authentication Tests:** Test user authentication, password verification, and token issuance inside the disposable test environment.
9. **Execute Negative & Tenant Isolation Tests:** Verify that an unprivileged test principal cannot access sensitive user columns directly and that cross-tenant RLS boundaries hold.
10. **Obtain Production Deployment Approval:** Present verified test evidence and secure formal human sign-off before applying any change to staging or production environments.

---

## 12. Final Status Summary

```
================================================================================
OVERALL PROJECT PHASE STATUS SUMMARY:
--------------------------------------------------------------------------------
- Technical Documentation Review: SUBSTANTIALLY COMPLETE (All minor corrections incorporated)
- Gate A (Design & Policy Approval): NOT COMPLETE (Awaiting human & specialist sign-offs)
- Gate B (Implementation Authorization): NOT AUTHORIZED (Strictly locked)
- Gate C (Isolated Database Validation): NOT VALIDATED (Strictly locked)
- Authentication Error: UNRESOLVED (public.lookup_user_by_email_for_auth)
- Database Implementation: NOT STARTED
- Production Deployment: NOT APPROVED
================================================================================
```

*This document marks the conclusion of the documentation review cycle. No further repetitive audits are to be generated. The next actionable milestone is securing human Gate A decisions and provisioning the authorized disposable test environment for controlled diagnosis.*
