# Phase 3A.4.4B — Step 7: Controlled Implementation Plan and Gate B/C Authorization Request
*(Incorporating Final Consistency Corrections and Technical Accuracy Reconciliations)*

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, PostgreSQL 17 Specialist, DevOps Security Engineer, Database Migration Specialist, PostgreSQL RLS Specialist, Independent Technical Auditor  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Baseline Deliverable:** [Step 6.3.6.2 Final Editorial Reconciliation and Remediation Handoff](./PHASE_3A_4_4B_STEP_6_3_6_2_FINAL_EDITORIAL_RECONCILIATION_AND_REMEDIATION_HANDOFF.md)  
**Deliverable Document:** `PHASE_3A_4_4B_STEP_7_CONTROLLED_IMPLEMENTATION_PLAN_AND_GATE_AUTHORIZATION_REQUEST.md`

---

## 1. Executive Summary

This document establishes the **Controlled Implementation Plan and Formal Gate Authorization Request** for Phase 3A.4.4B. It transitions the project out of iterative documentation audits into an actionable, technically accurate operational roadmap to resolve the outstanding security, database, and authentication issues of the College Chatbot multi-tenant platform.

### Core Objectives of This Plan
1. **Empirical Diagnosis of Authentication Failure:** Define a technically rigorous diagnostic sequence for runtime error `public.lookup_user_by_email_for_auth(unknown) does not exist (Error 42883)` without assuming unverified runtime outcomes.
2. **Reconciled Authentication Return Contract:** Document the exact seven-column contract (`is_verified` vs `college_id`) verified from repository source code.
3. **Migration Safety Protocol & Idempotency Realities:** Establish a provisional forward-only remediation proposal (Branch B, pending formal decision on D-01) respecting PostgreSQL DDL return-type constraints, manual migration execution realities, and distinguishing local replay from hosted migration history.
4. **PostgreSQL 17 Disposable Test Stack Specification:** Specify an official image (`pgvector/pgvector:pg17`) that actually provides `pgvector`, `pgcrypto`, and `uuid-ossp`, distinguishing database-level compatibility from the complete Supabase platform.
5. **Hardened Fail-Closed Loopback Isolation Architecture:** Specify an uncompromised loopback connection validator binding strictly to `127.0.0.1:54322`, validating credentials, preventing environment overrides, handling parsing errors, and distinguishing Docker port binding from outbound host network egress.
6. **Conditional Security Validation Matrix:** Document test specifications strictly conditional upon verified policies, table ACL grants, context function logic, and runtime exceptions.
7. **Strict Gate Governance:** Enforce the four-stage gate sequence (Gate A $\to$ Gate B $\to$ Gate C $\to$ Production), ensuring all 22 decisions remain pending human Project Owner approval with delegation unestablished.

```
================================================================================
GOVERNANCE POSTURE & VERDICT:
STEP 7 TECHNICAL PLAN RECONCILED — AWAITING FORMAL HUMAN DECISIONS AND SEPARATE IMPLEMENTATION AUTHORIZATION
================================================================================
```

---

## 2. Current Project Status & Baseline Facts

### 2.1 Verified Static Codebase Facts
- **SQL Migrations:** Migrations `001` through `022` exist as standalone SQL files in `database/migrations/`.
  - Migration `021_phase3a42_security_onboarding.sql` (lines 165–176) defines `public.lookup_user_by_email_for_auth(p_email text)` returning `SETOF public.users` with `SET search_path = pg_catalog, public, auth_private`.
  - Migration `022_minimize_auth_lookup.sql` (lines 14–25) drops and recreates `public.lookup_user_by_email_for_auth(p_email text)` returning a restricted 7-field table (`id uuid, email text, hashed_password text, full_name text, role text, is_verified boolean, is_active boolean`) with `SET search_path = pg_catalog`.
- **Application Data Access Layer:** `backend/app/repositories/user_repository.py` (lines 15–25) defines `AuthUserLookup` expecting these exact 7 fields (`id`, `email`, `hashed_password`, `full_name`, `role`, `is_verified`, `is_active`) and invokes (lines 43–44):
  ```python
  text("SELECT id, email, hashed_password, full_name, role, is_verified, is_active FROM public.lookup_user_by_email_for_auth(:email)")
  ```
- **Service Integration:** `backend/app/services/auth_service.py` (`authenticate` method, line 75) and `backend/app/api/v1/auth.py` (`/login` endpoint, line 75) consume `UserRepository.get_auth_account_by_email`.
- **Connection Configuration:** `backend/app/database/connection.py` configures connection pooling (`pool_size=10, max_overflow=20`) using `postgresql+asyncpg://`.
- **Migration Execution Method:** Static inspection reveals no automated database migration runner (such as Alembic, Flyway, or Sqitch) is configured in the repository. Migrations have historically been executed manually (e.g. via psql or Supabase SQL Editor). No automated migration tracking table (such as `schema_migrations`) is guaranteed to exist.
- **Test Configuration:** `tests/config.py` loads `.env` directly and derives connection strings without fail-closed host validation, presenting a risk of targeting remote cloud Supabase if `.env` points to hosted infrastructure.

### 2.2 Unverified Live Runtime State
- **Target Database Catalog State:** Live catalog objects (`pg_proc`, `pg_namespace`, `pg_roles`, `pg_auth_members`) remain uninspected.
- **Migration Execution History:** Which migrations (`001` through `022`) have been applied, partially applied, or omitted in the target database remains unknown.
- **Runtime Failure:** Test execution logs document the active runtime failure:
  ```
  public.lookup_user_by_email_for_auth(unknown) does not exist (PostgreSQL 42883)
  ```

---

## 3. Workstream A — Authentication Error Diagnostic Plan & Contract Reconciliation

### 3.1 Reconciled Authentication Return Contract
Static inspection resolves the documentary discrepancy regarding returned columns:

```
+---+------------------+-----------------------+-----------------------------+------------------------------------+
| # | Column Name      | PostgreSQL Data Type  | Python Dataclass Attribute  | Repository Query Projection        |
+---+------------------+-----------------------+-----------------------------+------------------------------------+
| 1 | id               | uuid                  | id: uuid.UUID               | SELECT id                          |
| 2 | email            | text                  | email: str                  | email                              |
| 3 | hashed_password  | text                  | hashed_password: str        | hashed_password                    |
| 4 | full_name        | text                  | full_name: str              | full_name                          |
| 5 | role             | text                  | role: str                   | role                               |
| 6 | is_verified      | boolean               | is_verified: bool           | is_verified                        |
| 7 | is_active        | boolean               | is_active: bool             | is_active                          |
+---+------------------+-----------------------+-----------------------------+------------------------------------+
```

#### Contract Reconciliation Findings:
1. **`is_verified` vs. `college_id`:** The sixth projected attribute is `is_verified` (`boolean`). In `022_minimize_auth_lookup.sql`, `college_id` is **not** returned by `lookup_user_by_email_for_auth`. In the application architecture, user-to-college associations are resolved downstream through `college_memberships` or signed request context (`app.current_college_id`). Earlier documentary references to `college_id` as part of the 7 returned fields were erroneous descriptions of the 022 contract.
2. **Column Order & Model Alignment:** The column order in `022_minimize_auth_lookup.sql` lines 18–24 exactly matches `AuthUserLookup` in `user_repository.py` lines 18–24 and the SQL query projection in line 43.
3. **Legacy Contract (021) Nuance:** Migration `021` returned `SETOF public.users`. Calling the 022 query projection (`SELECT id, email, ...`) against a database where migration 021 was applied but 022 was omitted represents an unverified runtime condition. Whether it would execute successfully (projecting matching columns from `SETOF public.users`) or fail depends on live catalog definitions and asyncpg mapping, which must be tested empirically rather than assumed.

---

### 3.2 Diagnostic Decision Tree & PostgreSQL Overload Realities
PostgreSQL error `42883: undefined_function` indicates that PostgreSQL cannot locate a routine matching the specified identifier and argument types in the candidate search path.

```
+-------------------------------------------------------------------------------------------------------------------------+
| DIAGNOSTIC DECISION TREE: public.lookup_user_by_email_for_auth(unknown) does not exist (Error 42883)                    |
+-------------------------------------------------------------------------------------------------------------------------+
                                                             |
                           [Step 1: Live Catalog Inspection in Disposable DB]
                                                             |
                             SELECT p.oid, p.proname, pg_get_function_identity_arguments(p.oid),
                                    pg_get_function_result(p.oid), p.proowner, p.prosecdef
                             FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                             WHERE n.nspname = 'public' AND p.proname = 'lookup_user_by_email_for_auth';
                                                             |
                               +-----------------------------+-----------------------------+
                               |                                                           |
                         [Row Not Found]                                              [Row Found]
                               |                                                           |
                   (Function Absent in public)                                             |
                               |                                                           |
             +-----------------+-----------------+                                         |
             |                                   |                                         |
     [Target State Unknown]             [Manual DDL Anomaly]                               |
             |                                   |                                         |
   Migration 021/022 was               Migration was executed on                           |
   never executed, executed            different database, was                             |
   in different schema, or             rolled back, or was                                 |
   failed during manual run.           manually dropped/altered.                           |
             |                                   |                                         |
             +-----------------+-----------------+                                         |
                               |                                                           |
                               v                                                           v
              [Must Replay Baseline Sequentially]                 [Inspect Argument Types & Overload Resolution]
                                                                                           |
                                                              +----------------------------+----------------------------+
                                                              |                                                         |
                                                    [Arg Incompatible with text]                              [Arg == text (OID 25)]
                                                              |                                                         |
                                                    Non-coercible signature                                             |
                                                    (e.g. integer or multiple args).                            |
                                                    Note: varchar is binary-coercible                           |
                                                    to text; won't fail solely on varchar.                      |
                                                    PostgreSQL fails 42883.                                     |
                                                              |                                                         |
                                                              +----------------------------+----------------------------+
                                                                                           |
                                                                           [Evaluate Parameter Typing & Driver]
                                                                                           |
                                                                           Inspect generated asyncpg statement protocol:
                                                                           Does driver send untyped bind or explicit OID?
                                                                                           |
                                                              +----------------------------+----------------------------+
                                                              |                                                         |
                                                    [Parameter Sent as unknown]                               [Explicit Parameter Type]
                                                              |                                                (e.g. via CAST(:email AS text))
                                                    Asyncpg passes untyped param;                                       |
                                                    planner fails overload                                              |
                                                    resolution -> Error 42883.                                          |
                                                              |                                                         |
                                                              +----------------------------+----------------------------+
                                                                                           |
                                                                           [Check Schema USAGE & Function EXECUTE]
                                                                                           |
                                                              +----------------------------+----------------------------+
                                                              |                                                         |
                                                    [USAGE on public Missing]                                 [EXECUTE Missing]
                                                              |                                                         |
                                                    Raises Error 42501:                                       Raises Error 42501:
                                                    "permission denied for schema public"                     "permission denied for function"
                                                    (Does NOT raise 42883!)                                   (Does NOT raise 42883!)
                                                              |                                                         |
                                                              +----------------------------+----------------------------+
                                                                                           |
                                                                           [Inspect Downstream Execution & Contract]
                                                                                           |
                                                              +----------------------------+----------------------------+
                                                              |                                                         |
                                                    [Return Columns Diverge]                                  [Invocation Exception]
                                                              |                                                         |
                                                    Function returns SETOF users                              Runtime exception inside
                                                    (021) or missing columns;                                 routine (e.g. search_path
                                                    UserRepository raises KeyError /                          resolution failure);
                                                    pydantic ValidationError.                                 Statement aborts with PL/pgSQL error.
```

### 3.3 Diagnostic Nuances: Parameter Typing & Coercion
- **PostgreSQL Implicit Coercion:** PostgreSQL allows implicit and binary-coercible conversions between string category types (`varchar` and `text`). A function expecting `text` will not produce error `42883` merely because a `varchar` argument is provided. However, when an untyped literal or unparameterized placeholder (`unknown`) is submitted in a prepared statement context, PostgreSQL's parser cannot always resolve overload candidates, leading to `42883`.
- **SQLAlchemy / asyncpg Behavior:** Whether asyncpg passes an explicit type OID (e.g. OID 25 for `text`) or an unspecified type OID (`0` / `unknown`) depends on how the query is compiled and whether bind parameters are explicitly typed in SQLAlchemy. Actual parameter typing must be empirically confirmed from frontend/backend protocol messages during Gate C validation, not presumed.
- **Scope of `CAST(:email AS text)`:** Explicitly casting the parameter resolves parameter typing during query planning **only if** `public.lookup_user_by_email_for_auth(text)` exists in the catalog. It **cannot** create a missing routine or bypass catalog permissions.

---

## 4. Workstream B — Migration Safety & DDL Idempotency Plan

### 4.1 Provisional Status of Branch B
- **Provisional Planning Default:** Branch B (forward-only corrective migration `023_...`) is the recommended technical approach while deployment history remains unknown.
- **Governance Requirement:** **Branch B has not been approved.** Decision D-01 remains pending formal human decision by the Project Owner.
- **Branch A Restriction:** Destructive baseline consolidation (Branch A) remains prohibited unless authoritative written documentation certifies that migrations `001`–`022` were never executed in any target environment.

### 4.2 PostgreSQL DDL Realities: Return Types, RESTRICT, and CASCADE
1. **`CREATE OR REPLACE FUNCTION` Return-Type Constraint:**
   - In PostgreSQL, `CREATE OR REPLACE FUNCTION` **cannot change the return type or output parameter list of an existing function**.
   - Attempting to replace a function returning `SETOF public.users` (migration 021) with `RETURNS TABLE (...)` (migration 022) using `CREATE OR REPLACE` fails immediately with:
     ```
     ERROR: 42P13: cannot change return type of existing function
     ```
2. **`DROP FUNCTION` Dependency Semantics (RESTRICT vs. CASCADE):**
   - By default, PostgreSQL executes `DROP FUNCTION ... RESTRICT`. If dependent objects (e.g. views, triggers, or other routines) rely on the function, the command aborts with an error.
   - Specifying `CASCADE` drops the function and recursively drops all dependent objects.
   - In either case, dropping a function removes routine-level `GRANT EXECUTE` permissions, routine ownership, and comments. Any corrective script must explicitly restore non-superuser ownership and re-grant `EXECUTE` permissions.
3. **`IF NOT EXISTS` Limitations:**
   - `IF NOT EXISTS` tests only whether an object identifier exists; it does **not** verify that columns, data types, nullability constraints, or search paths match expectations.

### 4.3 Sequential Baseline Reproduction vs. Hosted Database Reality
Because migrations have historically been applied manually without an automated migration runner or ledger table:
1. **Ad-Hoc Migration Prohibited:** Migrations `021` or `022` must not be executed independently or out-of-order in an attempt to fix missing objects.
2. **Sequential Baseline Reproduction in Test Stack:** In the fresh disposable test stack, all migrations (`001` through `022`) will be replayed sequentially in topological order to produce a **local reference schema**.
3. **Critical Governance Principle — Local Replay vs. Hosted History:**
   > [!IMPORTANT]
   > Replaying migrations `001` through `022` sequentially in a local disposable container produces an idealized reference schema, but **does NOT establish or prove the actual migration history of the hosted or remote Supabase database**.
   > Hosted migration history can ONLY be determined through an authoritative written deployment ledger (Evidence Package 1) or authorized read-only catalog queries against the target database during Gate C.
4. **Corrective DDL Authoring:** Only after catalog divergence is empirically documented between the local baseline and the target cluster may a forward-only migration (`023_reconcile_auth_lookup_and_security.sql`) be authored and submitted for approval.

---

## 5. Workstream C — Isolated PostgreSQL 17 Disposable Test Environment

### 5.1 Version Alignment & Database Compatibility Scope
To eliminate version discrepancies across project artifacts (resolving the previous PostgreSQL 15 reference against D-08's PostgreSQL 17 role membership requirements):
- **Intended Major Version:** **PostgreSQL 17.x** (matching PostgreSQL 17.11 tested in earlier phases and D-08's `pg_auth_members` `INHERIT TRUE, SET FALSE` semantics).
- **Required Available Extensions:** `vector` (pgvector), `pgcrypto`, and `uuid-ossp`.
- **Selected Image:** **`pgvector/pgvector:pg17`** (or `pgvector/pgvector:0.8.0-pg17`). Standard official `postgres:17` and `postgres:17-alpine` images include `pgcrypto` and `uuid-ossp` (standard contrib modules), but do **not** include `pgvector`. The official `pgvector/pgvector:pg17` image provides PostgreSQL 17 with `pgvector` pre-compiled and standard contrib packages pre-installed.
- **Scope of Supabase Compatibility:**
  > [!NOTE]
  > The disposable test stack provides **PostgreSQL database-level compatibility** for the application's schema and extension requirements (`vector`, `pgcrypto`, `uuid-ossp`, and custom schemas like `auth`).
  > It does **NOT** provide the complete Supabase platform (which comprises GoTrue/Auth server, PostgREST API gateway, Realtime server, Storage API, Kong, and Supabase Studio).
  > The College Chatbot backend interacts purely at the database level via asyncpg/SQLAlchemy; it does not utilize Supabase HTTP platform APIs.
- **Initialization Reality (auth Schema):** Standard PostgreSQL images (including `pgvector/pgvector:pg17`) do **not** initialize the Supabase `auth` schema or its internal functions out of the box. To achieve database compatibility:
  - An initialization script (`000_init_supabase_compat.sql`) must be mounted to `/docker-entrypoint-initdb.d/` to execute `CREATE SCHEMA IF NOT EXISTS auth;` and create minimal required stubs before migrations `001`–`022` execute.

```
+-----------------------------------------------------------------------------------------------------------------------+
| TEST ENVIRONMENT CAPABILITY MATRIX (POSTGRESQL 17 BASELINE)                                                           |
+--------------------------------------+------------------------------------+-------------------------------------------+
| Component / Capability               | Full Supabase CLI Local Stack      | Standalone pgvector/pgvector:pg17 Stack   |
+--------------------------------------+------------------------------------+-------------------------------------------+
| PostgreSQL Major Version             | Managed by CLI (often PG 15)       | EXACT PG 17.x BASELINE                    |
| PostgREST / GoTrue / Studio / Kong   | Included (Spawns 10+ containers)   | NOT Included (Database only)              |
| Pre-installed pgvector Extension     | Included                           | Pre-compiled and available                |
| Contrib (pgcrypto, uuid-ossp)        | Included                           | Pre-installed in image                    |
| Supabase auth Schema                 | Pre-seeded                         | Initialized via 000_init_compat script    |
| Resource Footprint                   | High (~2GB RAM, multiple ports)    | Lightweight (~250MB RAM, single port)     |
| Application Requirement Fit          | Unnecessary (FastAPI uses asyncpg) | EXACT FIT for backend & test harness      |
+--------------------------------------+------------------------------------+-------------------------------------------+
```

### 5.2 Hardened Fail-Closed Connection Validation
The connection validator in `tests/config.py` must enforce fail-closed loopback execution, handling URL parsing errors, credentials verification, and preventing environment overrides:

```python
import os
import sys
from urllib.parse import urlparse

# Expected disposable local test credentials (strictly non-production)
EXPECTED_TEST_USERS = {"college_app_user", "postgres"}
EXPECTED_TEST_PASSWORDS = {"DISPOSABLE_LOCAL_APP_PASSWORD", "DISPOSABLE_LOCAL_DEV_PASSWORD"}

def assert_disposable_loopback_target(url: str) -> None:
    """Enforces strict fail-closed connection boundaries for test execution.
    
    Validates:
      - Handles URL parsing exceptions cleanly without leakage
      - Driver scheme strictly matches 'postgresql+asyncpg://' or 'postgresql://'
      - Hostname strictly matches IPv4 literal '127.0.0.1' (localhost rejected to prevent IPv6/DNS ambiguity)
      - Port strictly matches disposable test port 54322
      - Database name strictly matches disposable test database 'postgres'
      - Credentials strictly match expected disposable local test fixtures
      - Rejects query parameters, multiple comma-separated hosts, and hosted Supabase/cloud domains.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise RuntimeError("FATAL: Database connection URL is empty or malformed. Test execution aborted.")
        
    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        raise RuntimeError(f"FATAL: Database connection URL parsing failed: {exc}. Execution terminated.") from exc

    # 1. Driver Scheme Validation
    if parsed.scheme not in ("postgresql+asyncpg", "postgresql"):
        raise RuntimeError(f"FATAL: Prohibited driver scheme '{parsed.scheme}'. Only asyncpg/psycopg2 permitted.")
        
    # 2. Hostname Validation (Strict IPv4 loopback literal)
    if parsed.hostname != "127.0.0.1":
        raise RuntimeError(
            f"FATAL: Prohibited database host '{parsed.hostname}'. "
            "Tests strictly require literal '127.0.0.1'. 'localhost' and external hosts are forbidden."
        )
        
    # 3. Port Validation
    if parsed.port != 54322:
        raise RuntimeError(f"FATAL: Prohibited port '{parsed.port}'. Disposable test stack must run on 54322.")
        
    # 4. Database Name Validation
    db_name = (parsed.path or "").lstrip("/")
    if db_name != "postgres":
        raise RuntimeError(f"FATAL: Prohibited database '{db_name}'. Expected disposable database 'postgres'.")
        
    # 5. Credentials & Secret Validation
    username = parsed.username
    password = parsed.password
    if username not in EXPECTED_TEST_USERS:
        raise RuntimeError(f"FATAL: Prohibited test user '{username}'. Only disposable test principals permitted.")
    if password not in EXPECTED_TEST_PASSWORDS:
        raise RuntimeError("FATAL: Unrecognized database password. Production credentials strictly forbidden.")

    # 6. Query Parameter & Multiple Host Rejection
    if parsed.query:
        raise RuntimeError(f"FATAL: Prohibited query parameters detected in test connection URL: '{parsed.query}'.")
    if "," in (parsed.netloc or ""):
        raise RuntimeError("FATAL: Multiple hosts detected in connection URL. Routing ambiguity forbidden.")
        
    # 7. Hosted Supabase / Cloud Rejection
    raw_lower = url.lower()
    if any(cloud in raw_lower for cloud in ("supabase.co", "pooler.supabase.com", "aws.com", "rds.amazonaws.com")):
        raise RuntimeError("FATAL: Hosted cloud Supabase or cloud endpoint detected! Execution terminated.")
```

#### Environment Override Protocol:
To prevent parent process environment bleed (e.g. if `.env` defines a production cloud URL), the test suite runner must load `.env.test.local` with explicit variable override:
```python
from dotenv import load_dotenv
# Explicitly override any pre-existing environment variables from parent shell or .env
load_dotenv(".env.test.local", override=True)
```

### 5.3 Docker Networking vs. Outbound Egress Isolation
- **Docker Port Binding:** Binding published container ports strictly to `127.0.0.1:54322` prevents external machines on the network from accessing the container.
- **Outbound Host Egress Limitation:** Docker port binding does **not** prevent the host Python test runner process from opening outbound connections to external databases. To guarantee complete egress isolation during test execution, the test suite must rely on the fail-closed URL validator above, combined with an isolated environment file (`.env.test.local`) that contains zero external credentials and explicitly overrides any production `.env` variables.

---

## 6. Workstream D — Security Validation Plan

### 6.1 Conditional Test Matrix (ACLs vs. RLS vs. Context Exceptions)
All test expectations are **conditional upon verified catalog policies, table grants, and context function logic**, rather than guaranteed invariant outcomes.

```
+----+-----------------------------+-------------------------------+--------------------------+-------------------------------------------------------------+
| #  | Test Vector                 | Execution Principal           | Target Object / Action   | Conditional Expected Outcome                                |
+----+-----------------------------+-------------------------------+--------------------------+-------------------------------------------------------------+
| 1  | Schema USAGE Access         | college_app_user              | Schema public            | Success if USAGE granted; Error 42501 if USAGE revoked.     |
| 2  | Private Schema Access       | college_app_user              | Schema auth_private      | DENIED: Error 42501 (Schema USAGE ACL denied).              |
| 3  | Auth Function Execution     | college_app_user              | lookup_user_by_email...  | Success: Returns 7 fields if EXECUTE granted & text param.  |
| 4  | Direct User Table Select    | college_app_user (No Context) | Table public.users       | Filtered: 0 rows if policy active & context returns false.  |
| 5  | User Table Select (AIT)     | college_app_user (AIT Signed) | Table public.users       | Returns AIT rows if policy matches tenant & context valid.  |
| 6  | Cross-Tenant Select (RCTI)  | college_app_user (AIT Signed) | Table public.users       | Filtered: 0 rows if USING clause filters cross-tenant rows. |
| 7  | Cross-Tenant Insert (RCTI)  | college_app_user (AIT Signed) | Table public.documents   | DENIED: Error 42501 if WITH CHECK clause rejects violation. |
| 8  | Direct Superuser Alteration | college_app_user              | ALTER ROLE ... SUPERUSER | DENIED: Error 42501 (insufficient_privilege ACL).           |
| 9  | Unauthorized Role Switch    | college_app_user              | SET ROLE test_synth_admin| DENIED: Error 42501 (SET ROLE privilege denied).            |
| 10 | Context Signature Tamper    | college_app_user (Bad HMAC)   | Any RLS-protected table  | Filtered: 0 rows if function returns false; or error if exc.|
| 11 | Expired Context Token       | college_app_user (Expired)    | Any RLS-protected table  | Filtered: 0 rows if function returns false; or error if exc.|
| 12 | Malformed GUC Syntax        | college_app_user (Bad Regex)  | Any RLS-protected table  | Statement error / Exception if cast fails, else 0 rows.     |
| 13 | Table ACL Absence           | Unprivileged Test Role        | Table public.users       | DENIED: Error 42501 (Table SELECT ACL denied before RLS).   |
| 14 | Definer Search Path Check   | System Catalog Inspection     | All definer functions    | search_path = pg_catalog                                    |
+----+-----------------------------+-------------------------------+--------------------------+-------------------------------------------------------------+
```

#### Diagnostic Breakdown of Conditional Context Failure Modes:
1. **Context Function Returning `false`:** Under `021_phase3a42_security_onboarding.sql`, `auth_private.is_request_context_valid()` returns `false` when HMAC verification fails or `expires_at` is expired. When combined in a policy via `USING (auth_private.is_request_context_valid() AND ...)`, `SELECT` statements evaluate to `false` and return `0 rows` without error **only if** no other permissive policy grants access.
2. **RLS `WITH CHECK` Rejection:** For `INSERT` or `UPDATE`, evaluating to `false` in `WITH CHECK` triggers PostgreSQL error `42501: new row violates row-level security policy` **only if** the policy is enforced.
3. **Malformed GUC Exception:** If a GUC contains a non-numeric string where `expires_at::bigint` is cast without prior regex validation, PostgreSQL throws a PL/pgSQL casting exception (aborting the query with an error), rather than returning zero rows.
4. **Table ACL Denial:** If `college_app_user` lacks table-level `SELECT` privilege on `public.users`, PostgreSQL raises `42501: permission denied for table users` immediately before RLS policies are evaluated.

---

## 7. Workstream E — D-01 through D-22 Decision Tracker

Every decision remains **`[PENDING HUMAN DECISION]`**. In the absence of an executed Delegation of Authority document (Package 6), all decisions require formal approval by the Project Owner.

```
+-----+---------------------------------------+-----------------------------+------------------------------------+-----------------------+---------------------------------------+-----------+--------------------------+
| ID  | Decision Title                        | Recommended Option          | Required Evidence                  | Decision Owner        | Specialist Advice Domain              | Gate A Blk| Current Status           |
+-----+---------------------------------------+-----------------------------+------------------------------------+-----------------------+---------------------------------------+-----------+--------------------------+
| D-01| Migration History & Branch Selection  | Branch B (Provisional)      | Certified deployment ledger (Pkg 1)| Project Owner (Pend.) | Database Release Engineer             | YES       | [PENDING HUMAN DECISION] |
| D-02| Shared vs. Isolated Worker Model      | Database Claims + Sandboxing| Worker Architecture Spec (Pkg 3)   | Project Owner (Pend.) | Worker Platform Lead & Security Arch. | YES       | [PENDING HUMAN DECISION] |
| D-03| Worker Claim Authentication           | NOLOGIN role + claim_job()  | Worker Architecture Spec (Pkg 3)   | Project Owner (Pend.) | Database Security Architect           | YES       | [PENDING HUMAN DECISION] |
| D-04| Job Lease & Heartbeat SLAs            | 5m lease, 60s heartbeat     | Worker Architecture Spec (Pkg 3)   | Project Owner (Pend.) | Distributed Systems Engineer          | YES       | [PENDING HUMAN DECISION] |
| D-05| SECURITY DEFINER Hardening            | SET search_path = pg_catalog| Catalog audit & migration 023 DDL  | Project Owner (Pend.) | PostgreSQL Security Architect         | YES       | [PENDING HUMAN DECISION] |
| D-06| Identity Architecture & session_user  | Signed context for RLS/audit| Asyncpg pooling evaluation         | Project Owner (Pend.) | AppSec Engineer & Database Architect  | YES       | [PENDING HUMAN DECISION] |
| D-07| Direct-Login Testing Harness          | Unprivileged test harness   | Test Stack Specification (Pkg 5)   | Project Owner (Pend.) | Security Test Engineer                | YES       | [PENDING HUMAN DECISION] |
| D-08| PG 17 Role Closure Allowlist          | Recursive auth_members check| Role graph audit script            | Project Owner (Pend.) | PostgreSQL Database Administrator     | YES       | [PENDING HUMAN DECISION] |
| D-09| Unprivileged Negative-Test Principal  | Synthetic test roles        | Test Stack Specification (Pkg 5)   | Project Owner (Pend.) | QA / Security Test Engineer           | YES       | [PENDING HUMAN DECISION] |
| D-10| Key Storage, Access, and Rotation     | Dual-key schema & external  | Key Management Runbook (Pkg 2)     | Project Owner (Pend.) | Key Management Specialist & AppSec    | YES       | [PENDING HUMAN DECISION] |
| D-11| Password-Reset Email Delivery/Defer   | Defer self-service in prod  | Service contract or product waiver | Project Owner (Pend.) | Communications Privacy Specialist     | YES       | [PENDING HUMAN DECISION] |
| D-12| Notification Retention (30-day)       | 30-day retention & scrub    | Privacy Policy Document (Pkg 4)    | Project Owner (Pend.) | Data Privacy & Compliance Officer     | YES       | [PENDING HUMAN DECISION] |
| D-13| College Registration Workflow         | Pending status + admin sign | Registration workflow spec         | Project Owner (Pend.) | Application Security Engineer         | YES       | [PENDING HUMAN DECISION] |
| D-14| EDITOR & VIEWER Permission Matrix     | Strict fail-closed RBAC     | RBAC matrix document               | Project Owner (Pend.) | Application Security Architect        | YES       | [PENDING HUMAN DECISION] |
| D-15| Audit & AI Telemetry Redaction        | Strict JSONB allowlist      | Privacy Policy Document (Pkg 4)    | Project Owner (Pend.) | Data Privacy Officer & AI Ops Lead    | YES       | [PENDING HUMAN DECISION] |
| D-16| Disposable Supabase Test Environment  | Loopback local stack only   | Test Stack Specification (Pkg 5)   | Project Owner (Pend.) | DevOps Engineer & Security Architect  | YES       | [PENDING HUMAN DECISION] |
| D-17| 4-Stage Gate Separation               | Strict Gate A/B/C separation| Delegation Document (Pkg 6)        | Project Owner (Pend.) | Lead System Architect                 | YES       | [PENDING HUMAN DECISION] |
| D-18| Custom Context vs Supabase auth.uid() | Standardize custom context  | Architectural Decision Record (ADR)| Project Owner (Pend.) | Identity & System Architect           | YES       | [PENDING HUMAN DECISION] |
| D-19| Visitor Token Lifetime (24h)          | 24h absolute non-sliding    | Anonymous Chat API Specification   | Project Owner (Pend.) | Application Security Engineer         | YES       | [PENDING HUMAN DECISION] |
| D-20| Guest Support Ticket Permissions      | Create-only guest tickets   | Support workflow policy document    | Project Owner (Pend.) | Security Architect                    | YES       | [PENDING HUMAN DECISION] |
| D-21| College Chat Analytics Privacy        | Aggregate metrics only      | Privacy Policy Document (Pkg 4)    | Project Owner (Pend.) | Data Privacy Officer                  | YES       | [PENDING HUMAN DECISION] |
| D-22| Sensitive Column Access & Auth Role   | Dedicated college_auth_role | Auth Role Architecture Spec         | Project Owner (Pend.) | AppSec Engineer & Database Architect  | YES       | [PENDING HUMAN DECISION] |
+-----+---------------------------------------+-----------------------------+------------------------------------+-----------------------+---------------------------------------+-----------+--------------------------+
```

---

## 8. Workstream F — Six Evidence Packages Checklist

```
+----+---------------------------------------------------------------+--------------+----------------------------------+-----------------------+---------------------------------------+-------------------+
| #  | Evidence Package Name                                         | Status       | Responsible Role                 | Required Reviewer     | Required Completion Evidence          | Decisions Supported|
+----+---------------------------------------------------------------+--------------+----------------------------------+-----------------------+---------------------------------------+-------------------+
| 1  | Authoritative Migration History and Deployment Ledger         | MISSING      | Database Release Engineer        | Project Owner         | Signed environment migration audit log| D-01              |
| 2  | Key Management and Rotation Runbook                           | MISSING      | Key Management Specialist        | AppSec Engineer       | Formal KMS key custody & rotation SOP | D-10              |
| 3  | Worker Authentication and Isolation Architecture              | INCOMPLETE   | Worker Platform Lead             | Security Architect    | Completed queue routing & DDL spec    | D-02, D-03, D-04  |
| 4  | Data Retention and Privacy Schedule                           | MISSING      | Data Privacy & Compliance Officer| Project Owner         | Signed 30-day retention & scrub policy| D-12, D-15, D-21  |
| 5  | Local Disposable Supabase Stack Specification                 | INCOMPLETE   | DevOps / Platform Engineer       | Security Architect    | Tested loopback Compose manifest & DDL| D-05–D-09, D-16   |
| 6  | Delegation of Authority and Approval Ownership Document       | MISSING      | Project Owner / Corporate Legal  | Independent Auditor   | Executed delegation charter for Gates | D-03, D-17, D-18  |
+----+---------------------------------------------------------------+--------------+----------------------------------+-----------------------+---------------------------------------+-------------------+
```

---

## 9. Gate A/B/C Authorization Requirements & Sequence

```
+-----------------------------------------------------------------------------------------------------------------------+
| CONTROLLED MULTI-STAGE EXECUTION SEQUENCE                                                                             |
+-----------------------------------------------------------------------------------------------------------------------+
|                                                                                                                       |
|  [STAGE 1: GATE A — DESIGN & GOVERNANCE APPROVAL]                                                                     |
|  - Execute written Project Owner decisions on D-01 through D-22.                                                      |
|  - Author and archive the 6 Evidence Packages (Packages 1, 2, 4, 6 from MISSING; Packages 3, 5 from INCOMPLETE).     |
|  - Collect specialist technical advice sign-offs across all 13 domains.                                               |
|  - FORMAL GATE A CLOSURE CERTIFICATE ISSUED.                                                                          |
|                                     |                                                                                 |
|                                     v                                                                                 |
|  [STAGE 2: GATE B — TEST IMPLEMENTATION AUTHORIZATION]                                                                |
|  - Submit formal Gate B implementation request with strict file allowlist.                                            |
|  - Authorized scope limited to: test configuration, disposable Docker manifests, and test fixtures.                  |
|  - Zero production application code or live migration modifications permitted.                                        |
|  - FORMAL GATE B IMPLEMENTATION APPROVAL ISSUED.                                                                      |
|                                     |                                                                                 |
|                                     v                                                                                 |
|  [STAGE 3: GATE C — ISOLATED DATABASE VALIDATION]                                                                     |
|  - Provision local disposable pgvector/pgvector:pg17 container stack on 127.0.0.1:54322.                             |
|  - Execute sequential migration replay (001–022) to establish local reference schema.                                 |
|  - Execute catalog diagnosis for public.lookup_user_by_email_for_auth.                                                |
|  - Run security test matrix (ACLs, RLS, negative fixtures).                                                           |
|  - Generate reproducible diagnostic and validation report.                                                            |
|  - Destroy disposable environment.                                                                                    |
|  - FORMAL GATE C VALIDATION CERTIFICATE ISSUED.                                                                       |
|                                     |                                                                                 |
|                                     v                                                                                 |
|  [STAGE 4: PRODUCTION DEPLOYMENT AUTHORIZATION]                                                                       |
|  - Review Gate C validation evidence.                                                                                 |
|  - Author deployment runbook, rollback script, and backup verification.                                              |
|  - Secure separate, independent human production release sign-off.                                                    |
|  - EXECUTE PRODUCTION RELEASE.                                                                                        |
+-----------------------------------------------------------------------------------------------------------------------+
```

---

## 10. Risk Register

```
+----+------------------------------------+----------+--------+---------------------------------------------------------------------------------------+
| #  | Risk Description                   | Severity | Impact | Mitigation Strategy                                                                   |
+----+------------------------------------+----------+--------+---------------------------------------------------------------------------------------+
| 1  | Accidental Cloud Connection        | CRITICAL | HIGH   | Implement fail-closed loopback check in tests/config.py; reject any non-127.0.0.1 host.|
| 2  | Migration History Drift            | HIGH     | HIGH   | Enforce Branch B (provisional); preflight check all catalog objects prior to DDL.     |
| 3  | Privilege Escalation Fixture Leak  | CRITICAL | HIGH   | Use synthetic roles (test_synthetic_admin); prohibit postgres/supabase_admin in tests.  |
| 4  | Connection Pool Identity Bleed     | HIGH     | HIGH   | Document session_user as connection principal; enforce HMAC-signed context for RLS.   |
| 5  | Return-Type Alteration Failure     | HIGH     | MEDIUM | Plan DROP/CREATE transactionally for return-type changes; do not rely on CREATE OR REP|
| 6  | Premature Production Execution     | CRITICAL | HIGH   | Strict 4-stage gate separation; Gate C success does not authorize production release. |
+----+------------------------------------+----------+--------+---------------------------------------------------------------------------------------+
```

---

## 11. Explicit Exclusions and Prohibited Actions

Under this plan and during the upcoming authorization request, the following actions remain **STRICTLY PROHIBITED**:

- **No Live Database Connections:** Connecting to hosted cloud Supabase, staging, or production databases.
- **No Direct Migration Application:** Applying migrations `021`, `022`, or drafts to any existing database environment.
- **No Unauthorized File Edits:** Modifying application source code (`backend/app/`), migration files, `.env` files, or production configurations.
- **No Production Testing:** Running tests against any database other than the authorized loopback-bound disposable container.
- **No Uncontrolled Role Manipulation:** Altering production database roles, granting superuser rights, or modifying live permissions.
- **No Bypassing Human Authorization:** Treating technical reviews as approval substitutes or automatically jumping from Gate A to Gate B/C.

---

## 12. Final Recommendation & Handoff

The technical and operational roadmap for resolving Phase 3A.4.4B is fully established. Further documentation audits will produce no new information. 

**The immediate actionable next steps are:**
1. **Present This Plan to the Project Owner:** Request formal human decisions on the D-01 through D-22 decision register and commission the 6 outstanding evidence packages to clear **Gate A**.
2. **Request Gate B Authorization:** Following Gate A clearance, request explicit written authorization to prepare the disposable local test harness and execute the diagnostic sequence under **Gate C**.

```
================================================================================
FINAL STEP 7 STATUS:
STEP 7 TECHNICAL PLAN RECONCILED — AWAITING FORMAL HUMAN DECISIONS AND SEPARATE IMPLEMENTATION AUTHORIZATION
================================================================================
```
