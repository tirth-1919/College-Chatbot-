# Phase 3A.4.4B — Step 6.2: Technical Findings Correction and Consolidation

**Evaluation Date:** 2026-11-16  
**Roles & Specialties:** Senior PostgreSQL Security Architect, Supabase Security Engineer, Application Security Engineer, Technical Project Reviewer  
**Local Workspace:** `C:\Users\HP\OneDrive\Desktop\College Chatbot`  
**GitHub Remote Backup:** `https://github.com/tirth-1919/College-Chatbot-`  
**Predecessor Documents:** 
- [Step 6 Human Decision Resolution Package](./phase3a4.4b-step6-human-decision-resolution.md)
- [Step 6.1 Technical Consistency & Auth Diagnostic](./phase3a4.4b-step6.1-technical-consistency-and-auth-diagnostic.md)
**Deliverable Document:** `.agents/tasks/phase3a4.4b-step6.2-technical-findings-correction.md`

---

## 1. Executive Decision

```
================================================================================
FINAL EVALUATION STATUS:
READY FOR HUMAN DECISION — TECHNICAL FINDINGS CONSOLIDATED — NO IMPLEMENTATION AUTHORIZED
================================================================================
```

This report performs a strictly read-only technical correction, consolidation, and refinement of the findings presented in Step 6.1. Every security finding and architectural observation has been re-evaluated against static repository evidence to ensure that:

1. **Source-code and migration-design defects** are strictly separated from **unverified runtime database state**.
2. **Missing cryptographic bindings** are distinguished from **demonstrated authorization bypasses**.
3. **Statutory compliance claims** (FERPA/GDPR) are corrected to reflect **institutional policy proposals**.
4. **Mandatory database safety boundaries** are enforced without executing queries or modifying configuration.

No application code, SQL migrations, database roles, table privileges, RLS policies, Docker containers, volumes, configuration files, or environment secrets have been altered.

---

## 2. Evidence-Based Technical Findings

### 2.1 Authentication Lookup Diagnostic (D-22)

#### The Observed Runtime Error
Existing test execution logs record the following failure during `/api/v1/auth/login`:
```
function public.lookup_user_by_email_for_auth(unknown) does not exist
```

#### Codebase Call-Chain Trace
1. **Endpoint:** `backend/app/api/v1/auth.py` lines 69–75 invokes `AuthService.authenticate(req)`.
2. **Service Layer:** `backend/app/services/auth_service.py` line 75 calls `UserRepository.get_auth_account_by_email(req.email)`.
3. **Repository Layer:** `backend/app/repositories/user_repository.py` lines 38–49 executes:
   ```python
   async def get_auth_account_by_email(self, email: str) -> Optional[AuthUserLookup]:
       normalized_email = email.lower().strip()
       result = await self.session.execute(
           text(
               "SELECT id, email, hashed_password, full_name, role, is_verified, is_active "
               "FROM public.lookup_user_by_email_for_auth(:email)"
           ),
           {"email": normalized_email},
       )
       row = result.mappings().one_or_none()
       return AuthUserLookup(**row) if row else None
   ```

#### SQLAlchemy Parameter-Binding & PostgreSQL Parser Analysis
- In SQLAlchemy with `asyncpg`, raw SQL constructed via `text("... (:email)")` binds `:email` as positional parameter `$1`.
- When PostgreSQL parses the statement, if the parameter lacks an explicit SQL type cast (`$1::text` or `CAST($1 AS text)`), its initial data type in the parse tree is `unknown`.
- PostgreSQL's function resolution algorithm (`parse_func.c`) searches for candidates named `public.lookup_user_by_email_for_auth`:
  - If a single candidate taking type `text` exists in schema `public`, PostgreSQL coerces the `unknown` parameter to `text`, and resolution succeeds.
  - If **no function with that name exists in schema `public`** (or if the connecting user lacks `USAGE` on schema `public`), PostgreSQL cannot resolve the parameter type or function. It terminates resolution and raises error code `42883` (`undefined_function`), citing the unresolved argument type: `(unknown)`.
- **Assessment of `CAST(:email AS text)`:** Adding an explicit cast (e.g., `FROM public.lookup_user_by_email_for_auth(CAST(:email AS text))`) ensures PostgreSQL types the parameter as `text` prior to function candidate lookup. While this prevents the error message from saying `(unknown)`, the query will still fail with `function public.lookup_user_by_email_for_auth(text) does not exist` if the function is absent from the catalog.

#### Precise Diagnostic Conclusion
Step 6.1 asserted that migrations 021 and 022 were "unapplied." However, because live catalog inspection is prohibited and migration ledgers are unverified, asserting historical database state exceeds repository evidence. The technically accurate and evidence-grounded conclusion is:

```
================================================================================
DIAGNOSTIC CONCLUSION:
FUNCTION RESOLUTION FAILURE — DATABASE CATALOG STATE UNVERIFIED
================================================================================
```
The application repository code (`user_repository.py`) strictly requires `public.lookup_user_by_email_for_auth(p_email text)` returning the 7-column projection defined in migration `022`. In the database target reached during test execution, this function could not be resolved by the query parser. Whether this is due to migration 021/022 never having been applied, partial application, schema placement, or permission revoking remains **unverified** pending authorized catalog inspection.

---

### 2.2 Visitor-Token Security Lifecycle (D-19)

#### Complete Lifecycle Trace Across Code and Migrations
1. **Token Generation:** 
   - `backend/app/api/v1/chat.py` line 138: For anonymous users (`current_user is None`), the server generates a cryptographically secure 32-byte URL-safe string:
     ```python
     visitor_token = secrets.token_urlsafe(32)
     ```
2. **Token Storage & Persistence:**
   - `backend/app/api/v1/chat.py` lines 145–147: The raw token is returned to the client in the response payload, while only its SHA-256 digest is stored in PostgreSQL:
     ```python
     visitor_token_hash = hashlib.sha256(visitor_token.encode("utf-8")).hexdigest()
     ```
   - Persisted into `chat_sessions.visitor_token_hash` (`character varying(64)`).
3. **Request Context Construction & HMAC Signing:**
   - `backend/app/database/session.py` lines 96–106:
     ```python
     payload = (
         f"v1|{user_id_str}|{college_id_str}|{is_super_str}|"
         f"{email_verification_str}|{expires_at}"
     )
     signature = base64.urlsafe_b64encode(
         hmac.new(signing_key, payload.encode("utf-8"), hashlib.sha256).digest()
     ).decode("ascii").rstrip("=")
     ```
   - **Architectural Observation:** The `visitor_token` (or its hash) is **not included** in `payload`.
4. **Database GUC Assignment:**
   - `backend/app/database/session.py` line 118:
     ```python
     set_config('app.chat_visitor_token', :visitor_token, true)
     ```
   - Executed with `is_local = true` (scoped to transaction).
5. **PostgreSQL Context Validation:**
   - Migration `021` lines 21–83: `auth_private.is_request_context_valid()` recalculates the HMAC using the active secret in `auth_private.rls_context_keys`. Because `app.chat_visitor_token` is not in the signed payload, context validation does not verify the visitor token.
6. **RLS Policy Evaluation:**
   - Migration `021` lines 455–462 (`p_chat_sessions_tenant`) and lines 494–502 (`p_chat_messages_tenant`):
     ```sql
     OR (
         user_id IS NULL
         AND public.current_app_user_id() IS NULL
         AND college_id = public.current_app_tenant()
         AND visitor_token_hash IS NOT NULL
         AND visitor_token_hash = encode(
             public.digest(COALESCE(current_setting('app.chat_visitor_token', true), ''), 'sha256'),
             'hex'
         )
     )
     ```
7. **Application-Layer Ownership Enforcement:**
   - `backend/app/api/v1/chat.py` lines 45–59 (`_assert_session_ownership`):
     ```python
     if current_user is None:
         if (
             chat_session.user_id is None
             and visitor_token
             and chat_session.visitor_token_hash
             and hmac.compare_digest(
                 hashlib.sha256(visitor_token.encode("utf-8")).hexdigest(),
                 chat_session.visitor_token_hash,
             )
         ):
             return
         raise HTTPException(status_code=403, detail="A valid chat visitor token is required...")
     ```
8. **Token Expiration:**
   - In application code, chat sessions remain active indefinitely unless cleaned up; Step 6 recommends a hard 24-hour absolute non-sliding expiry.

#### Authorization Bypass vs. Missing Cryptographic Binding
- **Can an untrusted caller manipulate `app.chat_visitor_token` and satisfy policy conditions?**
  - **No demonstrated authorization bypass exists.** To satisfy the RLS policy for an anonymous session, a caller must satisfy three concurrent conditions:
    1. `college_id = public.current_app_tenant()`: Must match the HMAC-signed, tamper-proof tenant context. An attacker cannot forge this for another college.
    2. `public.current_app_user_id() IS NULL`: Must be an anonymous session.
    3. `visitor_token_hash = encode(digest(current_setting('app.chat_visitor_token'), 'sha256'), 'hex')`: Must match the 256-bit SHA-256 pre-image of the random bearer token generated by `secrets.token_urlsafe(32)`.
  - Furthermore, the FastAPI application independently verifies ownership via `hmac.compare_digest` before returning messages.
- **The Actual Defect: Missing Cryptographic Binding:**
  - `app.chat_visitor_token` is an unsigned GUC.
  - While it does not enable an external attacker to bypass session isolation without knowing the secret token, it represents a defense-in-depth architectural gap: the database relies on an ambient, unsigned setting rather than validating that the caller's bearer capability is bound to the signed request transaction.

#### Proposed Secure Design
To establish complete cryptographic binding:
1. Extend context versioning to support anonymous visitor sessions:
   - When `user_id` is null and `visitor_token` is present:
     `v2|visitor|{college_id}|{visitor_token_hash}|{expires_at}`
2. Update `auth_private.is_request_context_valid()` to verify this signature.
3. Replace direct GUC reads in RLS policies with a verified helper:
   ```sql
   AND visitor_token_hash = public.current_chat_visitor_hash()
   ```
   where `public.current_chat_visitor_hash()` returns the hash only if verified by the HMAC signature.

---

### 2.3 Comprehensive SECURITY DEFINER Review (D-05)

Every `SECURITY DEFINER` function across migrations `001_extensions.sql` through `022_minimize_auth_lookup.sql` was inspected. All 14 occurrences are located exclusively in migrations `021` and `022`:

```
+-----------------------------------------------------------+---------+---------------------------------+---------------------+---------------------+-----------------------+
| Function Signature                                        | Migr.   | Search Path                     | Schema Qual. Refs?  | PUBLIC Revoked?     | Explicit Role Grants  |
+-----------------------------------------------------------+---------+---------------------------------+---------------------+---------------------+-----------------------+
| auth_private.is_request_context_valid()                   | 021     | pg_catalog, auth_private        | Yes                 | Yes (PUBLIC, app)   | None (Internal only)  |
| public.current_app_user_id()                              | 021     | pg_catalog, auth_private        | Yes                 | Yes (PUBLIC)        | college_app_user      |
| public.current_app_tenant()                               | 021     | pg_catalog, auth_private        | Yes                 | Yes (PUBLIC)        | college_app_user      |
| public.is_platform_super_admin()                          | 021     | pg_catalog, auth_private        | Yes                 | Yes (PUBLIC)        | college_app_user      |
| public.is_current_college_admin()                         | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.user_belongs_to_tenant(uuid, uuid)                 | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.lookup_user_by_email_for_auth(text)                | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.lookup_college_invitation_by_token(text)           | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.accept_college_admin_invitation(text, ...)        | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.submit_public_college_registration(jsonb)          | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.check_public_registration_availability(text, text) | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.get_public_registration_status(text)               | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.submit_public_registration_information(...)        | 021     | pg_catalog, public, auth_priv   | Partially           | Yes (PUBLIC)        | college_app_user      |
| public.lookup_user_by_email_for_auth(text)                | 022     | pg_catalog                      | Fully qualified     | Yes (PUBLIC)        | college_app_user      |
+-----------------------------------------------------------+---------+---------------------------------+---------------------+---------------------+-----------------------+
```

#### Detailed Findings on Function Security
1. **Function Ownership:**
   - In migration `021`, no `ALTER FUNCTION ... OWNER TO ...` statements exist. In PostgreSQL, `proowner` defaults to `CURRENT_USER` (the role executing the migration). In repository files, this owner is **unspecified**. If run by `postgres` or `supabase_admin`, functions execute with superuser/BYPASSRLS privileges.
   - In migration `022`, lines 9–13 dynamically queries `v_function_owner` from `pg_proc` and restores it (`ALTER FUNCTION ... OWNER TO v_function_owner`). If the prior owner was a superuser, superuser ownership is preserved.
2. **Search Path Vulnerability in Migration 021:**
   - 10 of the 13 functions in migration `021` set `SET search_path = pg_catalog, public, auth_private`.
   - Leaving `public` in the search path of a `SECURITY DEFINER` function allows unprivileged users with `CREATE` privilege on schema `public` to define malicious operators or shadow internal routines.
   - **Correction in Migration 022:** Migration `022` correctly sets `SET search_path = pg_catalog` and explicitly schema-qualifies all table references (`FROM public.users AS account`). This hardening must be extended to all definer functions.
3. **RLS & FORCE ROW LEVEL SECURITY Behavior:**
   - A `SECURITY DEFINER` function executes under its owner's privileges. If the owner possesses `rolsuper=true` or `rolbypassrls=true`, queries inside the function bypass all RLS policies, even if `FORCE ROW LEVEL SECURITY` is enabled on the table.
   - To enforce least privilege, definer functions must be owned by dedicated `NOLOGIN` capability roles (e.g., `college_definer_auth`, `college_definer_reg`) that lack superuser and BYPASSRLS attributes, with grants restricted to the specific tables accessed by those routines.

---

### 2.4 Key Rotation & Dual-Key Overlap Conflict (D-10)

#### The Schema vs. Recommendation Conflict
Step 6 D-10 specifies:
> *"Dual-key overlap: The database verifier must support an active key for signing and allow a 5-minute transition window for previous key verification to enable zero-downtime key rotation."*

However, in migration `021_phase3a42_security_onboarding.sql`:
1. **Schema Constraint:** Lines 16–18:
   ```sql
   CREATE UNIQUE INDEX uq_rls_context_single_active_key
       ON auth_private.rls_context_keys (is_active)
       WHERE is_active;
   ```
   This partial unique index strictly prevents more than one row in `auth_private.rls_context_keys` from having `is_active = true`.
2. **Function Query:** Lines 59–64 of `auth_private.is_request_context_valid()`:
   ```sql
   SELECT key.secret
     INTO v_secret
     FROM auth_private.rls_context_keys AS key
    WHERE key.is_active
    ORDER BY key.created_at DESC
    LIMIT 1;
   ```
   The query only retrieves a single secret (`LIMIT 1`).

#### Impact
Under migration `021` as written, attempting to insert a second active key to facilitate zero-downtime rotation triggers a unique constraint violation. Deactivating the old key immediately invalidates in-flight HTTP requests signed seconds earlier, causing intermittent 403 authorization failures during rotation.

#### Required Specification for True Zero-Downtime Rotation
```
+--------------------------------------------------------------------------------------------------+
| PROPOSED ROTATION LIFECYCLE SCHEMA                                                               |
+--------------------------------------------------------------------------------------------------+
| 1. Table Schema:                                                                                 |
|    - key_id text PRIMARY KEY                                                                     |
|    - secret bytea NOT NULL CHECK (octet_length(secret) >= 32)                                    |
|    - status text NOT NULL CHECK (status IN ('ACTIVE', 'PREVIOUS', 'REVOKED'))                    |
|    - expires_at timestamptz                                                                      |
|    - created_at timestamptz DEFAULT now()                                                        |
| 2. Constraints:                                                                                  |
|    - CREATE UNIQUE INDEX uq_single_active_key ON rls_context_keys (status) WHERE status='ACTIVE';|
|    - CREATE UNIQUE INDEX uq_single_prev_key ON rls_context_keys (status) WHERE status='PREVIOUS';|
| 3. Verifier Function Logic:                                                                      |
|    - Step A: Verify signature against the ACTIVE key. If valid -> RETURN true.                   |
|    - Step B: If invalid, retrieve PREVIOUS key WHERE status='PREVIOUS' AND expires_at > now().   |
|              If valid -> RETURN true.                                                            |
|    - Step C: Otherwise -> RETURN false.                                                          |
| 4. Emergency Revocation: Immediate status update to 'REVOKED' purges key from verification.   |
+--------------------------------------------------------------------------------------------------+
```

---

### 2.5 Worker Architecture & Feasible Isolation (D-02)

#### Codebase Reality Check
- **Broker & Queue:** A single Redis instance (`REDIS_URL`) and single Celery queue (`backend/app/tasks/celery_app.py`).
- **Database Engine:** A single shared async engine (`async_engine` in `connection.py`) using `DATABASE_APP_ROLE_URL` (`college_app_user`).
- **Task Execution:** Tasks (`crawler_tasks.py`, `document_tasks.py`, `knowledge_tasks.py`) receive `college_id` via Celery JSON kwargs and open sessions via `tenant_session(college_id=college_id)`.

#### Separation of Mandatory Security Controls vs. Infrastructure Choices
To reconcile D-02 with operational reality, security controls must be separated into mandatory database controls and optional infrastructure topologies:

```
+---------------------------------------------------+---------------------------------------------------+
| MANDATORY DATABASE CONTROLS                       | OPTIONAL INFRASTRUCTURE CHOICES                   |
| (Required regardless of worker pool model)        | (Project owner operational / budget trade-off)    |
+---------------------------------------------------+---------------------------------------------------+
| 1. Cryptographic Job Claim Function:             | Option A: Dedicated Per-Tenant Workers            |
|    - Worker cannot assert college_id via GUC.     | - Separate Celery worker process per college.     |
|    - claim_job(job_id, worker_id, lease_duration) | - Separate Redis queues per tenant.               |
|      validates ownership and returns lease token. | - Maximum blast radius protection.                |
| 2. Dedicated Worker Database Role:                | - High memory & infrastructure cost.              |
|    - college_worker_role (NOLOGIN capability role)|                                                   |
|    - Cannot access web users, passwords, or auth. | Option B: Shared Worker Pool with Subprocess Sandbox|
| 3. Connection Reset Hooks:                        | - Single shared Celery worker pool.               |
|    - Explicit RESET ALL on connection return.     | - Celery max_tasks_per_child = 10 to clear heap.  |
| 4. Bounded Lease & Heartbeat (D-04):              | - PyMuPDF / OCR executed in sandboxed subprocess. |
|    - 5-min lease, 60s heartbeat, max 3 retries.   | - Moderate infrastructure cost.                   |
+---------------------------------------------------+---------------------------------------------------+
```

---

### 2.6 Test Environment Safety & Fail-Closed Validation (D-16)

#### The Observed Safety Gap
1. `tests/config.py` loads `.env`.
2. `.env` configures `DATABASE_URL` and `DATABASE_APP_ROLE_URL` targeting `db.mefdzpqoestdwcyhnbxt.supabase.co:5432` (hosted cloud Supabase).
3. Running `python manage.py test-all` or `pytest backend/tests` locally inadvertently connects to a **remote cloud database**.
4. CI (`.github/workflows/ci.yml`) sets `DATABASE_URL: sqlite+aiosqlite:///:memory:`, which fails to test PostgreSQL RLS policies.

#### Minimum Local Disposable Supabase Stack Requirements
- Isolated local Docker stack managed via official Supabase CLI (`supabase start`).
- Dedicated loopback network binding: PostgreSQL on `127.0.0.1:54322`, API on `127.0.0.1:54321`.
- Standard Supabase roles initialized: `postgres`, `anon`, `authenticated`, `service_role`, `supabase_admin`.
- Extensions initialized: `pgvector`, `pgcrypto`.

#### Fail-Closed Test Target Guard (Proposed for `tests/config.py`)
To prevent accidental connection to cloud or production databases during automated testing, the following fail-closed preflight must be incorporated into test runners:
```python
# Proposed fail-closed test target assertion
_parsed_host = urlparse(DATABASE_URL).hostname or ""
if _parsed_host not in ("127.0.0.1", "localhost") or "supabase.co" in _parsed_host:
    raise SystemExit(
        f"CRITICAL SAFETY VIOLATION: Automated tests are prohibited from connecting to "
        f"non-loopback or cloud targets ({_parsed_host}). Use a local disposable stack."
    )
```

---

### 2.7 Privacy & Retention Policy Corrections (D-12)

#### Technical & Legal Clarification
Step 6 stated that retaining notification logs beyond 30 days "violates FERPA/GDPR data minimization principles." This is an unsupported legal assertion:
1. **FERPA (34 CFR Part 99):** Does not specify any 30-day retention or deletion window. Institutional educational records are subject to state record schedules and institutional policy, which frequently mandate multi-year preservation.
2. **GDPR (Article 5(1)(e)):** Mandates "storage limitation" (data must be kept in a form which permits identification for no longer than is necessary for the purposes for which it is processed). It does not mandate a universal 30-day rule.

#### Corrected Formulation
The proposed 30-day retention limit for notification logs and the redaction of message bodies/tokens must be described as a **proposed institutional data-governance policy** intended to enforce privacy-by-design and limit incident blast radius, subject to institutional legal review, rather than a universal statutory requirement.

---

## 3. Corrections Applied to Step 6.1 Findings

```
+----------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
| Item / Topic                           | Step 6.1 Statement                                    | Corrected Step 6.2 Formulation                        |
+----------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
| Auth Function Diagnostic (D-22)        | Asserted migration 021/022 were "unapplied".          | FUNCTION RESOLUTION FAILURE — DATABASE CATALOG STATE  |
|                                        |                                                       | UNVERIFIED (Catalog inspection is prohibited).        |
|                                        |                                                       |                                                       |
| Visitor Token Security (D-19)          | Labeled as "High Severity Security Bypass".           | Defense-in-depth missing cryptographic binding;       |
|                                        |                                                       | complete RLS & API conditions prevent direct bypass.  |
|                                        |                                                       |                                                       |
| SECURITY DEFINER Ownership (D-05)      | Assumed functions owned by migration runner superuser.| Proowner is unspecified in 021 DDL and unverified in  |
|                                        |                                                       | live catalog. Definer role hierarchy is proposed.     |
|                                        |                                                       |                                                       |
| Statutory Privacy Mandates (D-12)      | Claimed 30-day limit is mandated by FERPA/GDPR.       | Clarified as proposed institutional data governance   |
|                                        |                                                       | policy; FERPA/GDPR do not mandate 30 days.            |
+----------------------------------------+-------------------------------------------------------+-------------------------------------------------------+
```

---

## 4. D-01 through D-22 Consolidated Impact Summary

| Decision ID | Focus Area | Step 6.2 Consolidated Finding | Gate A Impact |
|:---|:---|:---|:---:|
| **D-01** | Migration History | Retain Branch B default; do not assume migration state without ledger. | Blocks Gate A |
| **D-02** | Worker Architecture | Separate mandatory DB claims/roles from infrastructure worker models. | Blocks Gate A |
| **D-03** | Worker Authentication | Require `claim_job()` with verified lease hashes. | Blocks Gate A |
| **D-04** | Job Lease & Recovery | 5-min lease, 60s heartbeat, 3 retries, idempotent DB effects. | Blocks Gate A |
| **D-05** | SECURITY DEFINER | Set `search_path = pg_catalog`; assign dedicated NOLOGIN owners. | Blocks Gate A |
| **D-06** | Identity Consumers | Remove `session_user` dependencies; rely strictly on Signed Context. | Blocks Gate A |
| **D-07** | Direct-Login Testing | Controlled `SET ROLE` harness; direct login only if session_user used. | Blocks Gate A |
| **D-08** | PG 17 Role Closure | Recursive cycle-safe membership query verifying zero escalation paths. | Blocks Gate A |
| **D-09** | Negative Principal | Dedicated `negative_test_user` to differentiate ACL vs RLS denials. | Blocks Gate A |
| **D-10** | Key Rotation | Drop partial unique index; adopt ACTIVE/PREVIOUS dual-key schema. | Blocks Gate A |
| **D-11** | Password Reset | Formally defer self-service reset until provider is contracted. | Blocks Gate A |
| **D-12** | Notification Retention | Adopt institutional 30-day purge policy; scrub bodies/tokens. | Resolved Rationale |
| **D-13** | College Registration | Public creates pending registrations; Super Admin approves/activates. | Blocks Gate A |
| **D-14** | Staff RBAC Matrix | VIEWER is strict read-only; EDITOR cannot publish live knowledge. | Blocks Gate A |
| **D-15** | Telemetry Redaction | Strict allowlist schema; prohibit raw prompts, errors, and PII. | Blocks Gate A |
| **D-16** | Test Environment | Require local loopback Supabase stack; fail closed on cloud DBs. | Blocks Gate B/C |
| **D-17** | Staged Authorization | Strict 3-gate model (Gate A $\to$ Gate B $\to$ Gate C). | Blocks Gate A |
| **D-18** | Identity Boundary | Custom HMAC signed context; deprecate `auth.uid()` in application. | Blocks Gate A |
| **D-19** | Visitor Token Security | Bind visitor token hash into HMAC context payload (`v2|visitor|...`). | Blocks Gate A |
| **D-20** | Guest Support Tickets | Strictly create-only; zero anonymous read/update/reply permissions. | Blocks Gate A |
| **D-21** | Chat Analytics | Aggregate-only metrics for college admins; raw logs support-only. | Blocks Gate A |
| **D-22** | Auth Lookup Contract | 7-column table projection; explicit `:email::text` casting. | Blocks Gate A |

---

## 5. Remaining Approvals Required

### 5.1 Project-Owner Decisions Pending
1. **D-01:** Formal adoption of Branch B (forward-only corrective migration) vs. Branch A.
2. **D-02:** Selection of Worker Infrastructure: Dedicated per-tenant workers vs. Shared worker pool with mandatory database-level job claims and subprocess isolation.
3. **D-11:** Decision to formally disable self-service password reset until a verified email provider is contracted.
4. **D-13:** Sign-off on registration workflow (public submissions create `PENDING` records only).
5. **D-14:** Approval of College Admin RBAC matrix (VIEWER read-only; EDITOR draft-only).
6. **D-21:** Approval of chat analytics privacy policy (aggregate metrics only for tenant admins).

### 5.2 Technical Specialist Approvals Pending
1. **PostgreSQL Security Architect (D-05, D-08, D-10):** Approval of definer role hierarchy, recursive role allowlist query, and dual-key rotation schema.
2. **Application Security Architect (D-03, D-06, D-18, D-19, D-22):** Sign-off on signed context `v2` payload, worker claim tokens, and 7-field authentication lookup contract.
3. **DevOps & Platform Engineer (D-16):** Approval of the local disposable Supabase CLI test environment manifest and fail-closed test target assertions.
4. **Data Privacy Officer (D-12, D-15, D-21):** Approval of the 30-day notification retention schedule and telemetry allowlist filter.

---

## 6. Gate Status Evaluation

```
+--------------------------------------------------------------------------------------------------+
| GATE A: DESIGN APPROVAL                                                                          |
| Status: NOT COMPLETE                                                                             |
| Rationale: All 22 decisions (D-01 through D-22) have consolidated technical findings and         |
|            remediated specifications, but remain pending formal human owner and specialist sign-off|
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| GATE B: IMPLEMENTATION AUTHORIZATION                                                             |
| Status: NOT AUTHORIZED                                                                           |
| Rationale: Implementation is prohibited until Gate A is formally completed and signed.           |
+--------------------------------------------------------------------------------------------------+
                                                |
                                                v
+--------------------------------------------------------------------------------------------------+
| GATE C: DATABASE VALIDATION & PRODUCTION RELEASE                                                 |
| Status: NOT VALIDATED — PRODUCTION NOT APPROVED                                                  |
| Rationale: No migrations or RLS tests have been executed on an authorized local Supabase stack.  |
+--------------------------------------------------------------------------------------------------+
```

---

## 7. Recommended Next Action

1. **Present Consolidated Package to Decision Owners:** Present this Step 6.2 report and the Step 6 decision register to the Project Owner and designated Technical Specialists.
2. **Formally Record Selections:** Capture formal sign-off for D-01 through D-22 in the Step 6 register.
3. **Mark Gate A COMPLETE:** Once sign-offs are archived, record Gate A as Complete.
4. **Prepare Gate B Request:** Formulate the isolated implementation plan (Step 7) on a dedicated local Supabase test container, incorporating the fail-closed cloud database connection block.
