# Phase 3A.4.4B — Step 6.3: Final Technical Consistency and Gate A Readiness Review

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Technical Project Reviewer  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Documents:**
- [Step 6 Human Decision Resolution Package](./phase3a4.4b-step6-human-decision-resolution.md)
- [Step 6.1 Technical Consistency & Auth Diagnostic](./phase3a4.4b-step6.1-technical-consistency-and-auth-diagnostic.md)
- [Step 6.2 Technical Findings Correction and Consolidation](./phase3a4.4b-step6.2-technical-findings-correction.md)
**Deliverable Document:** `.agents/tasks/phase3a4.4b-step6.3-final-technical-consistency-review.md`

---

## 1. Executive Status and Strict Gate Separation

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — FINAL TECHNICAL REVIEW COMPLETE — NO IMPLEMENTATION AUTHORIZED
================================================================================
```

This report represents the strictly read-only, definitive technical consistency review and Gate A readiness assessment for Phase 3A.4.4B. It reconciles, refines, and formally standardizes the architectural findings, database security specifications, and decision registers developed across Steps 6.0, 6.1, and 6.2.

### 1.1 Strict Gate Separation Architecture

To prevent premature modification, schema divergence, or accidental production compromise, the project strictly maintains four isolated and sequential stages:

```
+--------------------------------------------------------------------------------------------------+
| GATE A: HUMAN DESIGN AND SPECIALIST APPROVAL                                                     |
| Status: NOT COMPLETE                                                                             |
| Purpose: Formal review and explicit written sign-off by Project Owner and Technical Specialists   |
|          on all 22 architectural and security decisions (D-01 through D-22).                      |
| Constraint: Technical specification correction DOES NOT constitute approval. Zero changes.       |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| GATE B: EXPLICIT IMPLEMENTATION AUTHORIZATION                                                    |
| Status: NOT AUTHORIZED                                                                           |
| Purpose: Formal authorization to begin implementing code modifications, migrations, or tests.    |
| Constraint: Strictly prohibited until Gate A achieves 100% written sign-off.                     |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| GATE C: ISOLATED DATABASE AND SECURITY VALIDATION                                                |
| Status: NOT VALIDATED                                                                            |
| Purpose: Execution of migrations and test suites strictly within an isolated, disposable local   |
|          Supabase-compatible test container bound to loopback with fail-closed URL guards.        |
| Constraint: Zero connection to hosted cloud Supabase or production databases.                     |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| PRODUCTION APPROVAL: SEPARATE AUTHORIZATION AFTER SUCCESSFUL VALIDATION                          |
| Status: NOT APPROVED                                                                             |
| Purpose: Independent deployment sign-off following successful Gate C audit and rollback plans.    |
| Constraint: Gate B or Gate C validation never constitutes production release approval.           |
+--------------------------------------------------------------------------------------------------+
```

### 1.2 Mandatory Operational Restrictions Upheld

In accordance with Phase 3A.4.4B instructions:
1. **Read-Only Inspection Only:** Static source code, migration files, and existing logs were inspected without executing queries or runtime commands.
2. **Zero Code Changes:** No application files, test scripts, or configuration files were modified.
3. **Zero SQL or Migrations Executed:** No DDL, DML, or schema migration steps were applied.
4. **Zero Database Connections:** No socket or TCP connections were established to local or remote database instances.
5. **Zero Hosted Supabase Access:** Remote cloud endpoints (`*.supabase.co`) were not accessed.
6. **Zero Environment or Docker Alterations:** `.env` files, Docker containers, images, and volumes remained completely untouched.
7. **Zero Credential Disclosure:** All secrets, keys, and token hashes remain masked.
8. **No Implementation Authorization:** This document does not authorize any implementation.
9. **No Automatic Approval:** Correcting technical specifications for D-01 through D-22 does not mark any decision approved.

---

## 2. In-Depth Technical Corrections of Step 6.2 Findings

### 2.1 D-06 / D-18: Separation of Session Identity, Effective Role Identity, and Signed Context

A critical technical inconsistency identified in early planning documents was the conflation of PostgreSQL session identity, effective role identity, and application-level signed request context. These three identity concepts operate at distinct layers of the PostgreSQL engine and application stack:

```
+--------------------------------------------------------------------------------------------------------------------+
| IDENTITY LAYER COMPARISON MATRIX                                                                                   |
+-------------------------+---------------------------------+----------------------------------+---------------------+
| Layer                   | Mechanism / Primitive           | Set By / Managed By              | Where Consumed      |
+-------------------------+---------------------------------+----------------------------------+---------------------+
| PostgreSQL Session      | session_user                    | Authenticated TCP connection     | Connection pooling, |
| Identity                |                                 | string (e.g., college_app_user)  | connection audit log|
+-------------------------+---------------------------------+----------------------------------+---------------------+
| Effective Role Identity | current_user / current_role     | SET ROLE statement or            | SQL object ACLs,    |
|                         |                                 | SECURITY DEFINER function owner  | table privileges    |
+-------------------------+---------------------------------+----------------------------------+---------------------+
| Signed Application      | app.request_context GUCs        | FastAPI set_rls_context() via    | Multi-tenant RLS,   |
| Context                 | verified by HMAC in PL/pgSQL    | transaction-local set_config()   | row-level filters   |
+-------------------------+---------------------------------+----------------------------------+---------------------+
```

#### Detailed Layer Separation Analysis
1. **PostgreSQL Session Identity (`session_user`):**
   - Represents the physical role used to authenticate the database connection when the TCP socket is opened.
   - Remains constant for the entire duration of the connection unless altered via `SET SESSION AUTHORIZATION` (which requires superuser privileges).
   - In production, connection pools (e.g., `DATABASE_APP_ROLE_URL`) authenticate as `college_app_user`.
   - **Critical Rule:** No RLS policy, table-level grant, or application query should ever reference or depend on `session_user` for tenant isolation or user authorization. Conflating `session_user` with the end-user breaks connection pooling.

2. **Effective Role Identity (`current_user` / `current_role`):**
   - Represents the active privilege context under which PostgreSQL evaluates table permissions, view permissions, and schema access.
   - Defaults to `session_user` upon connection, but changes dynamically when executing `SET ROLE <role>` or when execution enters a `SECURITY DEFINER` function (where it temporarily adopts the function owner's role).
   - **Critical Rule:** `current_user` governs table-level ACL access (e.g., can `college_app_user` execute `SELECT` on `public.users`?). It does **not** determine multi-tenant data slicing; multi-tenant isolation is enforced at the row level via RLS policies.

3. **Signed Application Context (`app.request_context` / `public.current_app_*`):**
   - Represents the verified identity of the end-user and tenant, constructed by FastAPI and transported over PostgreSQL transaction-local GUCs (`is_local = true`).
   - Bound by an HMAC-SHA256 signature calculated over `v1|user_id|college_id|is_super|email_verified|expires_at` (or `v2` extended payload) and verified by `auth_private.is_request_context_valid()`.
   - RLS policies in migration `021` strictly evaluate `public.current_app_user_id()` and `public.current_app_tenant()`.
   - **Critical Rule:** The application context operates completely independently of PostgreSQL role membership. It completely replaces Supabase native `auth.uid()` in the FastAPI architecture. Conflating application context with `auth.uid()` or PostgreSQL roles creates critical policy bypasses.

---

### 2.2 D-07: Distinguishing SET ROLE Testing from Direct-Login Testing

Step 6.2 correctly identified that testing with `SET ROLE` behaves differently than opening a direct connection. This distinction must be rigorously maintained across all test specifications:

```
+--------------------------------------------------------------------------------------------------------------------+
| SET ROLE TESTING vs. DIRECT-LOGIN TESTING                                                                          |
+------------------------------------+---------------------------------------+---------------------------------------+
| Attribute                          | SET ROLE Testing                      | Direct-Login Testing                  |
+------------------------------------+---------------------------------------+---------------------------------------+
| Underlying Mechanism               | Executes "SET ROLE target_role" on an | Establishes brand new TCP connection   |
|                                    | already established database session. | authenticating with target credentials.|
+------------------------------------+---------------------------------------+---------------------------------------+
| session_user State                 | Preserves original connecting role    | Equal to target_role.                 |
|                                    | (e.g., test_harness_login).           |                                       |
+------------------------------------+---------------------------------------+---------------------------------------+
| current_user State                 | Changes to target_role.               | Equal to target_role.                 |
+------------------------------------+---------------------------------------+---------------------------------------+
| What It Validates                  | Table ACLs, column privileges, and    | Real connection authentication, pool  |
|                                    | RLS policies evaluated for effective  | initialization, search_path defaults, |
|                                    | role.                                 | and session-level GUC cleanups.       |
+------------------------------------+---------------------------------------+---------------------------------------+
| Production Role Impact             | Target role can remain NOLOGIN.       | Target role must have LOGIN and       |
|                                    | (Strictly follows least privilege).   | password (Violates least privilege).  |
+------------------------------------+---------------------------------------+---------------------------------------+
| Potential False Negatives          | Misses bugs if any trigger or audit   | Accurate simulation of production     |
|                                    | function reads session_user.          | pooled connection behavior.           |
+------------------------------------+---------------------------------------+---------------------------------------+
```

#### Approved Testing Strategy for D-07
- **Capability and RLS Testing:** Execute via a dedicated unprivileged test harness login role (`college_test_harness`) having `NOINHERIT` and a single `SET ROLE` grant to `college_app_user`. This proves effective RLS behavior while allowing runtime roles (`college_app_user`, `college_worker_role`) to remain `NOLOGIN` in accordance with least privilege.
- **Direct-Login Testing:** Strictly reserved for isolated sandbox verification of connection pool mechanics, search path initialization, and GUC resets. If D-06 audit confirms that zero production paths or triggers read `session_user`, direct-login testing against runtime roles in shared or staging environments is **prohibited**.

---

### 2.3 D-16: Fail-Closed Validation for Every Connection URL Used by Test Runners

Step 6.2 noted that `tests/config.py` was vulnerable to executing tests against cloud targets. Static inspection of `tests/config.py` lines 28–35 reveals that test runners construct and utilize multiple database connection URLs:
- `DATABASE_URL` (direct/admin/migration URL)
- `DATABASE_APP_ROLE_URL` (application runtime role URL for `college_app_user`)
- `ASYNC_APP_URL`
- `ASYNC_ADMIN_URL`
- `SYNC_ADMIN_URL`
- `SYNC_APP_URL`
- Celery broker and result URLs (`REDIS_URL`)
- Any dynamic connection strings passed to pytest fixtures or worker runners.

Existing `verify_safety_guard()` in `tests/config.py` (lines 89–99) only checks `"college_app_user" in DATABASE_APP_ROLE_URL`, completely omitting hostname and network destination verification!

#### Mandatory Fail-Closed Guard Specification
Every database connection URL loaded by `tests/config.py`, pytest conftest, or CLI runners must pass the following fail-closed validation prior to opening any socket or creating an engine:

```python
from urllib.parse import urlparse
import sys

ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
DISALLOWED_CLOUD_PATTERNS = ["supabase.co", "supabase.in", "amazonaws.com", "rds.amazonaws.com"]
AUTHORIZED_LOCAL_PORT = 54322  # Dedicated local disposable Supabase port

def validate_test_connection_url(url_name: str, url_value: str) -> None:
    """Validates that a connection URL strictly targets the authorized local loopback stack.
    
    Aborts execution immediately if any URL targets cloud or non-loopback destinations.
    """
    if not url_value:
        raise SystemExit(f"CRITICAL TEST CONFIG ERROR: Missing database URL for '{url_name}'.")
    
    # Strip database driver prefixes for standard urlparse
    clean_url = url_value
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg2://", "sqlite+aiosqlite://"):
        if clean_url.startswith(prefix):
            clean_url = clean_url.replace(prefix, "postgresql://", 1)
            break

    parsed = urlparse(clean_url)
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    # 1. Strict Cloud Pattern Check
    for pattern in DISALLOWED_CLOUD_PATTERNS:
        if pattern in hostname:
            raise SystemExit(
                f"FATAL SAFETY VIOLATION: {url_name} targets cloud infrastructure ({hostname}). "
                f"Automated test execution against hosted cloud databases is strictly prohibited!"
            )

    # 2. Strict Loopback Address Check
    if hostname not in ALLOWED_LOOPBACK_HOSTS:
        raise SystemExit(
            f"FATAL SAFETY VIOLATION: {url_name} targets non-loopback host ({hostname}). "
            f"Tests must only target authorized local disposable stack (127.0.0.1)."
        )

    # 3. Port Enforcement (Local disposable Supabase CLI stack)
    if port != AUTHORIZED_LOCAL_PORT:
        raise SystemExit(
            f"FATAL SAFETY VIOLATION: {url_name} port ({port}) does not match authorized "
            f"local disposable test container port ({AUTHORIZED_LOCAL_PORT})."
        )
```

This validation must be applied across `DATABASE_URL`, `DATABASE_APP_ROLE_URL`, `ASYNC_APP_URL`, `ASYNC_ADMIN_URL`, `SYNC_ADMIN_URL`, and `SYNC_APP_URL`. If any check fails, the test runner terminates immediately with a non-zero exit code (`SystemExit`).

---

### 2.4 D-19: Layered Separation of Visitor-Token Security Mechanics

Step 6.2 correctly downgraded the Step 6.1 claim of a "High Severity Security Bypass" to a "defense-in-depth missing cryptographic binding." To ensure rigorous clarity, the visitor token mechanics must be documented across three distinct architectural layers:

```
+--------------------------------------------------------------------------------------------------------------------+
| THREE-LAYER VISITOR-TOKEN SECURITY MODEL                                                                          |
+----------------------------------+---------------------------------------------------------------------------------+
| Layer 1: Bearer Capability       | Client-to-FastAPI boundary.                                                     |
| (Client-to-Application)          | - Generated via secrets.token_urlsafe(32) (256 bits of entropy).                |
|                                  | - Stored on client (cookie or localStorage); transmitted in HTTP headers.        |
|                                  | - Only SHA-256 digest is persisted in chat_sessions.visitor_token_hash.         |
|                                  | - Application checks pre-image match via hmac.compare_digest().                 |
+----------------------------------+---------------------------------------------------------------------------------+
| Layer 2: Signed Tenant Context   | FastAPI-to-PostgreSQL transaction boundary.                                     |
| (Application-to-Database)        | - FastAPI cryptographically binds college_id into app.request_context.          |
|                                  | - Signed via HMAC-SHA256 using active key from auth_private.rls_context_keys.   |
|                                  | - Verified in PL/pgSQL via auth_private.is_request_context_valid().             |
|                                  | - Prohibits cross-tenant data access, regardless of visitor token presented.    |
+----------------------------------+---------------------------------------------------------------------------------+
| Layer 3: Database Ownership      | PostgreSQL RLS policy evaluation boundary.                                      |
| (Database-Level Enforcement)     | - Evaluated on chat_sessions and chat_messages.                                 |
|                                  | - Current (021): Compares visitor_token_hash against digest of unsigned GUC     |
|                                  |   current_setting('app.chat_visitor_token', true).                              |
|                                  | - Proposed (v2): Binds visitor_token_hash directly into signed context payload   |
|                                  |   (v2|visitor|{college_id}|{visitor_token_hash}|{expires_at}).                   |
+----------------------------------+---------------------------------------------------------------------------------+
```

#### Technical Clarification on Bypass vs. Missing Binding
- **Why There Is No Direct Authorization Bypass:** An attacker presenting an arbitrary visitor token cannot access another tenant's sessions because Layer 2 (Signed Tenant Context) strictly constrains the database session to `public.current_app_tenant()`. Furthermore, within a tenant, the attacker cannot read a victim's session unless they know the 256-bit pre-image of `visitor_token_hash`.
- **The Actual Architectural Defect:** Layer 3 in migration `021` relies on an ambient, unsigned GUC (`app.chat_visitor_token`). If application middleware sets this GUC without proper validation, the database cannot independently verify that the application verified the bearer token.
- **The Remediation:** Adopt context payload `v2` for anonymous visitor sessions, incorporating `visitor_token_hash` into the HMAC-signed payload verified by `auth_private.is_request_context_valid()`.

---

### 2.5 D-05: Distinguishing Unsafe search_path Configuration from an Actually Demonstrated Exploitation Path

In PostgreSQL security analysis, an unsafe configuration pattern must be strictly distinguished from a demonstrated, actionable exploitation path:

```
+--------------------------------------------------------------------------------------------------------------------+
| CONFIGURATION VULNERABILITY vs. DEMONSTRATED EXPLOITATION PATH                                                     |
+---------------------------------------------+----------------------------------------------------------------------+
| Aspect                                      | Technical Reality in College Chatbot Repository                      |
+---------------------------------------------+----------------------------------------------------------------------+
| Identified Configuration Defect             | 10 of 13 SECURITY DEFINER functions in migration 021 set:            |
|                                             | "SET search_path = pg_catalog, public, auth_private"                 |
+---------------------------------------------+----------------------------------------------------------------------+
| Why It Is Unsafe (CWE-426 / CVE Pattern)     | If an untrusted actor has CREATE privilege on any schema in the      |
|                                             | search_path (such as public), they can define rogue operators or     |
|                                             | shadow functions that execute with the DEFINER function's privileges.|
+---------------------------------------------+----------------------------------------------------------------------+
| Is There an Actionable Exploit Path Today?  | NO DEMONSTRATED EXPLOIT PATH:                                        |
|                                             | 1. Hardening migrations (018, 020) execute REVOKE CREATE ON SCHEMA   |
|                                             |    public FROM PUBLIC; college_app_user has USAGE only.              |
|                                             | 2. An external attacker has no direct SQL query interface.           |
|                                             | 3. Without CREATE ON SCHEMA public, an attacker cannot place rogue   |
|                                             |    objects in public to intercept search_path resolution.            |
+---------------------------------------------+----------------------------------------------------------------------+
| Correct Technical Assessment                | An unsafe defense-in-depth architectural configuration that violates |
|                                             | PostgreSQL least-privilege standards, but NOT an actively            |
|                                             | exploitable remote code execution or privilege escalation zero-day.  |
+---------------------------------------------+----------------------------------------------------------------------+
```

#### Remediation Mandate (Standardized from Migration 022)
All `SECURITY DEFINER` functions must adopt the standard implemented in migration `022`:
1. Enforce `SET search_path = pg_catalog`.
2. Fully qualify all external schema references (e.g., `FROM public.users AS account`, `FROM auth_private.rls_context_keys`).
3. Reassign function ownership to dedicated `NOLOGIN` capability roles (e.g., `college_definer_auth`, `college_definer_reg`) lacking superuser and BYPASSRLS attributes.

---

### 2.6 D-10: Signing-Key Selection, Verification-Key Overlap, Expiry, and Emergency Revocation

Migration `021` lines 16–18 and 59–64 contain an architectural flaw that prevents zero-downtime key rotation:
- Partial unique index `uq_rls_context_single_active_key` forbids more than one row with `is_active = true`.
- `auth_private.is_request_context_valid()` executes `WHERE is_active ORDER BY created_at DESC LIMIT 1`.

To support continuous operations and rapid incident response, the key lifecycle must be restructured:

```
+--------------------------------------------------------------------------------------------------------------------+
| KEY LIFECYCLE SCHEMA & STATE MACHINE (D-10)                                                                        |
+--------------------------------------------------------------------------------------------------------------------+
| 1. Table Specification (auth_private.rls_context_keys):                                                            |
|    - key_id text PRIMARY KEY                                                                                       |
|    - secret bytea NOT NULL CHECK (octet_length(secret) >= 32)                                                      |
|    - status text NOT NULL CHECK (status IN ('ACTIVE', 'PREVIOUS', 'REVOKED', 'EXPIRED'))                           |
|    - created_at timestamptz NOT NULL DEFAULT statement_timestamp()                                                 |
|    - expires_at timestamptz                                                                                        |
| 2. Structural Constraints:                                                                                         |
|    - CREATE UNIQUE INDEX uq_single_active_signing_key ON auth_private.rls_context_keys (status) WHERE status='ACTIVE';|
|    - CREATE UNIQUE INDEX uq_single_previous_key ON auth_private.rls_context_keys (status) WHERE status='PREVIOUS'; |
+--------------------------------------------------------------------------------------------------------------------+
```

#### Explicit Operational Procedures
1. **Signing-Key Selection (Application Layer):**
   - The FastAPI backend selects exclusively the key marked `status = 'ACTIVE'`. All new outgoing request contexts are signed using this key.
2. **Verification-Key Overlap (Zero-Downtime Rotation):**
   - When a new key is provisioned:
     - The current `ACTIVE` key is updated to `status = 'PREVIOUS'` with `expires_at = statement_timestamp() + interval '5 minutes'`.
     - The new key is inserted with `status = 'ACTIVE'` and `expires_at = NULL`.
   - The verifier function `auth_private.is_request_context_valid()` executes a two-phase check:
     - **Phase 1:** Attempts verification against the `ACTIVE` key. If signature matches, returns `true`.
     - **Phase 2 (Fallback):** If Phase 1 fails, checks if a key exists with `status = 'PREVIOUS' AND expires_at > statement_timestamp()`. If signature matches, returns `true`.
     - **Phase 3:** If neither matches, returns `false`.
3. **Key Expiry:**
   - Once `statement_timestamp() >= expires_at`, the `PREVIOUS` key is ignored by the fallback check. A scheduled task or subsequent rotation script transitions it to `status = 'EXPIRED'`.
4. **Emergency Revocation:**
   - In the event of secret exposure, an emergency DBA command immediately updates the compromised key's status to `'REVOKED'`:
     ```sql
     UPDATE auth_private.rls_context_keys SET status = 'REVOKED' WHERE key_id = :compromised_key_id;
     ```
   - Because `is_request_context_valid()` queries only `'ACTIVE'` or `'PREVIOUS'` keys, all in-flight or forged tokens signed with the revoked key become instantly invalid across all database sessions.

---

### 2.7 D-22: Standardization on SQLAlchemy-Compatible `CAST(:email AS text)` Syntax

In Step 6.2 section 2.1, the PostgreSQL function resolution error `function public.lookup_user_by_email_for_auth(unknown) does not exist` was diagnosed.

#### Parser Conflict in SQLAlchemy
- In SQLAlchemy with `asyncpg`, writing PostgreSQL double-colon casts inside `text()` constructs (e.g., `text("... lookup_user_by_email_for_auth(:email::text)")`) can cause parser ambiguity because SQLAlchemy interprets `:text` as a second named bind parameter unless escaped as `\:\:text`.
- Furthermore, raw unescaped `:email` leaves the parameter typed as `unknown` in the PostgreSQL parse tree, producing the `(unknown)` error signature when function resolution fails.

#### Standardized SQL Syntax
To eliminate parser conflicts across SQLAlchemy, asyncpg, and PostgreSQL, all repository call sites and SQL specifications must standardize strictly on ANSI-SQL casting:

```python
# Standardized repository query pattern in UserRepository.get_auth_account_by_email
stmt = text(
    "SELECT id, email, hashed_password, full_name, role, is_verified, is_active "
    "FROM public.lookup_user_by_email_for_auth(CAST(:email AS text))"
)
```

`CAST(:email AS text)` is natively recognized by SQLAlchemy without backslash escaping and unambiguously forces PostgreSQL to type parameter `$1` as `text` prior to candidate function selection.

---

### 2.8 D-12: Separation of Corrected Legal Rationale from Actual Retention-Policy Approval

Step 6.2 correctly struck down the claim that a 30-day purge of notification logs is "mandated by FERPA/GDPR statutory requirements," noting that FERPA does not specify 30-day operational windows and GDPR Article 5(1)(e) requires purpose-limited storage rather than a fixed universal calendar limit.

#### Critical Gate A Correction
Correcting the legal rationale for a policy **does not approve or resolve the policy**. The decision regarding data retention (D-12) remains completely unapproved:

```
+--------------------------------------------------------------------------------------------------------------------+
| LEGAL RATIONALE CORRECTION vs. RETENTION POLICY APPROVAL (D-12)                                                   |
+---------------------------------------------+----------------------------------------------------------------------+
| Corrected Legal Rationale                   | Pending Institutional Policy Approval                                |
+---------------------------------------------+----------------------------------------------------------------------+
| Clarified that 30-day notification pruning  | The Project Owner and Data Privacy Officer must still formally:      |
| is an institutional data-minimization       | 1. Decide if notification logs will be retained for 30, 60, or 90    |
| recommendation, NOT a statutory rule        |    days, or aligned with university academic record schedules.       |
| dictated by FERPA or GDPR text.             | 2. Approve the exact sanitization rule (scrubbing recipient emails,  |
|                                             |    invitation tokens, and message bodies after dispatch).            |
|                                             | 3. Authorize the scheduled Celery purge task.                        |
+---------------------------------------------+----------------------------------------------------------------------+
| Status: Rationale Corrected in Step 6.2     | Status: PENDING HUMAN DECISION — BLOCKS GATE A                       |
+---------------------------------------------+----------------------------------------------------------------------+
```

Until the Project Owner and designated Data Privacy Officer execute written sign-off on the proposed schedule, D-12 remains **PENDING HUMAN DECISION** and blocks Gate A.

---

## 3. Comprehensive Decision Register Reconciliation (D-01 through D-22)

Every decision has been re-evaluated. No decision is marked approved merely because its technical specification has been corrected.

---

### D-01: Migration History and Branch Selection
- **Current Proposed Decision:** Branch B (Forward-Only Corrective Migration). Default to leaving migrations 001–022 immutable and applying all fixes via a forward migration `023_...`.
- **Technical Evidence:** Repository contains `database/migrations/001_...` through `022_...`. CI uses in-memory SQLite. `database/README.md` documents manual execution via Supabase SQL Editor. No authoritative ledger exists proving migrations were never run.
- **Unresolved Dependencies:** Lack of written attestation from Release Owner certifying whether 001–022 were ever executed in any cloud, staging, or production instance.
- **Project-Owner Approval Required:** Yes. Must formally select Branch B (or Branch A only with attestation).
- **Specialist Approval Required:** Database Release Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live database catalog state and migration history table (`schema_migrations`) remain unverified (inspection prohibited).

---

### D-02: Shared vs. Tenant-Isolated Worker Architecture
- **Current Proposed Decision:** Separate mandatory database-level job claims and capability roles from infrastructure worker topology choices (Dedicated per-tenant workers vs. Shared worker pool with sandboxed subprocesses).
- **Technical Evidence:** `backend/app/tasks/celery_app.py` uses a single Redis queue and shared Celery worker pool. Tasks use PyMuPDF for document extraction, which carries memory corruption and parsing risks.
- **Unresolved Dependencies:** Selection of infrastructure cost/complexity model by Project Owner.
- **Project-Owner Approval Required:** Yes (budget and infrastructure topology trade-off).
- **Specialist Approval Required:** Security Architect & Worker Platform Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Worker database role and lease tables do not currently exist in the database catalog.

---

### D-03: Worker Authentication and Claim Authorization
- **Current Proposed Decision:** Mandatory `SECURITY DEFINER` claim function `claim_job(p_job_id, p_lease_duration)` issuing short-lived cryptographic lease tokens. Workers connect via dedicated `college_worker_role` (`NOLOGIN`).
- **Technical Evidence:** Tasks currently receive `college_id` via Celery JSON kwargs and assert identity via unverified GUC `set_config('app.current_college_id', ...)`.
- **Unresolved Dependencies:** Final SQL definition and grant matrix for `claim_job()`.
- **Project-Owner Approval Required:** No (technical security architecture).
- **Specialist Approval Required:** Database Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Unverified whether any legacy worker functions exist in database.

---

### D-04: Job Lease, Heartbeat, Retry, Duplicate, and Crash Handling
- **Current Proposed Decision:** 5-minute lease duration, 60-second heartbeat interval, 3 maximum retries with exponential backoff, 1-hour hard timeout to dead-letter queue, and idempotent database upserts.
- **Technical Evidence:** `crawl_jobs` and `documents` have status columns (`PROCESSING`, `COMPLETED`, `FAILED`), but lack database lease expiration columns, heartbeat timestamps, or dead-letter queues.
- **Unresolved Dependencies:** Agreement on operational timeout thresholds.
- **Project-Owner Approval Required:** Yes (operational SLA and task latency expectations).
- **Specialist Approval Required:** Distributed Systems Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Catalog lacks `lease_expires_at` and `heartbeat_at` columns.

---

### D-05: SECURITY DEFINER Ownership, Grants, search_path, and RLS
- **Current Proposed Decision:** Dedicated unprivileged `NOLOGIN` definer role hierarchy (`college_definer_auth`, `college_definer_reg`); strict `SET search_path = pg_catalog`; fully qualified schema references; revoke `PUBLIC` execute; zero superuser or BYPASSRLS ownership.
- **Technical Evidence:** Migrations 021 defines 12 definer functions with `search_path = pg_catalog, public, auth_private`. Migration 022 uses `search_path = pg_catalog` for `lookup_user_by_email_for_auth`. Function ownership is dynamically assigned to the migration runner.
- **Unresolved Dependencies:** Creation of definer capability roles in schema migration.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** PostgreSQL Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live database `pg_proc.proowner` and `proacl` remain unverified.

---

### D-06: Identity Consumers: session_user, current_user, and Signed Context
- **Current Proposed Decision:** Eliminate all `session_user` dependencies from authorization and RLS; maintain `session_user` solely as connection login; anchor all authorization in `current_user` (ACLs) and verified HMAC signed context (RLS).
- **Technical Evidence:** `backend/app/database/session.py` sets HMAC-signed GUCs. Migration 021 checks signature in `auth_private.is_request_context_valid()`. Migration 017 referenced `auth.uid() = id`.
- **Unresolved Dependencies:** Complete identity consumer inventory verifying zero queries or triggers read `session_user`.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** Application Security Engineer & Database Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live database triggers and views unverified for `session_user` references.

---

### D-07: Direct-Login Testing Requirement
- **Current Proposed Decision:** Dedicated unprivileged test harness login (`college_test_harness`) executing controlled `SET ROLE college_app_user` for RLS testing. Direct-login testing strictly required only if `session_user` is consumed.
- **Technical Evidence:** Test scripts currently use superuser connection or execute `SET ROLE`. Runtime application roles are designed to be `NOLOGIN`.
- **Unresolved Dependencies:** Formal sign-off on test harness principal definition.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** Security Test Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Test database role configuration unverified.

---

### D-08: PostgreSQL 17 Role-Membership Closure and Protected-Role Allowlist
- **Current Proposed Decision:** Enforce strict protected-role allowlist. Execute cycle-safe recursive CTE query inspecting `set_option`, `inherit_option`, and `admin_option` in `pg_auth_members` to verify zero transitive escalation paths to superuser or table owners.
- **Technical Evidence:** Step 4 provided the recursive query specification. PostgreSQL 17 introduces granular role attributes in `pg_auth_members`.
- **Unresolved Dependencies:** Formal approval of the protected role set.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** PostgreSQL Database Administrator.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live `pg_auth_members` catalog state unverified.

---

### D-09: Unprivileged Negative-Test Principal
- **Current Proposed Decision:** Create a dedicated, disposable, completely unprivileged test principal (`negative_test_user`) with `LOGIN`, `NOINHERIT`, zero application memberships, and zero table grants to differentiate table ACL vs RLS denials.
- **Technical Evidence:** Existing tests lack an independent unprivileged principal, risking confusion between RLS row-level filters and table-level permission errors.
- **Unresolved Dependencies:** SQL specification for `negative_test_user`.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** QA / Security Test Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Presence of negative test fixtures in database unverified.

---

### D-10: Signing-Key Storage, Access, and Rotation
- **Current Proposed Decision:** External secret store management; adopt `ACTIVE` / `PREVIOUS` dual-key schema in `auth_private.rls_context_keys`; 5-minute transition overlap window; drop partial unique index; support emergency status update to `REVOKED`.
- **Technical Evidence:** Migration 021 lines 16–18 enforce single active key index, preventing zero-downtime rotation. Application uses `RLS_CONTEXT_SECRET` (32 bytes).
- **Unresolved Dependencies:** Key management runbook and migration dropping the unique partial index.
- **Project-Owner Approval Required:** Yes (operational key custody policy).
- **Specialist Approval Required:** Key Management Specialist & Application Security Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live contents of `auth_private.rls_context_keys` unverified.

---

### D-11: Password-Reset Email Delivery Provider or Deferral
- **Current Proposed Decision:** Formally defer/disable self-service password reset in production until a verified transactional email provider (SES, SendGrid, Resend) is contracted and configured with SPF/DKIM/DMARC.
- **Technical Evidence:** `backend/app/services/email_transport.py` implements a mock transport. Password reset tokens are currently discarded or logged.
- **Unresolved Dependencies:** Business contracting of transactional email provider vs. formal code deferral.
- **Project-Owner Approval Required:** Yes (product capability decision).
- **Specialist Approval Required:** Communications Privacy & Security Specialist.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** N/A (application/service layer).

---

### D-12: Notification Email Retention and Data Minimization
- **Current Proposed Decision:** Institutional 30-day bounded retention schedule for notification logs; mandatory scrubbing of recipient email addresses, tokens, and bodies after dispatch; automated Celery purge task.
- **Technical Evidence:** `backend/app/models/notification.py` defines `InAppNotification`. No automated pruning task exists in repository.
- **Unresolved Dependencies:** Formal institutional data retention schedule approval.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** Data Privacy & Compliance Officer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Database table rows and retention state unverified.

---

### D-13: Public College Registration versus Super Admin-Only Registration
- **Current Proposed Decision:** Public registration form inserts records into `college_registrations` with status `PENDING` only. Provisioning active tenants in `colleges` and admin users is strictly restricted to authenticated Super Admins.
- **Technical Evidence:** `apps/admin-frontend` provides registration form. Migration 021 defines `submit_public_college_registration(jsonb)`.
- **Unresolved Dependencies:** Registration state machine sign-off.
- **Project-Owner Approval Required:** Yes (onboarding business model).
- **Specialist Approval Required:** Application Security Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** RLS policies on `college_registrations` unverified in catalog.

---

### D-14: EDITOR and VIEWER Permission Matrix
- **Current Proposed Decision:** Fail-closed RBAC: `VIEWER` is strict read-only; `EDITOR` can upload documents and edit drafts but cannot publish live knowledge base chunks or delete documents; `COLLEGE_ADMIN` holds publishing rights.
- **Technical Evidence:** Enums in migration 003 define user and membership roles. Intermediate dashboard roles (`EDITOR`, `VIEWER`) lack database-enforced boundaries.
- **Unresolved Dependencies:** Formal RBAC matrix signed by Product and Security leads.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** Application Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Role enum values and table grants unverified in catalog.

---

### D-15: Audit Payload and AI Telemetry Allowlists and Redaction
- **Current Proposed Decision:** Strict key allowlist for audit JSONB payloads; automatic PII/credential redactor; AI telemetry records only aggregate numerical metrics (`tokens`, `latency_ms`) and categorized error codes; raw prompts and exception stack traces prohibited.
- **Technical Evidence:** Migration 008 creates `audit_logs` (`payload_before`, `payload_after`) and `ai_provider_events` (`error_message`, `prompt_tokens`). `_log_telemetry` records API calls.
- **Unresolved Dependencies:** Approved schema allowlist specification and unit test suite.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** AI Operations Lead & Privacy Officer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Unverified whether telemetry tables currently contain unredacted rows.

---

### D-16: Creation of a New Disposable Supabase-Compatible Test Environment
- **Current Proposed Decision:** Provision a fresh, isolated local Supabase stack via official CLI on loopback (`127.0.0.1:54322`); enforce fail-closed connection guards across all test URLs; strictly prohibit connecting to hosted cloud Supabase.
- **Technical Evidence:** `tests/config.py` loads `.env` targeting cloud Supabase. Vanilla PostgreSQL test container in Step 2 lacked Supabase `auth` schema and roles.
- **Unresolved Dependencies:** Docker compose manifest and startup script for local disposable Supabase CLI stack.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** DevOps / Platform Engineer & Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Local disposable test stack not yet instantiated.

---

### D-17: Implementation Authorization and Separate Production Approval
- **Current Proposed Decision:** Enforce strict staged gate separation: Gate A (Design Approval) $\to$ Gate B (Implementation in Local Test Stack) $\to$ Gate C (Security & Database Validation) $\to$ Production Approval.
- **Technical Evidence:** All audit reports (Steps 2–6.2) record that implementation is unauthorized.
- **Unresolved Dependencies:** Formal written designation of accountable human authorizers.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** Lead System Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** N/A (governance control).

---

### D-18: Application Identity Model and Supabase auth.uid() Boundary
- **Current Proposed Decision:** Standardize on custom HMAC-signed application context (`public.current_app_user_id()`, `public.current_app_tenant()`); formally deprecate and remove all application-level dependencies on Supabase `auth.uid()`.
- **Technical Evidence:** FastAPI issues custom JWTs. Migration 021 replaces `auth.uid()` policies with `current_app_user_id()`. PostgREST is not exposed to untrusted clients.
- **Unresolved Dependencies:** Architectural Decision Record (ADR) sign-off.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** Identity & Auth Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** RLS policies in live catalog unverified for lingering `auth.uid()` calls.

---

### D-19: Visitor Token Lifetime and Anonymous Feedback
- **Current Proposed Decision:** Cryptographically random 32-byte visitor bearer token; 24-hour absolute non-sliding expiration; matching visitor token strictly required for chat feedback; adopt `v2` signed context payload incorporating `visitor_token_hash`.
- **Technical Evidence:** `backend/app/api/v1/chat.py` generates visitor tokens. Migration 021 checks `app.chat_visitor_token` GUC in RLS policies.
- **Unresolved Dependencies:** Specification of context payload `v2` format.
- **Project-Owner Approval Required:** Yes (student experience policy).
- **Specialist Approval Required:** Application Security Engineer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Live chat session rows and token expiration status unverified.

---

### D-20: Guest Support-Ticket Permissions
- **Current Proposed Decision:** Guest support tickets are strictly create-only (write-once); prospective students receive zero database read, update, or reply permissions; follow-ups handled exclusively via email.
- **Technical Evidence:** `backend/app/services/support_service.py` allows unauthenticated ticket creation. `SupportTicket` model permits nullable `user_id`.
- **Unresolved Dependencies:** Product support workflow specification.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** RLS policies on `support_tickets` unverified in catalog.

---

### D-21: College Chat Analytics and Raw Conversation Access
- **Current Proposed Decision:** College Admins have access to aggregate metrics only (query volume, trends, sentiment, popular unanswered questions); zero direct browse access to raw student chat logs or transcripts unless escalated to a ticket.
- **Technical Evidence:** `apps/admin-frontend` analytics page queries aggregated endpoints. `backend/app/repositories/college_admin_repository.py` queries messages.
- **Unresolved Dependencies:** Analytics data governance policy approval.
- **Project-Owner Approval Required:** Yes.
- **Specialist Approval Required:** Data Privacy Officer.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** RLS policies and views for analytics unverified in catalog.

---

### D-22: Sensitive User-Column Access and Authentication Lookup Contract
- **Current Proposed Decision:** Standardize on minimal 7-field projection (`id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, `is_active`) via `public.lookup_user_by_email_for_auth(CAST(:email AS text))`; zero direct `SELECT` on `users.hashed_password` for application roles.
- **Technical Evidence:** Migration 022 implements 7-field projection. `UserRepository.get_auth_account_by_email` executes the function. Test logs show `lookup_user_by_email_for_auth(unknown) does not exist`.
- **Unresolved Dependencies:** Formal sign-off on the 7-field authentication contract.
- **Project-Owner Approval Required:** No.
- **Specialist Approval Required:** Application Security Engineer & Database Security Architect.
- **Blocks Gate A:** **YES**.
- **Database Evidence Unverified:** Presence and signature of `lookup_user_by_email_for_auth` in live database catalog remain unverified (inspection prohibited).

---

## 4. Decision Register Summary Matrix

```
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
| ID  | Focus Area                        | Review Rec.        | Approvers Required     | Blocks Gate A | DB State Verified? |
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
| D-01| Migration History & Branching     | Branch B (Forward) | Owner + Release Eng.   | YES           | NO (Unverified)    |
| D-02| Worker Process Isolation          | Sandboxed / Claim  | Owner + Sec. Architect | YES           | NO (Unverified)    |
| D-03| Worker Claim Authentication       | claim_job() & Role | DB Sec. Architect      | YES           | NO (Unverified)    |
| D-04| Job Lease, Heartbeat & Recovery   | 5m lease / 60s hb  | Owner + Systems Eng.   | YES           | NO (Unverified)    |
| D-05| SECURITY DEFINER & search_path    | pg_catalog / Roles | PostgreSQL Sec. Arch.  | YES           | NO (Unverified)    |
| D-06| Identity Layer Separation         | Signed Context     | AppSec + DB Architect  | YES           | NO (Unverified)    |
| D-07| Direct-Login vs. SET ROLE Testing | SET ROLE Harness   | Sec. Test Engineer     | YES           | NO (Unverified)    |
| D-08| PG 17 Role Closure & Allowlist    | Recursive CTE      | PostgreSQL DBA         | YES           | NO (Unverified)    |
| D-09| Negative Principal Isolation      | negative_test_user | QA / Sec. Test Eng.    | YES           | NO (Unverified)    |
| D-10| Key Rotation & Dual Verification  | Dual-Key Schema    | Owner + Key Mgmt Spec. | YES           | NO (Unverified)    |
| D-11| Password-Reset Email Handling     | Formal Deferral    | Owner + Privacy Spec.  | YES           | N/A (App Level)    |
| D-12| Notification Data Retention       | 30-Day Purge       | Owner + Privacy Off.   | YES           | NO (Unverified)    |
| D-13| College Registration Flow         | Pending Only       | Owner + AppSec         | YES           | NO (Unverified)    |
| D-14| Staff RBAC Matrix (Editor/Viewer) | Strict Read-Only   | Owner + AppSec         | YES           | NO (Unverified)    |
| D-15| Audit & Telemetry Redaction       | Strict Allowlist   | Owner + AI Sec. Lead   | YES           | NO (Unverified)    |
| D-16| Disposable Test Stack Isolation   | Local Loopback     | DevOps + Sec. Arch.    | YES           | NO (Unverified)    |
| D-17| Staged Gate Authorization Model   | 3-Gate Control     | Owner + Lead Architect | YES           | N/A (Governance)   |
| D-18| Application Identity Boundary     | Deprecate auth.uid | Identity Architect     | YES           | NO (Unverified)    |
| D-19| Visitor Token Lifecycle & Payload | 24h Fixed / v2     | Owner + AppSec         | YES           | NO (Unverified)    |
| D-20| Guest Support Ticket Boundary     | Create-Only        | Owner + Sec. Architect | YES           | NO (Unverified)    |
| D-21| College Chat Analytics Privacy    | Aggregate Only     | Owner + Privacy Off.   | YES           | NO (Unverified)    |
| D-22| Auth Lookup Function Contract     | CAST(:email AS text| AppSec + DB Architect  | YES           | NO (Unverified)    |
+-----+-----------------------------------+--------------------+------------------------+---------------+--------------------+
```

---

## 5. Gate A Readiness Checklist & Next Actions

### 5.1 Why Gate A is NOT Complete
Although technical consistency, architectural rigor, and security specifications have been fully established and reconciled across all 22 decisions, **Gate A remains NOT COMPLETE** because:
1. **Human Project Owner Decisions (D-01, D-02, D-04, D-10, D-11, D-12, D-13, D-14, D-15, D-17, D-19, D-20, D-21):** Formal written selections have not yet been recorded.
2. **Technical Specialist Sign-offs (D-01 through D-22):** Named specialists have not yet affixed written approvals.
3. **Missing Documentary Artifacts:** Key management runbooks, authoritative migration ledgers, and data retention schedules remain unsubmitted.

### 5.2 Actionable Next Steps to Achieve Gate A Completion
1. **Present Deliverable to Project Owner:** Present this Step 6.3 document alongside the Step 6 decision register to the accountable Project Owner.
2. **Record Owner Selections:** Capture formal, signed decisions on the 13 project-owner items.
3. **Convene Specialist Review:** Circulate the technical specifications to the designated engineering specialists for formal sign-off.
4. **Archive Sign-off Ledger:** Once all signatures are collected, record Gate A as **COMPLETE**.
5. **Formulate Gate B Request:** Formulate the isolated implementation plan for execution exclusively inside an authorized local disposable Supabase test container equipped with fail-closed URL guards.

---

## 6. Concluding Evaluation Status

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — FINAL TECHNICAL REVIEW COMPLETE — NO IMPLEMENTATION AUTHORIZED
================================================================================
```

*Report compiled under strict read-only constraints. Zero application modifications, database queries, migration executions, or credential exposures were performed.*
