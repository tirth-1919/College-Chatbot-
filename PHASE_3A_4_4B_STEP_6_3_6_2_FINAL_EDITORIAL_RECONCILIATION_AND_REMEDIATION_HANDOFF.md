# Phase 3A.4.4B — Step 6.3.6.2: Final Editorial Reconciliation and Remediation Handoff

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Database Migration Specialist, PostgreSQL RLS Specialist, Independent Technical Auditor  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Deliverables:**
- [Step 6.3.6 Final Snapshot RLS, Privilege, and Governance Audit](./PHASE_3A_4_4B_STEP_6_3_6_FINAL_SNAPSHOT_RLS_PRIVILEGE_AND_GOVERNANCE_AUDIT.md)
- [Step 6.3.5 Final Residual Technical and Governance Corrections](./PHASE_3A_4_4B_STEP_6_3_5_FINAL_RESIDUAL_TECHNICAL_AND_GOVERNANCE_CORRECTIONS.md)  
**Deliverable Document:** `PHASE_3A_4_4B_STEP_6_3_6_2_FINAL_EDITORIAL_RECONCILIATION_AND_REMEDIATION_HANDOFF.md`

---

## 1. Executive Verdict & Core Governance Posture

```
================================================================================
FINAL EDITORIAL & GOVERNANCE VERDICT:
READY FOR FORMAL HUMAN GATE A DECISIONS & PRACTICAL REMEDIATION HANDOFF
================================================================================
```

This document represents the definitive, strictly read-only final editorial reconciliation for Phase 3A.4.4B. It resolves all remaining documentary inconsistencies identified in Step 6.3.6 and Step 6.3.6.1, reconciles the anatomy and error categorization of the PostgreSQL authentication failure, consolidates decision registers and approval authorities, eliminates duplicate and contradictory declarations, and establishes the formal handoff to human decision-makers.

### Explicit Governance Declarations

1. **Gate A is NOT COMPLETE:** Technical documentation is reconciled, but Gate A cannot be certified as complete until the 22 pending decisions are formally approved in writing and outstanding evidence packages are completed.
2. **Gate B (Implementation) is NOT AUTHORIZED:** Modifying application code, SQL migrations, configuration files, `.env` files, or secrets remains strictly prohibited.
3. **Gate C (Database Validation) HAS NOT OCCURRED:** No database connection, catalog inspection, migration execution, or test suite has been executed.
4. **Authentication Error is UNRESOLVED:** The runtime failure `public.lookup_user_by_email_for_auth(unknown) does not exist` has not been repaired.
5. **Production Deployment is NOT APPROVED:** Production release remains unapproved and requires sequential passage through Gates A, B, and C.
6. **Documentation Audit Cycle Ceases:** No further iterative audit steps (e.g. Step 6.3.7) will be generated. The process transitions to human decisions and authorized remediation planning.

---

## 2. Specific Editorial Reconciliations Made in Step 6.3.6.2

### 2.1 Authentication Error Anatomy & Root Cause Classification

The runtime integration failure is:
```
public.lookup_user_by_email_for_auth(unknown) does not exist
```
PostgreSQL error code: `42883` (`undefined_function`).

To eliminate technical confusion, the diagnosis is separated into distinct categories:

#### A. Function Existence and Overload Resolution (Error 42883)
1. **Migration State Divergence:** Migrations `021` or `022` were never applied to the target database instance (or were rolled back), meaning no function named `public.lookup_user_by_email_for_auth` exists in the database catalog (`pg_proc`).
2. **Signature & Parameter Overload Mismatch:**
   - The stored procedure was created with an explicit parameter type (e.g. `public.lookup_user_by_email_for_auth(text)`).
   - When SQLAlchemy / asyncpg executes `SELECT * FROM public.lookup_user_by_email_for_auth(:email)` without explicit parameter typing, the bound parameter has type `unknown`.
   - PostgreSQL attempts function overload resolution. While PostgreSQL can coerce `unknown` literals to `text` in simple contexts, parameterized prepared statements under asyncpg can fail overload resolution if the engine cannot disambiguate candidate types, resulting in `42883`.
   - **Crucial Distinction:** `CAST(:email AS text)` solves parameter typing **only if** the target function with the matching `text` parameter actually exists in the database catalog. `CAST` cannot create a non-existent function.

#### B. Catalog Privileges vs. Function Existence
1. **`EXECUTE` Privilege Mechanics:**
   - In PostgreSQL, if a function exists in `pg_proc` and is visible in the search path or schema-qualified, but the calling role lacks `EXECUTE` privilege, PostgreSQL raises:
     ```
     ERROR: 42501: permission denied for function lookup_user_by_email_for_auth
     ```
   - Missing `EXECUTE` privilege does **not** produce error `42883` (`does not exist`).
2. **Schema `USAGE` Privilege Mechanics:**
   - If the calling role lacks `USAGE` on schema `public`, qualifying the call as `public.lookup_user_by_email_for_auth` raises:
     ```
     ERROR: 42501: permission denied for schema public
     ```
   - Missing schema `USAGE` raises `42501`, not `42883`.
3. **Conclusion:** The observed error `42883` is primarily an **existence or signature-resolution issue**, not an ACL permission denial.

#### C. Downstream Application Contract Validation (Separate Category)
The following contract issues surface only **after** PostgreSQL successfully resolves and invokes the function:
1. **Return Column Mismatches:** Differences between the columns returned by `SETOF record` / `TABLE(...)` and the 7-field projection expected by `UserRepository` (`id`, `email`, `hashed_password`, `role`, `college_id`, `is_active`, `full_name`).
2. **Result Set Cardinality:** Function returning zero rows (user not found) vs. returning multiple rows on duplicate email.
3. **Data Type Mismatches in Return Attributes:** Incompatible Python/Pydantic deserialization of returned UUIDs, enums, or timestamps.

---

### 2.2 D-06: Consolidated Identity Architecture

The decision register for D-06 is consolidated into a single authoritative definition:

- **Proposed Recommendation:** Evaluate `session_user` strictly in the context of the physical connection and connection pooling architecture (SQLAlchemy `AsyncEngine` with `asyncpg`). In a pooled environment where physical database connections are reused across multiple HTTP transactions, `session_user` represents the persistent connection login principal (`college_app_user`), not the ephemeral HTTP application user. Multi-tenant Row-Level Security and application auditing must not assume `session_user` identifies an application user. Row security and audit logging must consume validated, cryptographically signed application context (e.g., `public.current_app_user_id()`).
- **Project Owner Approval:** **REQUIRED** (or formally delegated authority under Evidence Package 6). Audit logging and multi-tenant identity architecture require formal approval.
- **Specialist Advice Domain:** Application Security Engineer & Database Security Architect.

---

### 2.3 D-03: Approval Authority Reconciled

Technical architecture decisions cannot be classified as exempt from Project Owner approval simply because they are technical.
- **Status:** In the absence of an executed Delegation of Authority document (Package 6), no specialist or engineer has legal or organizational authority to sign off on architectural or security designs.
- **Resolution:** The approval authority for D-03 (Worker Authentication and Claim Authorization) is recorded as **PENDING FORMAL DELEGATION**. The Project Owner or their formally delegated authority must decide.

---

### 2.4 D-05: Current Migration Definitions vs. Proposed Future Standard

To avoid overstating compliance, D-05 explicitly distinguishes existing codebase reality from proposed future hardening:

1. **Current Codebase Reality (Migrations 021 & 022):**
   - Migration `021_phase3a42_security_onboarding.sql` defines 9 `SECURITY DEFINER` functions that explicitly configure:
     ```sql
     SET search_path = pg_catalog, public, auth_private
     ```
     This configuration uses a mutable multi-schema search path and relies on schema search ordering.
   - Migration `022_minimize_auth_lookup.sql` defines `lookup_user_by_email_for_auth` with:
     ```sql
     SET search_path = pg_catalog
     ```
     This function references `public.users` using schema qualification.
   - **Finding:** Existing migration 021 functions do **not** satisfy the proposed strict single-schema standard.

2. **Proposed Future Hardening Standard:**
   - Restrict all `SECURITY DEFINER` functions to:
     ```sql
     SET search_path = pg_catalog
     ```
   - **Mandatory Consequence:** When `search_path` contains only `pg_catalog`, every reference to application tables, views, custom types, and application functions in `public` or `auth_private` **must be fully schema-qualified** (e.g., `public.users`, `auth_private.rls_context_keys`), otherwise PostgreSQL parser resolution will fail.
   - Revoke `PUBLIC` execute permissions, grant `EXECUTE` exclusively to dedicated `NOLOGIN` capability roles, and ensure non-superuser ownership.

---

### 2.5 Structural Deduplication & Unified Package Accounting

- **Six Outstanding Evidence Packages:** Consistently recorded across all sections as **four missing** (Packages 1, 2, 4, 6) and **two incomplete** (Packages 3, 5).
- **Canonical Decision Register:** Contains exactly one canonical entry for each of D-01 through D-22, all marked `[PENDING HUMAN DECISION]`.
- **Deduplication:** Removed repeated declarations, duplicated table rows, and redundant readiness matrices.

---

## 3. Canonical D-01 through D-22 Decision Register

```
Status Legend:
[REC] = Recommended Technical Position
[EVI] = Repository Evidence Available
[UNV] = Database Evidence Unverified
[DEP] = Unresolved Dependencies
[AUT] = Decision Approval Authority
[SPE] = Specialist Advice Domain
[BLK] = Blocks Gate A
```

---

### D-01: Migration History and Branch Selection
- **[REC]:** Branch B (Forward-Only Corrective Migration `023_...`) is the conservative default while database history is unverified. Branch A (destructive baseline consolidation) may be considered only if written attestation proves migrations 001–022 were never executed in any environment.
- **[EVI]:** Migrations 001–022 present in repository; CI executes in-memory SQLite; README provides manual SQL Editor instructions.
- **[UNV]:** Live database migration execution history (`schema_migrations`) is uninspected.
- **[AUT]:** Project Owner (or formally delegated authority).
- **[SPE]:** Database Release Engineer (Technical Advice).
- **[DEP]:** Authoritative written deployment ledger (Package 1).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-02: Shared vs. Tenant-Isolated Worker Architecture
- **[REC]:** Mandatory database job claims and unprivileged worker database principal; operational choice between dedicated per-tenant worker processes vs. shared worker pool with subprocess isolation.
- **[EVI]:** Shared Celery queue and Redis URL in `celery_app.py`; PyMuPDF document extraction in `document_tasks.py`.
- **[UNV]:** Worker queue memory footprint and performance under isolated execution unverified.
- **[AUT]:** Project Owner (Infrastructure cost and complexity sign-off).
- **[SPE]:** Worker Platform Engineer & Security Architect (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-03: Worker Authentication and Claim Authorization
- **[REC]:** Worker connects with authenticated login principal, assumes `NOLOGIN` capability role `college_worker_role`, and calls `claim_job()` to obtain a time-bounded cryptographic lease token bound to the tenant.
- **[EVI]:** Tasks currently receive raw `college_id` via Celery JSON kwargs; session sets ambient GUC without database validation.
- **[UNV]:** Claim function and lease verification logic do not exist in live database catalog.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** Database Security Architect (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3) & Delegation of Authority (Package 6).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-04: Job Lease, Heartbeat, Retry, Duplicate, and Crash Handling
- **[REC]:** 5-minute initial lease, 60-second heartbeat, max 3 retries with exponential backoff, 1-hour hard dead-letter timeout, idempotent database upserts.
- **[EVI]:** `crawl_jobs` and `documents` have basic status columns, but lack lease expiration, heartbeat timestamps, and dead-letter queues.
- **[UNV]:** Database schema columns for lease tracking unverified in live catalog.
- **[AUT]:** Project Owner (Acceptance of recovery latency SLA).
- **[SPE]:** Distributed Systems Engineer (Technical Advice).
- **[DEP]:** Worker Deployment Architecture Specification (Package 3).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-05: SECURITY DEFINER Ownership, Grants, search_path, and RLS
- **[REC]:** Adopt strict standard for future migrations: dedicated `NOLOGIN` definer capability roles; strict `SET search_path = pg_catalog`; fully schema-qualified object references; revoke `PUBLIC` execute; zero superuser ownership. Existing 021 functions do not yet meet this standard.
- **[EVI]:** 13 active functions across migrations 021 and 022; 9 definer functions in 021 set multi-schema search path; 022 sets `pg_catalog`.
- **[UNV]:** Live catalog `pg_proc.proowner`, `proacl`, and `pg_namespace` ACLs remain unverified.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** PostgreSQL Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-06: Identity Consumers: session_user, current_user, and Signed Context
- **[REC]:** Evaluate `session_user` strictly in the context of the connection pooling architecture. Pooled connections mean `session_user` represents the persistent connection login principal (`college_app_user`), not the HTTP application user. RLS and audit logging must consume validated, signed context (`public.current_app_user_id()`).
- **[EVI]:** `session.py` sets HMAC GUCs; migration 021 checks signature; migration 021 trigger checks `current_user <> 'postgres'`. `session_user` is not referenced in repository SQL.
- **[UNV]:** Live database views, triggers, and procedures unverified for hidden `session_user` calls.
- **[AUT]:** Project Owner (Auditing and multi-tenant identity architecture sign-off).
- **[SPE]:** Application Security Engineer & Database Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-07: Direct-Login Testing Requirement
- **[REC]:** Dedicated unprivileged test harness login (`college_test_harness`) executing `SET ROLE college_app_user` for RLS testing. Direct-login testing reserved for connection auth verification. Capability roles remain `NOLOGIN`.
- **[EVI]:** Tests currently run against SQLite in CI or connect via superuser in local scripts.
- **[UNV]:** Test harness credentials and role grants unverified in test catalog.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** Security Test Engineer (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-08: PostgreSQL 17 Role-Membership Closure and Protected-Role Allowlist
- **[REC]:** Enforce protected-role allowlist; execute recursive cycle-safe CTE checking `set_option`, `inherit_option`, and `admin_option` in `pg_auth_members` to prove zero paths to superuser.
- **[EVI]:** Step 4 recursive query specification; migration 018 role creation.
- **[UNV]:** Live `pg_auth_members` catalog state unverified.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** PostgreSQL Database Administrator (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-09: Unprivileged Negative-Test Principal
- **[REC]:** Multi-tiered negative test suite executed via an unprivileged test principal covering ACL denials, RLS policy enforcement, and privilege escalation vectors. Proposed conditional test expectations include:
  - Table ACL denials raising error `42501` (`insufficient_privilege`).
  - Cross-tenant `SELECT` returning zero rows (RLS `USING` clause filtering).
  - Cross-tenant `INSERT` raising error `42501` (RLS `WITH CHECK` clause violation).
  - Cross-tenant `UPDATE` affecting zero rows (`USING` clause filtering rows prior to evaluation).
  - Tenant-violating `UPDATE` raising error `42501` (`WITH CHECK` clause violation).
  - Unauthorized `ALTER ROLE ... SUPERUSER` or `SET ROLE` raising error `42501`.
  *Note:* Each outcome is a conditional test expectation; actual runtime behavior depends on applicable policies, ACLs, role attributes, execution identity, and seeded data. All expectations require verification in the authorized disposable test environment.
- **[EVI]:** Existing tests test tenant switching within single connection; lack separate unprivileged login principal.
- **[UNV]:** Negative test fixtures unverified in database catalog.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** QA / Security Test Engineer (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-10: Signing-Key Storage, Access, and Rotation
- **[REC]:** External secret store; dual-key schema (`ACTIVE` and `PREVIOUS`) in `auth_private.rls_context_keys`; overlap window derived from token TTL, deployment duration, and cache TTL; multi-instance cache invalidation; emergency `REVOKED` state.
- **[EVI]:** Migration 021 has unique partial index preventing dual active keys; `session.py` requires 32-byte secret.
- **[UNV]:** Contents of `auth_private.rls_context_keys` unverified in live catalog.
- **[AUT]:** Project Owner (Key custody policy approval).
- **[SPE]:** Key Management Specialist & Application Security Engineer (Technical Advice).
- **[DEP]:** Key Management Runbook (Package 2).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-11: Password-Reset Email Delivery Provider or Deferral
- **[REC]:** Formally defer and disable self-service password reset in production until a contracted transactional email provider with verified SPF/DKIM/DMARC is integrated.
- **[EVI]:** `email_transport.py` implements mock/logging transport; reset tokens are discarded or logged.
- **[UNV]:** N/A (application service layer).
- **[AUT]:** Project Owner (Product decision to disable feature vs contract provider).
- **[SPE]:** Communications Privacy Specialist (Technical Advice).
- **[DEP]:** None (service-level business contract).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-12: Notification Email Retention and Data Minimization
- **[REC]:** Institutional 30-day retention schedule for notification delivery logs; automated scrubbing of recipient email addresses, tokens, and bodies after dispatch; Celery purge task.
- **[EVI]:** `notification.py` model; no automated pruning task in repository.
- **[UNV]:** Live notification table records unverified.
- **[AUT]:** Project Owner (Written approval of 30-day retention schedule).
- **[SPE]:** Data Privacy & Compliance Officer (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-13: Public College Registration versus Super Admin-Only Registration
- **[REC]:** Public registration creates records in `college_registrations` with status `PENDING` only. Provisioning active tenants in `colleges` and creating admin accounts is strictly restricted to Super Admin approval.
- **[EVI]:** Public registration page in `apps/admin-frontend`; migration 021 defines `submit_public_college_registration()`.
- **[UNV]:** Registration table RLS policies unverified in live catalog.
- **[AUT]:** Project Owner (Onboarding workflow business approval).
- **[SPE]:** Application Security Engineer (Technical Advice).
- **[DEP]:** Registration approval workflow specification.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-14: EDITOR and VIEWER Permission Matrix
- **[REC]:** Fail-closed RBAC: `VIEWER` is strict read-only; `EDITOR` can upload documents and edit drafts but cannot publish knowledge chunks or delete documents; `COLLEGE_ADMIN` holds publish/delete authority.
- **[EVI]:** Role enums in migration 003 define basic roles; intermediate dashboard roles lack database-level grants.
- **[UNV]:** Enum types and table grants unverified in live catalog.
- **[AUT]:** Project Owner (Product RBAC matrix sign-off).
- **[SPE]:** Application Security Architect (Technical Advice).
- **[DEP]:** Formal RBAC permission matrix document.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-15: Audit Payload and AI Telemetry Allowlists and Redaction
- **[REC]:** Strict key allowlist for audit JSONB payloads; PII/credential scrubber; AI telemetry restricted to aggregate metrics (`tokens`, `latency_ms`) and error codes; raw prompts and stack traces prohibited.
- **[EVI]:** Migration 008 creates `audit_logs` and `ai_provider_events`; `_log_telemetry` logs API metrics.
- **[UNV]:** Live telemetry table rows unverified for unredacted data.
- **[AUT]:** Project Owner (Telemetry data governance sign-off).
- **[SPE]:** Data Privacy Officer & AI Operations Lead (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-16: Creation of a New Disposable Supabase-Compatible Test Environment
- **[REC]:** Provision fresh, isolated local Supabase CLI stack on loopback interface (`127.0.0.1`); enforce fail-closed connection guards on all test URLs; strictly prohibit cloud connections.
- **[EVI]:** `tests/config.py` loads `.env` targeting remote cloud Supabase; Step 2 vanilla PostgreSQL container lacked Supabase `auth` schemas.
- **[UNV]:** Local Supabase test stack not yet provisioned.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** DevOps / Platform Engineer & PostgreSQL Security Architect (Technical Advice).
- **[DEP]:** Local Disposable Stack Specification (Package 5).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-17: Implementation Authorization and Separate Production Approval
- **[REC]:** Enforce strict 4-stage gate separation: Gate A (Design Approval) $\to$ Gate B (Test Implementation) $\to$ Gate C (Database Validation) $\to$ Production Approval.
- **[EVI]:** All audit reports record zero implementation authorization.
- **[UNV]:** N/A (governance control).
- **[AUT]:** Project Owner (Formal delegation of authority sign-off).
- **[SPE]:** Lead System Architect (Technical Advice).
- **[DEP]:** Delegation of Authority Document (Package 6).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-18: Application Identity Model and Supabase auth.uid() Boundary
- **[REC]:** Standardize on custom HMAC-signed application context (`public.current_app_user_id()`); deprecate and remove application dependencies on Supabase `auth.uid()`.
- **[EVI]:** FastAPI issues custom JWTs; migration 021 implements context functions.
- **[UNV]:** Live catalog unverified for lingering `auth.uid()` references.
- **[AUT]:** Project Owner or formally delegated authority (Package 6 required).
- **[SPE]:** Lead System Architect & Identity Architect (Technical Advice).
- **[DEP]:** Architectural Decision Record (ADR) sign-off.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-19: Visitor Token Lifetime and Anonymous Feedback
- **[REC]:** 32-byte visitor bearer token; 24-hour absolute non-sliding expiration; matching token required for chat feedback; adopt `v2` context payload binding `visitor_token_hash`.
- **[EVI]:** `chat.py` generates visitor tokens; migration 021 checks `app.chat_visitor_token` GUC.
- **[UNV]:** Live chat session rows and token expiration state unverified.
- **[AUT]:** Project Owner (Student user experience policy sign-off).
- **[SPE]:** Application Security Engineer (Technical Advice).
- **[DEP]:** Anonymous Chat API Specification.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-20: Guest Support-Ticket Permissions
- **[REC]:** Guest support tickets are strictly create-only; zero database read/update/reply permissions; staff follow up exclusively via email.
- **[EVI]:** `support_service.py` allows unauthenticated creation; `SupportTicket` model permits nullable `user_id`.
- **[UNV]:** RLS policies on `support_tickets` unverified in live catalog.
- **[AUT]:** Project Owner (Support workflow policy approval).
- **[SPE]:** Security Architect (Technical Advice).
- **[DEP]:** Support workflow policy document.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-21: College Chat Analytics and Raw Conversation Access
- **[REC]:** College Admins receive aggregate metrics only; zero direct browse access to raw student chat logs or transcripts unless escalated to a ticket.
- **[EVI]:** `analytics_service.py` provides aggregated queries; `college-admin/analytics/page.tsx` displays charts.
- **[UNV]:** Analytics views and RLS policies unverified in live catalog.
- **[AUT]:** Project Owner (Student privacy policy approval).
- **[SPE]:** Data Privacy Officer (Technical Advice).
- **[DEP]:** Data Retention & Privacy Schedule (Package 4).
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

### D-22: Sensitive User-Column Access and Authentication Lookup Contract
- **[REC]:** Enforce minimal 7-field projection via `public.lookup_user_by_email_for_auth(CAST(:email AS text))`; introduce dedicated `college_auth_role` with exclusive `EXECUTE` and dedicated connection pool (`DATABASE_AUTH_ROLE_URL`); revoke `EXECUTE` from `college_app_user`. `CAST(:email AS text)` solves parameter typing only if the text-signature routine exists in the catalog.
- **[EVI]:** Migration 022 implements 7-field projection; `UserRepository` executes function; test logs show `lookup_user_by_email_for_auth(unknown) does not exist`.
- **[UNV]:** Live database function existence, parameter types, return projection, and catalog grants remain unverified.
- **[AUT]:** Project Owner (Infrastructure and dedicated pool approval).
- **[SPE]:** Application Security Engineer & Database Security Architect (Technical Advice).
- **[DEP]:** Dedicated Authentication Role Architecture Specification.
- **[BLK]:** **YES**.
- **[STATUS]:** **`[PENDING HUMAN DECISION]`**

---

## 4. Outstanding Evidence Packages Accounting

There are **six outstanding evidence packages: four missing and two incomplete.**

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

## 5. Consolidated Specialist Advice & Governance Authority Traceability

Technical specialists provide advisory evaluations only. Specialist advice does not constitute business approval. In the absence of an executed Delegation of Authority document (Package 6), final decision authority resides exclusively with the Project Owner.

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
| 3  | Database Security Architect          | D-03, D-05, D-06,   | Reviews worker cryptographic claims, SECURITY DEFINER       | Final approval authority not established; Project Owner or  |
|    |                                      | D-22                | privilege model, search_path, and dedicated auth role DDL.  | formally delegated authority must decide.                   |
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

## 6. Gate A Readiness Matrix

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

## 7. Explicit Operational and Deployment Gates

```
================================================================================
EXPLICIT GOVERNANCE DIRECTIVE:
1. GATE A (DESIGN & GOVERNANCE APPROVAL): NOT COMPLETE.
   - Requires formal written sign-offs on D-01 through D-22.
   - Requires completion of the 6 evidence packages.
2. GATE B (IMPLEMENTATION AUTHORIZATION): STRICTLY NOT AUTHORIZED.
   - Zero application code, migration, or configuration modifications permitted.
   - Gate B requires separate, written authorization following Gate A certification.
3. GATE C (ISOLATED DATABASE VALIDATION): STRICTLY NOT VALIDATED.
   - Zero SQL execution, container operations, or database connections permitted.
   - Validation must take place exclusively inside an authorized local disposable Supabase stack.
4. AUTHENTICATION ERROR STATUS: UNRESOLVED.
   - public.lookup_user_by_email_for_auth(unknown) does not exist is not repaired.
5. PRODUCTION DEPLOYMENT: STRICTLY NOT APPROVED.
================================================================================
```

---

## 8. Controlled Practical Remediation Sequence

The following 10-step sequence is proposed for diagnosing and remediating the authentication error. **This is a proposed sequence only; no step requiring database access or code modification may be executed without separate Gate B/C authorization:**

1. **Obtain Authoritative Migration History:** Collect the certified migration execution history (`schema_migrations` or migration table) across all target environments (Evidence Package 1).
2. **Authorize Isolated Disposable Test Stack:** Secure formal approval to provision an isolated, local disposable Supabase-compatible container stack bound exclusively to loopback (`127.0.0.1`) (Evidence Package 5).
3. **Reproduce Baseline Migration State:** Apply migrations sequentially in the isolated test stack to reproduce the target database state.
4. **Inspect Live Catalog Objects:** Query `pg_proc`, `pg_namespace`, `pg_roles`, and `pg_shdescription` in the disposable stack to verify function existence, argument types, return columns, function ownership, and explicit `GRANT EXECUTE` rights.
5. **Reconcile Database Contract with Application Code:** Compare the live database contract against `UserRepository.get_user_for_auth_by_email`, `AuthService.authenticate_user`, and the FastAPI auth endpoints.
6. **Identify Exact Root Cause:** Determine definitively whether the issue is migration absence, parameter type casting, privilege revocation, or schema visibility.
7. **Formulate Minimal Forward-Only Remediation:** Author the smallest safe, forward-only SQL migration (e.g. `023_...`) to repair the function definition, grants, and search path if migration history remains ambiguous.
8. **Execute Isolated Authentication Tests:** Test user authentication, password verification, and token issuance inside the disposable test environment.
9. **Execute Negative & Tenant Isolation Tests:** Verify that an unprivileged test principal cannot access sensitive user columns directly and that cross-tenant RLS boundaries hold.
10. **Obtain Production Deployment Approval:** Present verified test evidence and secure formal human sign-off before applying any change to staging or production environments.

---

## 9. Final Handoff and Next Practical Milestones

### 9.1 Summary of Editorial Corrections Completed
1. Reconciled authentication error anatomy: separated existence/resolution (`42883`) from privileges (`42501`) and downstream contract validation.
2. Consolidated D-06 into a single authoritative definition reflecting connection pooling realities.
3. Reconciled D-03 approval authority: marked pending formal delegation rather than exempt.
4. Reconciled D-05: distinguished current migration 021 reality from the proposed future `SET search_path = pg_catalog` standard requiring schema qualification.
5. Deduplicated document structure: unified package accounting (four missing, two incomplete) and single canonical register.

### 9.2 Unresolved Documentary Issues
- **Live Catalog State:** Cannot be determined statically without live database inspection during Gate C.
- **Evidence Packages:** Packages 1, 2, 4, and 6 are missing; Packages 3 and 5 are incomplete.
- **Delegation of Authority:** Package 6 is missing; all authority rests with the Project Owner until formally delegated.

### 9.3 Package and Decision Accounting
- **Evidence Packages:** 6 total (4 Missing, 2 Incomplete).
- **Decision Register:** 22 total (D-01 through D-22: all `[PENDING HUMAN DECISION]`).

### 9.4 Final Governance Posture
- **Gate A:** NOT COMPLETE
- **Gate B:** NOT AUTHORIZED
- **Gate C:** NOT VALIDATED
- **Auth Error:** UNRESOLVED
- **Production:** NOT APPROVED

### 9.5 The Next Practical Milestone
The documentation review cycle is complete. **No further documentation audits are recommended.** The project transitions to:
1. **Human Gate A Decisions:** Delivery of this handoff package to the Project Owner to execute formal decisions on D-01 through D-22 and author the missing evidence packages.
2. **Step 7 Implementation Plan Formulation:** Authoring a separately scoped Step 7 implementation plan to request formal Gate B authorization to provision the local disposable Supabase test container and execute the controlled diagnostic sequence.
