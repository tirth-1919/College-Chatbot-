# Phase 3A.4.4B — Step 6: Human Decision Resolution and Gate A Preparation

**Current Status:** `READY FOR HUMAN DECISION — GATE A NOT COMPLETE — IMPLEMENTATION NOT AUTHORIZED — DATABASE NOT VALIDATED`  
**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Technical Project Reviewer  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Document:** [Step 5 Human Review and Decision Approval Package](./phase3a4.4b-step5-human-review-and-decision-approval.md)

---

## 1. Executive Status

This document establishes the comprehensive **Human Decision Resolution Package** for Phase 3A.4.4B, covering all twenty-two architectural, operational, and security decisions (**D-01 through D-22**) identified in Step 5. 

The primary objective of Step 6 is to equip the project owner and designated technical specialists with the exact evidence, risk profiles, recommended least-privilege positions, viable alternatives, and documentary requirements needed to resolve each decision before implementation is contemplated.

### Mandatory Operational Boundaries

1. **Zero Implementation / Zero Modification:** This is a documentation, audit, and decision-preparation artifact. No application code, SQL migrations, database roles, table privileges, RLS policies, Docker containers, volumes, configuration files, or environment secrets have been modified, created, or executed.
2. **Migration History Default (Branch B):** In strict accordance with the critical migration-history invariant, Branch A cannot and will not be selected without authoritative, written confirmation from the accountable release owner certifying that migrations `001_extensions.sql` through `022_minimize_auth_lookup.sql` have never been applied, partially applied, released, or deployed in *any* environment (development, staging, shared, or production). Because no such written attestation exists, **Branch B remains the mandatory default pending human decision**.
3. **Database Test Environment Boundary:** The vanilla PostgreSQL test container described in Step 2 lacks the Supabase `auth` schema, `auth.uid()` functions, and native roles (`anon`, `authenticated`, `service_role`). Reusing that container or volume is strictly prohibited. A dedicated, disposable, local Supabase-compatible test stack must be separately authorized and provisioned for future validation.
4. **Independent Gate Boundary:**
   - **Gate A (Design Approval):** **NOT COMPLETE** (22 decisions pending human and specialist approval).
   - **Gate B (Implementation Authorization):** **NOT AUTHORIZED** (no written authorization granted; implementation prohibited).
   - **Gate C (Database Validation):** **NOT VALIDATED** (no migrations or RLS validations executed).
   - **Production Release:** **NOT APPROVED** (strictly prohibited).

---

## 2. Source Inspection & Evidence Limitations

### Inspected Artifacts
1. **Prior Audit & Planning Documents:**
   - [Step 5 Human Review and Decision Approval Package](./phase3a4.4b-step5-human-review-and-decision-approval.md)
   - [Step 4 Controlled Implementation Plan](./phase3a4.4b-step4-controlled-implementation-plan.md)
   - [Step 4 Correction Summary](./phase3a4.4b-step4-correction-summary.md)
   - [Step 3 Final Approval Package](./phase3a4.4b-step3-final-approval-package.md)
   - [Step 3.1 Security Gap Closure Addendum](./phase3a4.4b-step3.1-security-gap-closure.md)
   - [Step 2 Migration Validation Report](./phase3a4.4b-step2-migration-validation-report.md)
2. **Database Specifications & SQL Migrations:**
   - [database/README.md](../../database/README.md)
   - Migrations `database/migrations/001_extensions.sql` through `database/migrations/022_minimize_auth_lookup.sql`
   - Specifically cross-checked: `017_row_level_security_policies.sql`, `018_create_application_role.sql`, `019_complete_rls_policies.sql`, `020_revoke_anon_grants.sql`, `021_phase3a42_security_onboarding.sql`, `022_minimize_auth_lookup.sql`
3. **Application & Infrastructure Code:**
   - `backend/app/database/session.py` (HMAC context signing, `set_rls_context`)
   - `backend/app/database/connection.py` (async engine, connection pool reset hooks)
   - `backend/app/models/` (`user.py`, `college.py`, `chat.py`, `registration.py`, `ai.py`, `audit.py`)
   - `backend/app/api/v1/` (`auth.py`, `colleges.py`, `chat.py`, `college_admin.py`, `super_admin.py`, `support.py`)
   - `backend/app/tasks/` (`celery_app.py`, `crawler_tasks.py`, `document_tasks.py`, `knowledge_tasks.py`)
   - CI/CD workflows: `.github/workflows/ci.yml`, `.github/workflows/cd.yml`

### Evidence Classifications Applied Throughout This Report
- **Confirmed by Inspected Source:** Verified directly by static analysis of repository files. Verifies code syntax and static definitions only; does *not* prove runtime execution or database catalog state.
- **Confirmed by Existing Documentation:** Documented in prior reports (Steps 2–5). Not independently re-executed.
- **Proposed but Not Executed:** Recommended architectural design, migration step, catalog assertion, or test suite described in planning documents but not executed.
- **Requires Human Confirmation:** Blocked on an accountable human owner's decision, policy sign-off, or documentary proof.
- **Unknown or Unavailable:** Cannot be determined from workspace files or local documentation without live production or environment access (which is prohibited).

---

## 3. Human Decision Register (D-01 through D-22)

Every decision is currently **PENDING HUMAN DECISION**. No decision has been resolved, pre-approved, or bypassed.

```
Status Legend:
[REC] = Recommended by Technical Review
[OWN] = Accepted by Project Owner (Pending)
[SPE] = Approved by Accountable Specialist (Pending)
[EVI] = Documentary Evidence Received (Pending)
[RES] = Decision Resolved (Pending)
```

| ID | Title / Scope | Review Rec. | Owner Status | Specialist Status | Evidence Status | Overall Status |
|:---|:---|:---:|:---:|:---:|:---:|:---:|
| **D-01** | Migration History & Branch Selection | Branch B | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-02** | Shared vs. Tenant-Isolated Workers | Tenant-Isolated | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-03** | Worker Authentication & Claim Auth | DB-Authenticated Pool | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-04** | Job Lease, Heartbeat & Retry Recovery | Bounded Lease / Hash | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-05** | SECURITY DEFINER Ownership & RLS | NOLOGIN / Search-Path | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-06** | Identity Consumers (session_user, etc.) | Explicit Consumer Map | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-07** | Direct-Login Testing Requirement | Disposable Login if Used | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-08** | PG 17 Role Closure & Allowlist | Recursive Transitive Check | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-09** | Unprivileged Negative-Test Principal | Dedicated Non-App Role | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-10** | Signing-Key Storage & Rotation | External Secret Vault | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-11** | Password-Reset Email Delivery | Defer or Provider Sign-off | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-12** | Notification Email Data Retention | Minimized / Bounded | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-13** | Public Registration vs. Super Admin | Pending Registration Only | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-14** | EDITOR & VIEWER Permission Matrix | Read-Only Default | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-15** | Audit & AI Telemetry Redaction | Strict Allowlist Schema | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-16** | Disposable Supabase Test Environment | Isolated Local Stack | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-17** | Implementation & Production Gates | Separate Gate Approvals | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-18** | Application Identity vs. auth.uid() | Custom Signed Context | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-19** | Visitor Token Lifetime & Feedback | 24h Fixed / Hash Bound | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-20** | Guest Support-Ticket Capabilities | Create-Only Boundary | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-21** | College Chat Analytics vs. Raw Logs | Aggregate-Only Admin | Pending | Pending | Pending | **PENDING HUMAN DECISION** |
| **D-22** | Sensitive User-Column Projections | 7-Field Auth Projection | Pending | Pending | Pending | **PENDING HUMAN DECISION** |

---

## 4. Comprehensive Decision Analyses (D-01 to D-22)

### D-01 — Migration History and Branch A / Branch B Selection

- **Current Step 5 Status:** PENDING (Defaulting to Branch B).
- **Relevant Repository Evidence:**
  - Files `database/migrations/001_...` through `022_...` exist in the repository tree.
  - `database/README.md` outlines manual execution instructions for Supabase SQL Editor.
  - `.github/workflows/cd.yml` contains a placeholder deployment step with commented SSH commands; no automated migration pipeline is present.
  - `.github/workflows/ci.yml` runs unit tests against an in-memory SQLite database (`sqlite+aiosqlite:///:memory:`).
  - Step 2 test database did not execute migrations 001–022.
- **Exact Unresolved Question:** Have migrations 001 through 022 ever been applied, partially applied, executed manually via SQL Editor, or deployed to *any* hosted Supabase project, staging database, or production cluster?
- **Recommended Option & Rationale:** **Branch B (Forward-Only Corrective Migration)**. Unless written, unequivocal proof confirms that migrations 001–022 were never executed anywhere, rewriting existing migrations (Branch A) risks catastrophic divergence between repository files and deployed database catalogs. Branch B preserves historical integrity and introduces a clean, forward-only corrective migration (e.g., `023_...`) following an authoritative schema inventory.
- **Alternative Options:**
  - *Branch A (In-Place Rewrite):* Edit migrations 017–022 directly in place. Permissible *only* if formal written attestation proves zero external environments ever executed 001–022.
- **Security & Operational Risks:** Choosing Branch A on an environment that already ran 017–022 causes irreversible state divergence, checksum failure in future migration runners, and potentially leaves dangling or broken RLS policies.
- **Who Must Approve:** Both Project Owner and Accountable Database/Release Owner.
- **Exact Human Approval Required:** Formal written attestation from the Release Owner certifying either (a) zero execution in any environment, or (b) approval of forward-only Branch B schema remediation.
- **Evidence Required to Resolve:** Signed deployment ledger or release audit report covering all hosted Supabase projects and staging/production databases.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-02 — Shared versus Tenant-Isolated Worker Architecture

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/tasks/celery_app.py` defines a shared Celery task queue over Redis.
  - `backend/app/tasks/crawler_tasks.py`, `document_tasks.py`, and `knowledge_tasks.py` instantiate database sessions via `tenant_session(college_id)`.
  - Sessions run under the single shared database user (`college_app_user` or connection string default).
- **Exact Unresolved Question:** Will asynchronous background tasks (crawling, OCR, document chunking, embedding generation) execute in a single shared Celery worker pool, or will worker processes and queues be strictly partitioned per tenant or bounded trust cohort?
- **Recommended Option & Rationale:** **Tenant-Isolated Workers** (or explicitly approved trust cohorts). In a shared worker pool, an application-layer vulnerability or memory corruption exploit in a complex PDF parser (PyMuPDF) or HTML extractor allows cross-tenant data compromise. Isolating worker processes/credentials strictly bounds the blast radius.
- **Alternative Options:**
  - *Option 2 (Single Shared Worker Pool with Compensating Controls):* Continue using a shared Celery pool, but enforce database-level job-claim tokens, separate PostgreSQL connection credentials, and unprivileged sandboxed sub-processes.
  - *Option 3 (Bounded Trust Cohorts):* Group low-risk tenants together while isolating high-compliance institutional tenants in dedicated queues.
- **Security & Operational Risks:** Shared workers risk cross-tenant data leakage if Celery memory leaks or background state persists across task executions. Tenant-isolated workers increase infrastructure operational overhead and Redis queue management complexity.
- **Who Must Approve:** Technical Specialist (Security Architect) and Project Owner (Infrastructure Cost/Operations).
- **Exact Human Approval Required:** Written sign-off on the worker isolation boundary and acceptance of residual operational/blast-radius trade-offs.
- **Evidence Required to Resolve:** Documented worker deployment specification, queue routing topology, and credential boundary plan.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-03 — Worker Authentication and Claim Authorization

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Tasks receive `college_id: uuid.UUID` and `job_id: uuid.UUID` as raw JSON arguments from Celery Redis messages.
  - Database queries rely entirely on `tenant_session(college_id=college_id)` setting the GUC `app.current_college_id`.
  - There is no cryptographic claim token or database-verified lease currently required to access or update job rows.
- **Exact Unresolved Question:** How does the database verify that a worker connecting to process a job is genuinely authorized to claim and execute that specific job for that specific tenant?
- **Recommended Option & Rationale:** **PostgreSQL-Authenticated Pool with Database Claim Function**. Workers connect using a distinct PostgreSQL identity mapped to a dedicated `NOLOGIN` capability role (e.g., `college_worker_role`). A `SECURITY DEFINER` claim function (`claim_job(p_job_id, p_lease_duration)`) must verify tenant ownership, issue a short-lived cryptographic lease hash, and bind the session to that tenant alone.
- **Alternative Options:**
  - *Option 2 (Signed Worker Tokens):* The API signs an HMAC job-execution token containing `(job_id, tenant_id, expiry)`, which the worker presents to the database via signed context.
  - *Option 3 (Caller-Asserted Identity — Current Legacy):* Worker asserts `college_id` via GUC without database validation (Unsafe: rejected by security review).
- **Security & Operational Risks:** Without database-enforced claims, any compromised worker or rogue Celery task can forge a GUC to read or corrupt any other tenant's document processing pipeline.
- **Who Must Approve:** Technical Specialist (Database Security Architect).
- **Exact Human Approval Required:** Formal sign-off on the worker claim function signature, credential provisioning method, and capability role privileges.
- **Evidence Required to Resolve:** Approved SQL definition for `claim_job`, schema grant matrix, and secret separation runbook.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-04 — Job Lease, Heartbeat, Retry, Duplicate, and Crash Handling

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `crawl_jobs` and `documents` have status columns (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`).
  - Tasks lack database-level lease timestamps, heartbeat callbacks, or dead-letter queue limits.
  - If a Celery worker dies mid-extraction, the job remains stuck in `PROCESSING` indefinitely.
- **Exact Unresolved Question:** What are the exact numerical thresholds for job lease duration, heartbeat intervals, maximum execution timeouts, retry limits, and crash reclamation?
- **Recommended Option & Rationale:** **Bounded Lease with Idempotency & Database Dead-Letter Queue**.
  - Default lease duration: **5 minutes**.
  - Heartbeat interval: **60 seconds** (updates `lease_expires_at`).
  - Hard task timeout: **1 hour** (triggers terminal dead-lettering).
  - Max retries: **3 attempts** with exponential backoff.
  - At-least-once processing semantics backed by idempotent database upserts.
- **Alternative Options:**
  - *Option 2 (Long Static Lease):* 1-hour static lease without heartbeats (Risks delayed failure recovery if worker crashes early).
  - *Option 3 (Optimistic Locking):* Version-column increment on update (Does not resolve worker death or crash timeout).
- **Security & Operational Risks:** Overly aggressive timeouts cause premature lease reclamation and duplicate concurrent processing. Overly long leases stall tenant ingestion queues when workers encounter out-of-memory crashes on oversized files.
- **Who Must Approve:** Technical Specialist (Worker Platform Engineer) and Project Owner.
- **Exact Human Approval Required:** Agreement on lease parameters, retry counts, and dead-letter alert thresholds.
- **Evidence Required to Resolve:** Documented operational SLA, task retry policy, and synthetic test specification for lease expiry and duplicate handling.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-05 — SECURITY DEFINER Ownership, Grants, search_path, and RLS

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Migration 021 defines 12 `SECURITY DEFINER` functions in schemas `auth_private` and `public`.
  - Migration 022 redefines `public.lookup_user_by_email_for_auth(text)` as `SECURITY DEFINER` with `SET search_path = pg_catalog`.
  - Function ownership in 022 is dynamically set to `v_function_owner` (the role running the migration, typically `postgres` or `supabase_admin`).
  - Function grants in 021/022 revoke from `PUBLIC` and grant to `college_app_user`.
- **Exact Unresolved Question:** Which exact database role will own each `SECURITY DEFINER` function, and how will schema permissions, `search_path`, and function execution privilege chains be constrained?
- **Recommended Option & Rationale:** **Dedicated Unprivileged NOLOGIN Function Owner Role**. Create a dedicated, non-login role (e.g., `college_definer_auth`, `college_definer_reg`) owning only the specific tables required for that subsystem. Every function must enforce `SET search_path = pg_catalog` (with explicitly qualified schema calls), explicitly revoke `PUBLIC` execute permissions, and enforce fail-closed input sanitization. Never allow `postgres` or `supabase_admin` (superuser/BYPASSRLS) to own functions callable by application roles.
- **Alternative Options:**
  - *Option 2 (Single Definer Owner):* A single `college_definer_owner` role for all functions (Less granular, but avoids superuser ownership).
  - *Option 3 (Default Migration Owner — Current):* Functions remain owned by the deployment superuser (High risk: privilege escalation vulnerability).
- **Security & Operational Risks:** If a `SECURITY DEFINER` function is owned by a superuser or BYPASSRLS role, any SQL injection or mutable `search_path` vulnerability inside the function allows the caller to bypass RLS and gain full cluster compromise.
- **Who Must Approve:** Technical Specialist (PostgreSQL Security Architect).
- **Exact Human Approval Required:** Architectural approval of the function-owner role hierarchy, search-path policy, and default ACL revocations.
- **Evidence Required to Resolve:** Catalog query design proving function owners have `rolsuper=false` and `rolbypassrls=false`, and a full grant matrix.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-06 — Identity Consumers: session_user, current_user, current_role, and Signed Context

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/database/connection.py` establishes async connections using `DATABASE_APP_ROLE_URL` or `DATABASE_URL`.
  - `backend/app/database/session.py` invokes `set_config` to set `app.current_user_id`, `app.current_college_id`, `app.is_super_admin`, and HMAC signature.
  - Migration 021 functions check `current_setting('app.request_context_signature', true)`.
  - Migration 017 policies referenced `auth.uid() = id`.
- **Exact Unresolved Question:** Does any production authorization path, database policy, trigger, or audit log consume `session_user` directly, or is authorization strictly anchored in `current_user` and verified signed context claims?
- **Recommended Option & Rationale:** **Eliminate session_user Dependencies; Enforce Signed Context & current_user**. Maintain `session_user` solely as the authenticated database connection identity (`college_app_user` for web, `college_worker_user` for tasks). All fine-grained authorization, multi-tenant isolation, and user attribution must consume verified signed context claims validated via database HMAC functions (`auth_private.is_request_context_valid()`).
- **Alternative Options:**
  - *Option 2 (PostgreSQL Role Per User):* Map every web user to a database role (Incompatible with connection pooling and Supabase architecture).
  - *Option 3 (Supabase Native Auth Only):* Abandon custom JWT and signed context, relying strictly on Supabase Auth tokens and `auth.uid()` (Requires complete frontend and backend authentication redesign).
- **Security & Operational Risks:** If test harnesses or application code confuse `session_user` (the connection login) with `current_user` (the effective role) or context GUCs, connection pool reuse can result in confused-deputy authorization bypass.
- **Who Must Approve:** Technical Specialist (Application Security Engineer & Database Architect).
- **Exact Human Approval Required:** Formal sign-off on the Identity Consumer Inventory covering every policy, function, and repository query.
- **Evidence Required to Resolve:** Complete inventory mapping each database table and policy to its exact identity source.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-07 — Direct-Login Testing Requirement

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Existing database test scripts (`scripts/test_user_rls.py`, `backend/tests/test_multi_tenant_isolation.py`) execute `SET ROLE` or connect via superuser/default pool URLs.
  - Step 4 proposed a harness login role using `SET ROLE college_app_user`.
- **Exact Unresolved Question:** Is direct-login testing required for runtime roles (where `session_user == 'college_app_user'`), or is a dedicated test harness login executing controlled `SET ROLE` sufficient?
- **Recommended Option & Rationale:** **Dedicated Harness Login with Controlled SET ROLE for Capability Tests; Disposable Direct Login Only if session_user is Consumed**.
  - Runtime roles (`college_app_user`, `college_worker_role`) must remain `NOLOGIN` in production.
  - For RLS and capability testing, an unprivileged harness login with `NOINHERIT` and a single `SET-only` membership validates effective privileges without enabling credentials on runtime roles.
  - If D-06 reveals any production path reading `session_user`, a disposable direct-login test must be executed in a dedicated sandbox.
- **Alternative Options:**
  - *Option 2 (Enable LOGIN on Runtime Roles in Test Stack):* Temporarily assign passwords to runtime roles for direct connection testing (Carries risk of accidental credential leakage to production templates).
  - *Option 3 (Direct Grants to Test Harness):* Copy grants to a distinct test role (Fails to test the actual target role's effective privileges).
- **Security & Operational Risks:** Using `SET ROLE` tests effective permissions (`current_user`), but does *not* validate connection string authentication or `session_user` assertions. Enabling `LOGIN` on production roles violates least privilege.
- **Who Must Approve:** Technical Specialist (Security Test Engineer).
- **Exact Human Approval Required:** Approval of the test harness principal specification and authorization criteria for direct-login tests.
- **Evidence Required to Resolve:** Verification that D-06 contains no `session_user` dependencies, or an approved test plan for disposable direct login.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-08 — PostgreSQL 17 Role-Membership Closure and Protected-Role Allowlist

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Migration 018 creates `college_app_user`.
  - Migration 020 revokes permissions from `anon` and `authenticated`.
  - Step 4 provided a cycle-safe recursive CTE query inspecting PostgreSQL 17 `set_option`, `inherit_option`, and `admin_option` flags in `pg_auth_members`.
- **Exact Unresolved Question:** What is the approved inventory of protected database roles and object owners, and what are the permissible transitive membership routes for application, migration, and test principals?
- **Recommended Option & Rationale:** **Strict Protected-Role Allowlist with Fail-Closed Transitive Inspection**.
  - Protected set: All roles with `rolsuper=true`, `rolbypassrls=true`, all schema owners, all relation/function owners, migration roles, and Supabase management roles (`supabase_admin`, `postgres`).
  - Permitted paths: `college_app_user` and `college_worker_role` must have zero direct or transitive routes to any protected role via `SET`, `INHERIT`, or `ADMIN OPTION`.
  - The cycle-safe recursive query must be executed as a mandatory Gate C assertion.
- **Alternative Options:**
  - *Option 2 (Direct Membership Check Only):* Inspect only direct entries in `pg_auth_members` (Unsafe: misses multi-hop privilege escalation).
- **Security & Operational Risks:** Transitive role inheritance or `ADMIN OPTION` grants can allow an unprivileged web application role to escalate to table owner or superuser, completely bypassing all RLS protections.
- **Who Must Approve:** Technical Specialist (PostgreSQL Database Administrator & Security Architect).
- **Exact Human Approval Required:** Sign-off on the complete protected role allowlist and recursive membership verification script.
- **Evidence Required to Resolve:** Approved baseline catalog query and documented role hierarchy definition.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-09 — Independent Unprivileged Negative-Test Login

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Existing test suites test isolation by attempting queries across different `college_id` GUCs using the same database connection pool.
  - There is no separate, genuinely unprivileged database role utilized to verify that negative ACL boundaries hold.
- **Exact Unresolved Question:** Will negative tests rely on Supabase's `anon` role or a distinct, disposable, unprivileged database principal with zero application memberships?
- **Recommended Option & Rationale:** **Dedicated Disposable Unprivileged Principal (`negative_test_user`)**. Create a dedicated test role with `LOGIN`, `NOINHERIT`, `rolsuper=false`, `rolbypassrls=false`, zero memberships in application/worker/owner roles, and no default table grants. This role exercises negative fixtures to prove that unauthorized principals are denied by both table ACLs and RLS policies.
- **Alternative Options:**
  - *Option 2 (Use Supabase anon):* Test using `anon` (Unsafe assumption: `anon` in Supabase may have ambient grants or postgrest-specific configurations not representative of arbitrary attackers).
  - *Option 3 (Application Role Negative Tests Only):* Only test authenticated tenants against other tenants (Leaves unauthenticated database connection boundaries untested).
- **Security & Operational Risks:** Without an independent negative principal, tests cannot distinguish between a successful RLS row-filter denial and a table-level `PERMISSION DENIED` ACL failure.
- **Who Must Approve:** Technical Specialist (Security Test Engineer).
- **Exact Human Approval Required:** Approval of the negative-test principal definition, fixture grant rationale, and test assertions.
- **Evidence Required to Resolve:** SQL specification for `negative_test_user` and test case list for unauthorized read, write, DDL, and definer execution.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-10 — Signing-Key Storage, Access, and Rotation

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/core/config.py` defines `RLS_CONTEXT_SECRET: SecretStr`.
  - `.env.example` contains placeholder `RLS_CONTEXT_SECRET=0123456789abcdef...` (64 hex characters / 32 bytes).
  - Migration 021 defines `auth_private.rls_context_keys` to store the active key in PostgreSQL.
  - Comments in migration 021 state: `-- INSERT INTO auth_private.rls_context_keys ... Do not commit the key`.
- **Exact Unresolved Question:** Where will the cryptographic context-signing key be stored, how will it be injected into the backend and database, and what is the exact dual-verification rotation procedure?
- **Recommended Option & Rationale:** **External Secret Store with Dual-Key Overlap Rotation**.
  - The 32-byte master key must reside in a dedicated secret manager (e.g., AWS Secrets Manager, Vault, or Supabase Vault), never in Git or migrations.
  - Provisioned separately into `auth_private.rls_context_keys` by an authorized DBA runbook.
  - Dual-key overlap: The database verifier must support an `active` key for signing and allow a 5-minute transition window for `previous` key verification to enable zero-downtime key rotation.
  - Never share context-signing keys with user JWT signing keys (`JWT_SECRET_KEY`).
- **Alternative Options:**
  - *Option 2 (Environment Variable Only):* Inject via `.env` and manual SQL insert (Operational friction; high risk of key desynchronization).
  - *Option 3 (Single Key Without Rotation Window):* Instantaneous key replacement (Causes in-flight web requests to fail signature checks).
- **Security & Operational Risks:** Compromise of `RLS_CONTEXT_SECRET` enables total forgery of tenant context (`app.current_college_id`) and super-admin flags, completely dismantling RLS. Hardcoding or logging keys in migrations creates permanent Git compromise.
- **Who Must Approve:** Both Project Owner and Technical Specialist (Application Security & Key Management Owner).
- **Exact Human Approval Required:** Sign-off on key custody runbook, rotation schedule, and KMS access policies.
- **Evidence Required to Resolve:** Approved Key Management Runbook specifying secret injection and overlap rotation procedures without revealing secret values.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-11 — Password-Reset Email Delivery Provider or Deferral

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/services/email_transport.py` implements an SMTP/SES mock and delivery handler.
  - `backend/app/api/v1/auth.py` contains password reset request endpoints.
  - Step 3.1 and Step 4 document that the password reset endpoint currently discards or logs reset tokens because a live production email delivery provider is not configured.
- **Exact Unresolved Question:** Will a production transactional email provider (SendGrid, AWS SES, Resend, Postmark) be integrated, or will the password reset capability be formally deferred/disabled in the initial production release?
- **Recommended Option & Rationale:** **Explicit Deferral / Disable in Production Until Secure Provider is Provisioned**. If no live transactional email provider is approved and contracted, the password-reset API endpoint must return a safe, generic message (`{"message": "If this email is registered, password reset instructions have been sent"}`) while internally disabling token generation, preventing unhandled token leakage in server logs or response payloads.
- **Alternative Options:**
  - *Option 2 (Contract and Configure Email Provider):* Approve and configure an official transactional email provider with TLS, SPF, DKIM, and DMARC verification.
  - *Option 3 (Admin-Assisted Reset Only):* Password resets can only be performed by College Admins or Super Admins via an authenticated admin workflow.
- **Security & Operational Risks:** Emitting reset tokens in API responses or server logs allows trivial account takeover. Discarding tokens silently frustrates legitimate users without recovering accounts.
- **Who Must Approve:** Project Owner (Product/Business Decision) and Technical Specialist (Privacy & Communications Security).
- **Exact Human Approval Required:** Written decision to either (a) contract a specific transactional provider, (b) adopt admin-only reset, or (c) formally disable password reset.
- **Evidence Required to Resolve:** Provider configuration agreement OR approved pull-request specification disabling the self-service reset route.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-12 — Notification Email Retention and Data Minimization

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/models/notification.py` defines `InAppNotification`.
  - Notification logging records recipient email addresses and delivery payloads.
  - No automated data retention or pruning job exists in `scripts/` or `backend/app/tasks/`.
- **Exact Unresolved Question:** What is the maximum retention period for notification logs containing recipient email addresses, and how will message bodies and personal data be minimized or scrubbed?
- **Recommended Option & Rationale:** **30-Day Bounded Retention with Token/Body Scrubbing**. Notification logs must store recipient addresses for a maximum of 30 days solely for delivery troubleshooting. Invitation tokens, password reset links, email bodies, and raw provider errors must be scrubbed before database persistence. A Celery periodic task must purge records older than 30 days.
- **Alternative Options:**
  - *Option 2 (Pseudonymized Logging):* Store only HMAC-SHA256 digests of email addresses (Prevents reverse lookup; complicates user support inquiry tracking).
  - *Option 3 (Indefinite Retention):* Retain all logs permanently (Violates GDPR/FERPA data minimization principles).
- **Security & Operational Risks:** Storing unencrypted email bodies and recipient addresses indefinitely exposes student and applicant personal data in database backups and audit dumps.
- **Who Must Approve:** Technical Specialist (Data Privacy & Compliance Officer) and Project Owner.
- **Exact Human Approval Required:** Written sign-off on the notification data retention policy and scrubbing rules.
- **Evidence Required to Resolve:** Approved data retention policy document and scheduled purge task design.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-13 — Public College Registration versus Super Admin-Only Registration

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `apps/admin-frontend/src/app/(auth)/register-college/page.tsx` provides a public registration portal.
  - `backend/app/api/v1/college_registrations.py` handles public submission.
  - Migration 021 defines `submit_public_college_registration(jsonb)`.
  - Table `college_registrations` holds registrations with status `PENDING`, `APPROVED`, `REJECTED`, `UNDER_REVIEW`.
- **Exact Unresolved Question:** Can public visitors directly create or onboard new college tenants, or is onboarding strictly restricted to Super Admin approval of pending submissions?
- **Recommended Option & Rationale:** **Public Submission Creates Pending Registration Only; Super Admin Controls Tenant Provisioning**. Public applicants can only insert into `college_registrations` with status `PENDING`. Creation of the actual root tenant record in `colleges`, provisioning of admin accounts in `users`, and membership linking in `college_memberships` must be strictly restricted to authenticated Super Admins executing reviewed approval functions.
- **Alternative Options:**
  - *Option 2 (Super Admin Only / Closed Onboarding):* Remove the public registration form completely; Super Admins manually register colleges after offline agreements.
  - *Option 3 (Automated Self-Service Provisioning):* Automatically activate colleges upon domain verification (Extremely high risk: allows spam/phishing tenants).
- **Security & Operational Risks:** Allowing unvetted public registration to directly instantiate active colleges in `colleges` exposes the platform to subdomain takeover, phishing, and vector database resource exhaustion.
- **Who Must Approve:** Project Owner (Product/Business Model) and Technical Specialist (Application Security).
- **Exact Human Approval Required:** Formal sign-off on the registration state machine and confirmation that public users cannot directly provision active tenants.
- **Evidence Required to Resolve:** Documented registration lifecycle specification and negative test cases verifying public users cannot insert into `public.colleges`.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-14 — EDITOR and VIEWER Permission Matrix

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Enum `user_role` in `003_create_users_and_memberships.sql` defines: `SUPER_ADMIN`, `COLLEGE_ADMIN`, `STAFF`, `STUDENT`.
  - Membership role enum in `003` defines: `ADMIN`, `MEMBER`.
  - Application references mention `EDITOR` and `VIEWER` roles for college admin dashboards.
- **Exact Unresolved Question:** What are the exact database-level and API-level permission boundaries for `EDITOR` and `VIEWER` roles within a college tenant?
- **Recommended Option & Rationale:** **Fail-Closed: VIEWER is Strict Read-Only; EDITOR is Limited to Drafts/Reviews; Admins Hold Publish/Delete Rights**.
  - `VIEWER`: Can read verified knowledge chunks, view analytics dashboards, and read crawled pages. Zero write permissions.
  - `EDITOR`: Can trigger crawl jobs, upload documents, and edit draft FAQs. Cannot delete documents, cannot approve production knowledge base chunks, and cannot manage college settings or memberships.
  - `COLLEGE_ADMIN`: Full administrative control over tenant settings, staff invitations, and knowledge publishing.
- **Alternative Options:**
  - *Option 2 (Defer Granular Roles):* Consolidate permissions under `COLLEGE_ADMIN` only, treating all tenant staff identically until product requirements mature.
  - *Option 3 (Permissive Co-Admin):* Grant `EDITOR` full knowledge base publishing rights.
- **Security & Operational Risks:** Undefined or weakly enforced intermediate roles lead to horizontal privilege escalation, where view-only staff or compromised credentials modify crawler targets or poison the RAG vector index.
- **Who Must Approve:** Project Owner (Product Feature Requirements) and Technical Specialist (Application Security Architect).
- **Exact Human Approval Required:** Approved Role-Based Access Control (RBAC) matrix signed by Product and Security leads.
- **Evidence Required to Resolve:** Formal RBAC Matrix table mapping every API route and database table to allowed role actions.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-15 — Audit Payload and AI Telemetry Allowlists and Redaction

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `database/migrations/008_create_ai_and_audit_tables.sql` creates `audit_logs` and `ai_provider_events`.
  - `audit_logs` contains `payload_before JSONB` and `payload_after JSONB`.
  - `ai_provider_events` records `error_message text`, `prompt_tokens`, `completion_tokens`, and `latency_ms`.
  - `backend/app/services/ai_provider_service.py` logs events via `_log_telemetry`.
- **Exact Unresolved Question:** What strict key allowlists, data redaction filters, and retention limits govern audit logs and AI telemetry to prevent leaking student PII, credentials, or proprietary prompts?
- **Recommended Option & Rationale:** **Strict Key Allowlist & Automatic Secret/PII Redactor**.
  - Audit payloads must pass through an explicit schema filter allowing only non-sensitive field changes (e.g., status changes, timestamps, names). Passwords, tokens, secret keys, and personal contact details must be stripped before logging.
  - AI telemetry must record only aggregate numerical metrics (`latency_ms`, `prompt_tokens`, `completion_tokens`, `model`, `provider`) and categorized error codes (`TIMEOUT`, `RATE_LIMIT`, `FAILOVER`). Raw student chat prompts, full model responses, and raw HTTP exception bodies must be strictly prohibited from telemetry tables.
- **Alternative Options:**
  - *Option 2 (Raw JSON Logging with Regex Masking):* Log complete payloads through regex filters (Fragile: easily bypassed by nested or malformed structures).
  - *Option 3 (Minimal Counter Telemetry):* Do not record database telemetry rows; rely entirely on external Prometheus/Datadog metrics.
- **Security & Operational Risks:** Storing unredacted audit diffs or AI telemetry logs frequently causes accidental credential leaks, PII exposure under FERPA/GDPR, and vector database poisoning visibility.
- **Who Must Approve:** Technical Specialist (Security/Privacy Officer & AI Operations Lead).
- **Exact Human Approval Required:** Sign-off on the telemetry schema allowlist and sanitization filter specification.
- **Evidence Required to Resolve:** Approved schema allowlist specification and unit test cases proving sensitive fields are redacted before persistence.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-16 — Creation of a New Disposable Supabase-Compatible Test Environment

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Step 2 test ran on a vanilla PostgreSQL Docker container where migrations failed on `auth.uid()` because Supabase schemas were absent.
  - Step 4 explicitly notes that the previous container/volume must *not* be reused.
  - No active Supabase CLI local stack (`supabase start`) is currently running in the repository.
- **Exact Unresolved Question:** What exact local container architecture will be approved to provide a pure Supabase-compatible validation environment (including `auth`, `storage`, `realtime`, and native roles) without connecting to hosted production?
- **Recommended Option & Rationale:** **Disposable Local Supabase Stack via Official Supabase CLI / Isolated Docker Network**.
  - Spin up a fresh, disposable local Supabase stack utilizing the official Supabase CLI on a dedicated loopback interface (`127.0.0.1`) with isolated volumes.
  - Must include the genuine Supabase Auth service, `pgvector`, and standard roles (`postgres`, `anon`, `authenticated`, `service_role`).
  - Completely separate from hosted production; zero production credentials, connection strings, or real institutional data permitted.
  - The old vanilla PostgreSQL container and volume must remain completely untouched and unreferenced.
- **Alternative Options:**
  - *Option 2 (Staging Supabase Cloud Project):* Provision a separate disposable cloud project on Supabase Free/Pro tier (Introduces internet/cloud dependency; requires network egress approval).
  - *Option 3 (Custom Dockerfile with Shims):* Manually load Supabase schemas into vanilla PostgreSQL (Fragile and inaccurate: does not truly validate Supabase behavior).
- **Security & Operational Risks:** Testing against vanilla PostgreSQL gives false confidence because Supabase RLS functions (`auth.uid()`) fail to execute. Testing against cloud projects risks accidental production connection if credentials are misconfigured.
- **Who Must Approve:** Technical Specialist (DevOps / Infrastructure Engineer & Database Architect).
- **Exact Human Approval Required:** Written approval of the local Supabase container manifest, network isolation configuration, and teardown runbook.
- **Evidence Required to Resolve:** Documented local container compose manifest and verification that the environment exposes loopback ports with zero cloud linkage.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-17 — Implementation Authorization and Separate Production Approval

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - All preceding steps (Steps 2, 3, 3.1, 4, 5) explicitly state that planning documents do not constitute implementation authorization.
  - The repository remains in a pre-implementation state.
- **Exact Unresolved Question:** Who holds the formal authority to authorize Phase 3A.4.4B code/migration implementation (Gate B), and who holds separate release authority for production deployment (Gate C)?
- **Recommended Option & Rationale:** **Strict Three-Gate Staged Authorization Boundary**.
  - **Gate A:** Design and architectural approval (Resolution of D-01 through D-22).
  - **Gate B:** Authorization to implement code changes and run migrations in the *disposable local test environment only*. Requires named Project Owner and Technical Specialist sign-off.
  - **Gate C:** Production deployment authorization. Requires independent verification of Gate B test results, clean security audit reports, and a formal rollback plan. Gate B approval *never* implies Gate C approval.
- **Alternative Options:**
  - *Option 2 (Combined Implementation & Release Approval):* Authorize implementation and deployment in a single decision (Extremely dangerous: violates standard engineering controls).
- **Security & Operational Risks:** Conflating design review with implementation authorization leads to unreviewed code edits and accidental database changes before architectural consensus is reached.
- **Who Must Approve:** Project Owner (Business Authorization) and Lead System Architect.
- **Exact Human Approval Required:** Formal written designation of accountable authorizers and sign-off on the staged gate process.
- **Evidence Required to Resolve:** Written corporate delegation of authority document naming the accountable project owner and technical lead.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-18 — Application Identity Model and Supabase auth.uid() Boundary

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - Migration 017 defined RLS policies using `auth.uid() = id`.
  - Backend `app/database/session.py` implements a custom JWT and HMAC-signed context model (`app.current_user_id`, `app.current_college_id`).
  - Migration 021 replaces `auth.uid()` policies with `public.current_app_user_id()`.
- **Exact Unresolved Question:** Does the platform rely on Supabase Native Auth (`auth.uid()`) as its primary identity anchor, or does it utilize custom application JWTs and database-verified signed context?
- **Recommended Option & Rationale:** **Custom Signed Application Context; Formal Deprecation of auth.uid()**.
  - The backend uses FastAPI with custom JWT authentication and multi-tenant claims.
  - PostgREST is not exposed directly to untrusted web clients; all traffic flows through FastAPI.
  - Database RLS must evaluate identity via verified context functions (`public.current_app_user_id()`, `public.current_app_tenant()`) backed by HMAC signature verification.
  - Migration policies referencing `auth.uid()` must be completely removed or replaced, as Supabase Auth is not the caller.
- **Alternative Options:**
  - *Option 2 (Migrate Entire Backend to Supabase Auth):* Rewrite FastAPI authentication to issue Supabase Auth tokens and pass them to PostgREST (Massive refactor: invalidates current frontend/backend architecture).
  - *Option 3 (Hybrid / Dual Identity):* Support both `auth.uid()` and signed context (High complexity: creates dual-path policy vulnerabilities).
- **Security & Operational Risks:** Mixing `auth.uid()` and custom signed context leads to policy bypass where `auth.uid()` evaluates to `NULL` for custom JWT callers, causing queries to fail or default-allow branches to trigger.
- **Who Must Approve:** Technical Specialist (Application Security Architect).
- **Exact Human Approval Required:** Architectural decision record (ADR) approving the custom signed context model and deprecating `auth.uid()`.
- **Evidence Required to Resolve:** Approved Architecture Decision Record on Application Identity and policy migration plan.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-19 — Visitor-Token Lifetime and Anonymous Feedback

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/api/v1/chat.py` generates visitor tokens for anonymous prospective students.
  - Migration 021 introduces `app.chat_visitor_token` and visitor hash tracking in `chat_sessions`.
  - Step 3.1 recommends a 24-hour absolute non-sliding expiration.
- **Exact Unresolved Question:** What is the maximum valid lifetime of an anonymous visitor token, and can anonymous users submit feedback on chat answers without presenting the matching session token?
- **Recommended Option & Rationale:** **Strict 24-Hour Absolute Expiry; Matching-Token Required for Feedback**.
  - Anonymous visitor tokens must be cryptographically random 32-byte bearer tokens.
  - The database stores only the SHA-256 digest of the token.
  - Absolute non-sliding lifetime: **24 hours maximum** from session creation.
  - Feedback submission on a chat session *must* present the matching visitor token; unauthenticated third parties cannot submit feedback to arbitrary session IDs.
- **Alternative Options:**
  - *Option 2 (Sliding Expiry):* Extend token lifetime by 2 hours on each request up to 7 days (Increases token replay vulnerability).
  - *Option 3 (Open Feedback Submission):* Allow any client to rate any message ID without a visitor token (Allows feedback spam and rating manipulation).
- **Security & Operational Risks:** Long-lived or non-expiring visitor tokens allow session hijacking of prospective student chats. Permissive feedback endpoints allow malicious rating manipulation of college knowledge answers.
- **Who Must Approve:** Project Owner (Student User Experience) and Technical Specialist (Application Security).
- **Exact Human Approval Required:** Sign-off on the 24-hour non-sliding expiry policy and matching-token feedback validation requirement.
- **Evidence Required to Resolve:** Approved API specification for anonymous chat and feedback endpoints.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-20 — Guest Support-Ticket Permissions

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `apps/user-frontend` allows prospective students to submit an inquiry when the chatbot cannot answer.
  - `backend/app/services/support_service.py` implements `create_ticket`.
  - `backend/app/models/feedback_support.py` defines `SupportTicket` with optional `user_id` and mandatory `college_id`.
- **Exact Unresolved Question:** Can unauthenticated guest ticket submitters view ticket status, read replies, or add follow-up comments, or is guest support strictly create-only?
- **Recommended Option & Rationale:** **Guest Support is Strictly Create-Only (Write-Once)**.
  - Guest ticket creation requires student name, valid email, category, priority, and message.
  - Upon creation, the ticket is stored, and staff reply via email.
  - Guests receive *zero* database read, update, or reply permissions. Unauthenticated users cannot list tickets or read internal staff notes.
  - Any interactive ticket conversation requires the user to authenticate.
- **Alternative Options:**
  - *Option 2 (Capability URL / Bearer Ticket Link):* Email a signed capability token allowing the guest to view that specific ticket in the browser (Requires token generation, expiry, and access logging).
  - *Option 3 (Open Ticket Lookup by Email):* Allow lookup of tickets by email address (Severe PII leak: allows scraping of student inquiries).
- **Security & Operational Risks:** Giving anonymous users read access to tickets risks leaking internal staff notes, counselor commentary, and student contact information.
- **Who Must Approve:** Project Owner (Support Workflow) and Technical Specialist (Security Architect).
- **Exact Human Approval Required:** Formal confirmation that guest ticket submission remains create-only in this phase.
- **Evidence Required to Resolve:** Product workflow specification confirming email-based follow-up for guest tickets.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-21 — College Chat Analytics and Raw Conversation Access

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `apps/admin-frontend/src/app/college-admin/analytics/page.tsx` displays analytics dashboards.
  - `backend/app/services/analytics_service.py` provides metrics (`daily_query_trend`, `popular_questions`).
  - `backend/app/repositories/college_admin_repository.py` queries `chat_messages` for analytics.
- **Exact Unresolved Question:** Do College Administrators have access to raw student chat logs and conversation transcripts, or are they strictly limited to anonymized, aggregated analytics metrics?
- **Recommended Option & Rationale:** **Strictly Aggregate-Only for College Admins; Raw Transcripts Restricted to Authorized Support Workflows**.
  - College Admins receive aggregated metrics (total query volume, category breakdowns, daily trends, sentiment percentages, unanswered question frequency).
  - Raw prompts and answers must not be browsable by general college staff unless the student explicitly escalated the conversation into a support ticket.
  - Aggregation queries must be implemented via `SECURITY DEFINER` functions enforcing strict `college_id` tenant filtering.
- **Alternative Options:**
  - *Option 2 (Full Transcript Access):* College Admins can read all anonymous student chat histories (High privacy risk; potential student deanonymization).
  - *Option 3 (Sanitized Sample Transcripts):* Provide a random sample of transcripts with PII redacted (Requires complex PII detection and redaction).
- **Security & Operational Risks:** Exposing raw chat logs allows staff to view sensitive personal admissions questions, financial inquiries, and student medical/disability accommodation discussions.
- **Who Must Approve:** Project Owner (Institutional Policy) and Technical Specialist (Data Privacy Officer).
- **Exact Human Approval Required:** Policy approval confirming that college admin dashboards display aggregate metrics only.
- **Evidence Required to Resolve:** Approved Analytics Data Governance specification.
- **Current Status:** **PENDING HUMAN DECISION**.

---

### D-22 — Sensitive User-Column Access and Authentication Lookup Contract

- **Current Step 5 Status:** PENDING.
- **Relevant Repository Evidence:**
  - `backend/app/models/user.py` maps `User` with columns `hashed_password`, `email`, `role`, `is_verified`, `is_active`, `preferences`.
  - Migration 021 initially defined `lookup_user_by_email_for_auth`.
  - Migration 022 explicitly replaced `lookup_user_by_email_for_auth` to return a strictly limited 7-field projection: `id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, `is_active`.
  - Migration 022 revokes all other direct table permissions on sensitive columns from `college_app_user`.
- **Exact Unresolved Question:** What is the approved, minimal column projection returned by the authentication lookup function, and are direct `SELECT` queries on `users.hashed_password` prohibited for runtime application roles?
- **Recommended Option & Rationale:** **Enforce Migration 022 Minimal 7-Field Projection; Prohibit Direct Table Reads on Password Hashes**.
  - `college_app_user` must have zero direct `SELECT` privileges on `users.hashed_password`.
  - Authentication verification must exclusively execute `public.lookup_user_by_email_for_auth(p_email)` which returns exactly the 7 required fields.
  - General user queries (`get_user_by_id`, `list_users`) must use explicit SQLAlchemy projections excluding `hashed_password`.
- **Alternative Options:**
  - *Option 2 (Direct Table Select with ORM Column Deferral):* Grant table SELECT but use SQLAlchemy `defer("hashed_password")` (Fragile: developer oversight can accidentally fetch hashes).
  - *Option 3 (Separate Credentials Table):* Move `hashed_password` to `auth_private.user_credentials` (Clean, but requires forward-only schema migration under Branch B).
- **Security & Operational Risks:** Permitting application roles to execute unrestricted `SELECT * FROM users` risks exposing Bcrypt password hashes in memory dumps, error tracebacks, or API JSON serialization bugs.
- **Who Must Approve:** Technical Specialist (Application Security Engineer & Database Security Architect).
- **Exact Human Approval Required:** Sign-off on the 7-field authentication lookup contract and column grant restrictions.
- **Evidence Required to Resolve:** Inspection report verifying that all backend authentication call sites use `lookup_user_by_email_for_auth` and ORM models exclude password hashes from standard queries.
- **Current Status:** **PENDING HUMAN DECISION**.

---

## 5. Required Project-Owner Decisions (Plain-Language Guide)

The following six decisions directly impact product functionality, operational budget, and business risk. They must be decided by the **Project Owner**:

```
+--------+------------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
| ID     | Decision Title (Plain Language)          | Option A (Recommended)                                | Option B (Alternative)                                |
+--------+------------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
| D-01   | Database Migration Strategy              | Branch B: Safe forward repair (zero data loss risk).   | Branch A: Rewrite existing files (only if never run). |
| D-02   | Background Worker Isolation              | Tenant-Isolated: Clean separation between colleges.   | Shared Pool: Cheaper, but higher cross-tenant risk.   |
| D-11   | Student Password Reset Handling          | Formally defer self-service reset until provider on.  | Contract transactional email provider immediately.    |
| D-13   | New College Onboarding Policy            | Public forms submit pending requests for Super Admin. | Automated public registration with instant live apps. |
| D-14   | Staff Dashboard Roles (Editor vs Viewer) | Viewers are read-only; Editors cannot publish live.   | Granular staff roles deferred; admin-only control.    |
| D-21   | Chat History Privacy for College Admins  | Admins see summary charts only; no raw student logs.  | Admins can browse all student chat transcripts.       |
+--------+------------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
```

### Consequences for Project Owner Consideration
1. **D-01 (Migrations):** Choosing Branch A when migrations have already run in any cloud instance will corrupt deployment pipelines. Defaulting to Branch B is the universally accepted DevOps safe practice.
2. **D-02 (Workers):** Isolated workers require slightly higher container memory and queue configuration, but completely eliminate cross-college data leaks during document OCR.
3. **D-11 (Password Reset):** If transactional email is not yet purchased, self-service password reset must be disabled to prevent security vulnerabilities.
4. **D-13 (Onboarding):** Allowing instant self-service college creation invites spammers to create fraudulent academic portals. Super Admin review is essential.
5. **D-14 (Roles):** Clearly separating Editors from Viewers prevents unauthorized document deletion or unvetted FAQ publication.
6. **D-21 (Chat Privacy):** Protecting raw student chat logs ensures institutional compliance with educational privacy expectations.

---

## 6. Required Specialist Approvals (Role Matrix)

Technical sign-offs must be obtained from individuals holding the specific technical specialties below. Names must be filled in upon formal review:

| Decision ID | Required Specialist Domain | Specific Expertise Evaluated | Specialist Sign-off Status |
|:---|:---|:---|:---:|
| **D-01** | Database Release Engineer | PostgreSQL migration engines, schema versioning, Supabase CLI | PENDING |
| **D-03** | Database Security Architect | PostgreSQL capability roles, claim functions, connection pooling | PENDING |
| **D-04** | Distributed Systems Engineer | Queue leasing, Redis heartbeats, dead-letter recovery, Celery | PENDING |
| **D-05** | PostgreSQL Security Architect | `SECURITY DEFINER`, search paths, function ownership, ACLs | PENDING |
| **D-06** | Application Security Engineer | PostgreSQL GUCs, session vs current user, HMAC verification | PENDING |
| **D-07** | Security Test Engineer | Connection harness design, runtime role credential boundaries | PENDING |
| **D-08** | PostgreSQL Database Administrator | PostgreSQL 17 role catalog recursion, privilege inheritance | PENDING |
| **D-09** | QA / Security Test Engineer | Negative fixture design, ACL vs RLS denial differentiation | PENDING |
| **D-10** | Key Management Specialist | KMS architecture, cryptographic secret rotation, HMAC-SHA256 | PENDING |
| **D-12** | Data Privacy & Compliance Officer | FERPA/GDPR data minimization, notification log retention | PENDING |
| **D-15** | Application & AI Security Engineer | Telemetry schema design, PII sanitization, prompt protection | PENDING |
| **D-16** | DevOps / Platform Engineer | Local Docker networking, loopback isolation, Supabase CLI stack | PENDING |
| **D-18** | Identity & Auth Architect | JWT token design, custom context vs Supabase Auth boundaries | PENDING |
| **D-22** | Application Security Engineer | ORM projection safety, database column-level privilege masks | PENDING |

---

## 7. Missing Documentary Evidence

The following documentary records are currently missing from the workspace and must be provided before decisions can be marked resolved:

1. **Authoritative Migration Ledger (for D-01):** Environment-by-environment record showing migration execution timestamps across all development, test, and hosted Supabase instances.
2. **Key Management Runbook (for D-10):** Operational protocol defining how `RLS_CONTEXT_SECRET` will be generated, injected, and rotated without developer exposure.
3. **Worker Deployment Architecture Diagram (for D-02, D-03, D-04):** Formal specification of Celery queue routing, process isolation, and database connection credentials.
4. **Data Retention & Privacy Schedule (for D-12, D-15, D-21):** Formal policy defining data lifecycle, retention cutoffs, and purging mechanisms for notification logs, telemetry, and chat sessions.
5. **Local Supabase Environment Specification (for D-16):** Docker Compose configuration file and startup script for the disposable local Supabase stack.
6. **Delegation of Authority Document (for D-17):** Formal written designation identifying the project owner and technical leads authorized to approve Gates A, B, and C.

---

## 8. Gate A Approval Checklist

To achieve **Gate A (Design Approval)**, every item below must be satisfied and documented:

- [ ] **Decision Consensus:** All 22 decisions (D-01 through D-22) have an approved option selected.
- [ ] **Accountable Owners Named:** Project Owner and technical specialist names are recorded alongside each decision.
- [ ] **Migration Strategy Certified:** Written attestation provided for Branch A, OR forward-only schema repair adopted under Branch B.
- [ ] **Identity & Role Architecture Approved:** Custom signed context model and PostgreSQL role hierarchy formally approved.
- [ ] **Worker Trust Model Signed Off:** Worker isolation boundary, claim functions, and lease parameters agreed upon.
- [ ] **Privacy & Retention Boundaries Established:** Clear limits set for notifications, telemetry, and visitor sessions.
- [ ] **Missing Evidence Resolved:** All six documentary evidence packages listed in Section 7 received and archived.

**Current Gate A Assessment:** **NOT COMPLETE** (Awaiting human owner and specialist determinations).

---

## 9. Gate B and Gate C Restrictions

### Gate B Restrictions (Implementation Authorization)
- **Status:** **NOT AUTHORIZED**.
- Gate A approval does *not* automatically grant Gate B authorization.
- Zero application code, migrations, or database roles may be edited until Gate B is explicitly signed.
- Gate B authorization must specifically define:
  1. Exact list of repository files authorized for modification.
  2. Approved local disposable test environment (hosted cloud instances strictly forbidden).
  3. Prohibited actions (e.g., zero production connections, zero commit of secrets).
  4. Explicit rollback and git branch recovery plan.

### Gate C Restrictions (Database Validation & Production Release)
- **Status:** **NOT VALIDATED — PRODUCTION NOT APPROVED**.
- Gate B implementation does *not* validate the database or authorize production release.
- Gate C requires:
  1. Execution of the complete security test matrix on the disposable Supabase-compatible stack.
  2. Recursive role-membership catalog verification passing with zero unreviewed routes.
  3. Negative test suite confirming independent unprivileged principal is blocked.
  4. Formal sign-off on backup/recovery and production rollback procedures.
  5. Dedicated, separate production release approval.

---

## 10. Exact Next Steps for Step 7

Upon completion of this Step 6 package, the technical team and project leadership must proceed through the following sequential actions:

1. **Convene Human Decision Review:**
   - Present this Step 6 report to the Project Owner and relevant Technical Specialists.
   - Walk through the plain-language owner decisions (D-01, D-02, D-11, D-13, D-14, D-21).
   - Review specialist technical decisions (D-03 through D-10, D-12, D-15 through D-20, D-22).
2. **Collect Missing Documentary Evidence:**
   - Obtain migration execution records from all team members to resolve D-01.
   - Draft and review the Key Management and Data Retention runbooks.
3. **Execute Gate A Sign-Off:**
   - Record formal selections and approvals in the decision register.
   - Mark Gate A as **COMPLETE** once all approvals and evidence are archived.
4. **Prepare Gate B Implementation Request (Step 7):**
   - Formulate the precise file-by-file implementation plan for the approved options.
   - Prepare the Docker configuration for the disposable local Supabase test environment.
   - Submit formal Gate B authorization request to the Project Owner.

---

## 11. Final Status Affirmation

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — GATE A NOT COMPLETE — IMPLEMENTATION NOT AUTHORIZED — DATABASE NOT VALIDATED
================================================================================
```
*No application source code, SQL migrations, database catalogs, or cloud resources were modified or executed during the creation of this document.*
