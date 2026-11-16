# Phase 3A.4.4B — Step 5: Human Review and Decision Approval Package

## 1. Executive decision: READY FOR HUMAN DECISION

This package organizes the open design decisions and evidence needed before implementation can be considered. It does not resolve decisions on behalf of their owners, authorize implementation, validate a database, or approve a production release.

The inspected material supports a decision review, but migration history remains unknown for every environment outside the one disposable database described in Step 2. The recommended migration default is Branch B unless an accountable owner supplies written evidence that migrations 001–022 have never been applied, partially applied, released, or deployed anywhere. No human decisions or approvals are recorded here as completed.

Step 3 and Step 3.1 use a readiness label for human implementation-approval review, while explicitly stating that they do not authorize implementation. Step 4 is more restrictive and remains **READY FOR HUMAN REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION — NOT DATABASE VALIDATED**. These reports are proposals and review artifacts, not implementation authorization or database-validation evidence.

## 2. Documents and repository evidence inspected

### Requested reports

1. [Step 4 controlled implementation plan](./phase3a4.4b-step4-controlled-implementation-plan.md) — reviewed across its full report, including migration decision tree, worker/function designs, human decisions, test matrix, rollback, gates, and limitations.
2. [Step 4 correction summary](./phase3a4.4b-step4-correction-summary.md).
3. [Step 3 final approval package](./phase3a4.4b-step3-final-approval-package.md).
4. [Step 3.1 security gap closure](./phase3a4.4b-step3.1-security-gap-closure.md).
5. [Step 2 migration-validation report](./phase3a4.4b-step2-migration-validation-report.md).

### Related repository material

- [database/README.md](../../database/README.md).
- [CI workflow](../../.github/workflows/ci.yml) and [CD workflow](../../.github/workflows/cd.yml).
- Migration source read for this review: [017_row_level_security_policies.sql](../../database/migrations/017_row_level_security_policies.sql), [018_create_application_role.sql](../../database/migrations/018_create_application_role.sql), [019_complete_rls_policies.sql](../../database/migrations/019_complete_rls_policies.sql), [020_revoke_anon_grants.sql](../../database/migrations/020_revoke_anon_grants.sql), [021_phase3a42_security_onboarding.sql](../../database/migrations/021_phase3a42_security_onboarding.sql), and [022_minimize_auth_lookup.sql](../../database/migrations/022_minimize_auth_lookup.sql).
- The repository migration-file listing showed numbered files 001–022. Their presence is not evidence that they ran. The Step 2 report says it reviewed the full chain; this Step 5 review did not reread SQL source for 001–016.

### Agreement and discrepancies

- The reports consistently distinguish recommendations from executed validation, and Step 4 explicitly does not authorize implementation or claim database validation.
- Step 2 documents that migration execution stopped before 001 on its preserved vanilla PostgreSQL test target; it describes only limited target/catalog checks there. That statement applies to that target and time only. It does not establish migration history for staging, production, shared, or other databases.
- The Step 4/Step 4 summary say no authoritative per-environment migration ledger was found in the prior repository review. The README contains manual hosted-Supabase SQL instructions, not an execution ledger.
- The CI workflow sets the backend test database to in-memory SQLite; this cannot establish PostgreSQL RLS behavior. The CD workflow publishes images and includes a deployment job, but the inspected deployment commands are placeholders/comments and no migration-application step is shown. Neither workflow proves whether migrations were applied by another mechanism.
- The migration source confirms important design-review facts: 017 contains `auth.uid()` policy references; 018 defines a LOGIN application role with a placeholder password and broad grants; 019 contains broad policies; 020 assumes Supabase roles; 021 has its own transaction and destructive token/hash-column changes; and 022 has its own transaction. These are static source facts, not runtime or deployment facts.
- Step 3 and Step 3.1 recommendations are retained in Step 4, but their earlier readiness labels do not establish that the human decisions they list were accepted. Step 4 still identifies them as pending.
- No inconsistency was found that resolves migration history, role state, function ownership, worker identity, or any of the approval decisions below.

## 3. Evidence classifications

Use these labels when interpreting the register:

- **Confirmed by inspected source:** Directly visible in repository files read for this review. This confirms file contents only, not runtime behavior.
- **Confirmed by existing documentation:** Stated in a prior report or plan. It is not independently re-executed or proved by this review.
- **Proposed but not executed:** Design, catalog inspection, test, or operational step described in the plans but not carried out.
- **Requires human confirmation:** Needs an accountable owner's decision, records, or approval.
- **Unknown or unavailable:** Cannot be established from the inspected repository material.

Where a prior report describes application-source findings not independently opened in this Step 5 review, those findings are attributed to that report rather than presented as freshly verified source facts.

## 4. Human decision register

Every item below is **PENDING**. No named accountable owner or completed approval record was identified in the inspected documents. Role descriptions identify who should decide; the organization must name the actual person.

### D-01 — Migration history and Branch A versus Branch B

- **Decision required:** Establish migration 001–022 status separately for every relevant environment and select the migration branch.
- **Options:** Branch A only with written confirmation of never applied/released/deployed anywhere; Branch B for any applied, partial, released, or uncertain history.
- **Consequences:** Rewriting an already-used migration can diverge environments and obscure data changes. Branch B preserves history but requires a schema inventory and forward-only correction.
- **Recommendation:** Default to Branch B unless the accountable owner positively documents the complete Branch A condition. Do not query production as part of this package.
- **Required owner:** Accountable database/release owner; name not identified.
- **Evidence needed:** Environment-by-environment migration ledger or equivalent deployment records, release history, and written owner attestation covering partial attempts and all shared/staging/production environments. If Branch B applies, an approved non-production schema/version inventory is required before naming the next migration.
- **Evidence now:** Step 2 documents no migrations ran in its preserved vanilla test database; Step 4 says no authoritative per-environment ledger was found. Repository file presence and manual README instructions do not establish application history. **Unknown** for other environments.
- **Approval status:** PENDING.

### D-02 — Shared versus tenant-isolated workers

- **Decision required:** Choose one shared worker/pool, tenant-isolated workers, or explicitly bounded trust cohorts.
- **Options and consequences:** A shared pool is operationally simpler but a compromised worker can affect every tenant in its scope. Per-tenant pools reduce the blast radius but add deployment, queue, and secret-management complexity. Cohorts are a compromise and still expose every tenant in the cohort.
- **Recommendation:** Tenant-isolated workers, or small explicitly approved trust cohorts if per-tenant operation is infeasible. Record residual risk and compensating controls if a shared worker is selected.
- **Required owner:** Security architecture owner and worker/platform operations owner; names not identified.
- **Evidence needed:** Approved tenant/cohort boundaries, service deployment and queue ownership model, isolation/revocation procedures, and written acceptance of residual compromise impact.
- **Evidence now:** Step 3.1/Step 4 document shared application-engine/task paths and recommend isolation; that design has not been implemented or operationally validated. **Confirmed by existing documentation; proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-03 — Worker authentication and claim authorization

- **Decision required:** Define how the database authenticates the worker pool and authorizes job claims.
- **Options:** PostgreSQL-authenticated per-pool connection principal mapped to a NOLOGIN capability role; or an external signed identity that the database independently verifies. Any alternative needs the same verified pool binding and reviewed function boundary.
- **Consequences:** A job UUID, caller-supplied tenant/resource, worker name, or unsigned GUC is not proof of authorization. An overbroad claim function or shared credential increases cross-tenant exposure.
- **Recommendation:** Use a distinct authenticated principal per tenant or approved cohort, map it to a narrowly scoped NOLOGIN capability role, and have a reviewed claim function validate database-derived job/resource bindings. If using external identity, verify issuer, audience, key ID, signature, expiry, and pool binding in the database.
- **Required owner:** Database security owner and worker-service identity owner; names not identified.
- **Evidence needed:** Chosen identity/credential mechanism; exact claimant and capability roles; function owner, EXECUTE grants, internal table rights, pool mapping, and threat model; approval of secret provisioning separate from migrations.
- **Evidence now:** Step 4 describes these alternatives and recommends a database-authenticated pool mapping; no separate worker principal, claim function, or credential boundary is documented as deployed. **Proposed but not executed; requires human confirmation; implementation state unknown.**
- **Approval status:** PENDING.

### D-04 — Lease, retry, duplicate delivery, and crash recovery

- **Decision required:** Approve lease duration, heartbeat, task limit, attempt limits, retry/dead-letter behavior, and idempotency semantics.
- **Options:** Approve Step 4's proposed five-minute lease, 60-second heartbeat, one-hour task limit, database-clock expiry, at-least-once delivery with idempotent effects; or specify reviewed alternatives.
- **Consequences:** Weak expiry/retry rules allow stale workers or duplicate delivery to repeat effects. A short lease can increase retries and operational load. “Exactly once” cannot be assumed for external side effects.
- **Recommendation:** Treat queue delivery as at-least-once; use database-enforced lease/attempt state, one-time lease capability hashes, per-effect idempotency, bounded retries, and terminal/dead-letter state. Approve numerical defaults only after workload owners review them.
- **Required owner:** Worker product/operations owner with database security owner; names not identified.
- **Evidence needed:** Final numerical limits and retry policy, external-side-effect idempotency plan, crash/reclaim behavior, and later synthetic tests for expiry, duplicate completion, stale tokens, retry, and recovery.
- **Evidence now:** The limits and lifecycle are design proposals in Step 3.1/Step 4. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-05 — SECURITY DEFINER ownership, grants, search_path, and RLS

- **Decision required:** Approve the owner and privilege contract for every existing and proposed SECURITY DEFINER function.
- **Options:** Distinct least-privilege NOLOGIN owners by function group, or fewer reviewed owner groups with equivalent least privilege. Any BYPASSRLS design requires separate justification and approval.
- **Consequences:** Owner/table rights, PUBLIC or inherited EXECUTE, mutable search paths, nested definer calls, or owner membership can defeat intended RLS. A stored NULL `proacl` does not prove PUBLIC was revoked.
- **Recommendation:** Explicit non-login, non-owner, non-superuser, non-BYPASSRLS owners; fixed `pg_catalog` search path with schema-qualified objects; explicit PUBLIC revoke and per-function EXECUTE allowlists; effective ACL/default-ACL and transitive-membership checks; review nested calls and actual RLS behavior.
- **Required owner:** Database security architect and accountable database owner; names not identified.
- **Evidence needed:** Per-function inventory and owner/grant matrix; schema/table/column rights; default ACLs; effective privileges including memberships; function definitions and nested/dynamic call review; test evidence that owners cannot access unrelated tenant data.
- **Evidence now:** Step 3.1/Step 4 contain proposals and proposed catalog queries, explicitly unexecuted. Migration source shows current functions and grants, but no live catalog evidence exists in this review. **Confirmed by inspected source** for file contents; **proposed but not executed** for the target design.
- **Approval status:** PENDING.

### D-06 — `session_user`, `current_user`, `current_role`, and other identity dependencies

- **Decision required:** Identify every production authorization path that consumes connection identity, effective SQL role, role membership, signed application identity, or external identity.
- **Options:** Remove unnecessary dependence on session identity; retain a documented `session_user` trust anchor and validate it with a matching direct-login test; or adopt another explicitly reviewed identity contract.
- **Consequences:** `SET ROLE` changes `current_user`/`current_role` but leaves `session_user` as the harness login. SECURITY DEFINER execution changes `current_user` to the function owner. Treating these values as interchangeable can invalidate tests or create a confused-deputy boundary.
- **Recommendation:** Produce an identity-consumer map for each policy, function, connection path, and worker path. Do not count SET ROLE as evidence for any `session_user`-dependent behavior.
- **Required owner:** Application security owner and database security owner; names not identified.
- **Evidence needed:** Reviewed source/definitions for every identity consumer, connection/pool configuration, expected identity tuple by request type, and approved identity contract.
- **Evidence now:** Step 4 explicitly says the production identity dependencies are not established. **Requires human confirmation; unknown or unavailable** until the source/catalog inventory is completed.
- **Approval status:** PENDING.

### D-07 — Direct-login testing requirement

- **Decision required:** Decide whether any security path needs a disposable direct-login test in addition to the SET ROLE capability tests.
- **Options:** No direct-login test only if the approved identity audit establishes no production authorization depends on direct-login `session_user`; otherwise complete a separately approved disposable direct-login test with a matching test principal.
- **Consequences:** SET ROLE validates effective capability-role privileges and role-targeted RLS, not direct-login session identity or authentication behavior.
- **Recommendation:** If any production path uses `session_user`, keep that path **UNVALIDATED** until a separately approved direct-login test is completed. Keep production runtime roles NOLOGIN; do not enable LOGIN on them for testing.
- **Required owner:** Database security owner and accountable test-environment owner; names not identified.
- **Evidence needed:** D-06 identity-consumer map, explicit test-principal design, isolated environment approval, and test results. A copied-grant role alone is not evidence of equivalent identity.
- **Evidence now:** Step 4 requires the distinction and says the direct-login test is not completed. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-08 — PostgreSQL 17 membership closure and protected-role allowlist

- **Decision required:** Approve the complete protected-role/object-owner inventory and the membership paths permitted for each required principal.
- **Options:** Approve a fail-closed allowlist and no unreviewed route to privileged roles; any exception must identify principal, path, purpose, and risk.
- **Consequences:** Direct-membership-only review misses transitive SET, inherited, or ADMIN OPTION paths. Privileged paths may reach superuser, BYPASSRLS, table/migration/function owners, or other sensitive objects.
- **Recommendation:** Include exact runtime, worker, harness, negative-test, migration, and SECURITY DEFINER roles; recursively inspect every path using PostgreSQL 17 `set_option`, `inherit_option`, and `admin_option`; treat missing principals or unexamined paths as blocked.
- **Required owner:** Accountable PostgreSQL administrator and security reviewer; names not identified.
- **Evidence needed:** Approved protected-role and object-owner inventory, exact principal roster, complete recursive path output, effective `pg_has_role`/`has_*_privilege` results, and documented review of each privileged path.
- **Evidence now:** Step 4 supplies a proposed query and fail-closed assertions, not execution results. No role catalog was queried for this Step 5 review. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-09 — Independent unprivileged negative-test principal

- **Decision required:** Approve a disposable negative-test login and its minimal fixture privileges.
- **Options:** Use the distinct principal described in Step 4, with only narrowly scoped synthetic fixture-table privileges needed to distinguish ACL denials from RLS denials; or revise the harness while preserving an independently unprivileged boundary test.
- **Consequences:** Testing only as Supabase `anon` does not show that an arbitrary unprivileged login lacks memberships, ownership, schema CREATE, protected EXECUTE, or escalation paths. Missing table grants alone do not prove RLS works.
- **Recommendation:** Use a separate non-superuser, NOBYPASSRLS, non-owner principal with no direct/transitive application, worker, migration, or definer-owner membership, no unintended schema CREATE, and no protected EXECUTE. Use only synthetic fixtures in the approved disposable environment.
- **Required owner:** Security test owner and database administrator; names not identified.
- **Evidence needed:** Principal attributes, complete membership/ownership/effective-privilege inventory, fixture grant rationale, and negative tests for function invocation, identity changes, cross-tenant reads/writes, RLS bypass, worker claim, and maintenance operations.
- **Evidence now:** Step 4 specifies this design and its tests; no role or test was created or run. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-10 — Signing-key storage, rotation, and access

- **Decision required:** Choose the approved key store, key owner/operator, access model, and rotation/revocation procedure for each context purpose.
- **Options:** A separately managed protected secret store with narrowly scoped service access, or another approved mechanism that keeps keys unavailable to general web/worker principals and SQL callers.
- **Consequences:** Shared, over-scoped, or long-lived keys allow forged contexts and enlarge compromise scope. Rotation without a bounded verification overlap can either break requests or preserve old keys too long.
- **Recommendation:** Separate purpose/key IDs for USER/VISITOR/WORKER contexts; keep secrets out of migrations, source, logs, and reports; approve a named rotation operator and bounded old-key verification overlap consistent with the proposed maximum context lifetime. Do not reuse the JWT key.
- **Required owner:** Security/key-management owner and application operations owner; names not identified.
- **Evidence needed:** Chosen key store and access policy, issuance/rotation/revocation runbook, purpose binding, audit trail, and later synthetic rotation/replay tests. No key value is requested.
- **Evidence now:** Step 3.1/Step 4 describe a proposal; no key was provisioned or inspected. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-11 — Password-reset email delivery

- **Decision required:** Approve an email-delivery provider/owner and end-to-end reset flow, or explicitly defer password reset until delivery is available.
- **Options:** Integrate an approved provider; defer/reset-disable the flow; or choose another explicitly approved channel.
- **Consequences:** Returning reset tokens through public responses or storing plaintext risks account takeover. An issued token that is discarded cannot complete the user journey.
- **Recommendation:** Keep generic public responses and purpose-bound, expiring, hashed one-time tokens; do not expose tokens in API responses or logs. Do not claim reset delivery works until an approved channel is implemented and tested.
- **Required owner:** Product/account-recovery owner and security/privacy owner; names not identified.
- **Evidence needed:** Provider and delivery ownership decision, message/content policy, token purpose/expiry/consumption requirements, and later end-to-end delivery and negative tests.
- **Evidence now:** Step 3.1/Step 4 report that the forgot-password route discards a service-returned token and that delivery is unresolved. This review did not inspect the route implementation. **Confirmed by existing documentation; requires human confirmation; runtime behavior not independently validated.**
- **Approval status:** PENDING.

### D-12 — Notification recipient data and retention

- **Decision required:** Decide whether notification logs retain recipient email or a keyed/irreversible reference, and define retention/deletion duration.
- **Options:** Retain the address for a bounded approved period; store a minimized reference; or omit it.
- **Consequences:** Email and message metadata are personal data and can link accounts/events. Retention may aid delivery support but increases exposure and deletion obligations.
- **Recommendation:** Minimize and redact; retain direct recipient data only if operationally necessary, with an explicit bounded period and deletion process. Exclude email bodies, prompts, invitation URLs/tokens, free-form reasons, and raw provider errors.
- **Required owner:** Privacy/data-retention owner with notification operations owner; names not identified.
- **Evidence needed:** Purpose, data-field inventory, retention schedule, deletion mechanism, access list, and audit/redaction review.
- **Evidence now:** Step 3.1 documents current log-content concerns and proposes constrained recording; no retention decision is recorded. **Confirmed by existing documentation; proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-13 — Public college registration versus Super Admin-only creation

- **Decision required:** Decide whether public applicants may submit a pending registration or only Super Admins may create colleges directly.
- **Options:** Public route creates only a pending/inactive registration; direct creation is Super Admin-only; or an alternative with equivalent approval enforcement.
- **Consequences:** Unrestricted tenant inserts or caller-supplied college IDs can create unauthorized tenants or bypass approval. Restricting creation changes onboarding behavior.
- **Recommendation:** Public registration creates pending/inactive state only; activation and legal state transitions are Super Admin-controlled. Direct tenant insertion is not an ordinary authenticated-user capability.
- **Required owner:** Product/onboarding owner and security owner; names not identified.
- **Evidence needed:** Product decision, state-transition rules, approved registration lifecycle, and tests for unauthorized create/approve/activate/update.
- **Evidence now:** Step 3/3.1/Step 4 identify the direct-create path as unresolved and recommend the pending-registration boundary. **Confirmed by existing documentation; requires human confirmation.**
- **Approval status:** PENDING.

### D-14 — EDITOR and VIEWER permission boundaries

- **Decision required:** Define whether EDITOR and VIEWER have distinct API/database capabilities and which operations each may perform.
- **Options:** Approve an explicit capability matrix, or defer additional permissions and deny writes until product requirements are specified.
- **Consequences:** Role labels without enforced boundaries can cause unintended privilege elevation or inconsistent UI/API behavior.
- **Recommendation:** Default to no additional write capability for EDITOR/VIEWER until a product-approved matrix is mapped to API checks and database grants/policies.
- **Required owner:** Product owner and application security owner; names not identified.
- **Evidence needed:** Role definitions, allowed operations/data, migration compatibility for current members, and positive/negative tests for each role.
- **Evidence now:** Step 4 says the complete capability matrix is not established. **Confirmed by existing documentation; requires human confirmation.**
- **Approval status:** PENDING.

### D-15 — Audit payload and AI telemetry restrictions

- **Decision required:** Approve event/payload allowlists, metric bounds, actor derivation, retention, and redaction rules for audit and AI telemetry.
- **Options:** Adopt the Step 3.1 constrained recorder proposal or approve a revised bounded schema with equivalent protection.
- **Consequences:** Caller-selected actors or targets can forge audit history; prompts, provider responses, exception strings, or secrets in telemetry create disclosure risk; unrestricted metrics can distort operations.
- **Recommendation:** Derive actors/targets from verified context and database rows; allow only fixed event categories and bounded numeric fields; exclude prompts, credentials, raw provider errors, arbitrary JSON, and unapproved personal data. Keep writes behind narrowly scoped functions.
- **Required owner:** Security/audit owner, AI operations owner, and privacy owner; names not identified.
- **Evidence needed:** Approved event and key allowlists, numeric bounds, retention, read access, redaction rules, and later tests proving rejected fields are not persisted.
- **Evidence now:** Step 3.1 records current call-site risks and proposes constraints; no schema/function/test is implemented or validated. **Confirmed by existing documentation; proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-16 — Disposable Supabase-compatible test environment

- **Decision required:** Approve a new isolated local Supabase-compatible environment for later implementation and validation.
- **Options:** A separately provisioned disposable local Supabase stack; or another specifically approved environment that provides the required PostgreSQL/Supabase Auth behavior without touching existing data.
- **Consequences:** Vanilla PostgreSQL lacks the Supabase `auth`, `anon`, and `authenticated` dependencies described in the reports. A hand-built shim cannot be described as Supabase validation. Reusing the preserved container or volume risks contaminating prior state.
- **Recommendation:** Use a new, isolated local Supabase-compatible stack with synthetic data, loopback-only exposure, dedicated storage/network, verified versions and no hosted-project linkage. Keep the existing PostgreSQL test container/volume untouched.
- **Required owner:** Platform/database operations owner and security test owner; names not identified.
- **Evidence needed:** Written environment approval, version/extension/Auth-role inventory, network/volume isolation evidence, credential separation, synthetic-data plan, cleanup/recovery owner.
- **Evidence now:** Step 2 documents a prior vanilla PostgreSQL target and absence of Supabase Auth/roles there; Step 4 says no new Supabase stack was provisioned or verified. **Confirmed by existing documentation; proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-17 — Implementation authorization and later production approval

- **Decision required:** Identify the accountable authorizer and decide whether/when to authorize a precisely scoped implementation; separately decide later database validation and production release.
- **Options:** Defer; authorize only an approved isolated implementation scope after Gate A; or approve a later production release only after independent evidence and a distinct release decision.
- **Consequences:** Design approval alone does not authorize code changes, credentials, database work, or deployment. Implementation authorization does not validate the database or approve production.
- **Recommendation:** No implementation or production authorization is granted by this package. Require written Gate B authorization naming files, environments, prohibited actions, rollback, and responsible operators. Require separate Gate C database/security evidence and explicit production release approval.
- **Required owner:** Accountable project/business owner and release owner; names not identified.
- **Evidence needed:** Signed authorization, exact approved scope, approved isolated environment, rollback and incident plan; later, security test results, independent review, and explicit production approval.
- **Evidence now:** Step 3/3.1/Step 4 state that earlier planning does not itself authorize work; no Step 5 authorization exists. **Requires human confirmation.**
- **Approval status:** PENDING.

### D-18 — Application identity model and Supabase Auth boundary

- **Decision required:** Confirm the application identity source and explicitly define how it relates to Supabase `auth.uid()`.
- **Options:** Retain custom JWT plus database-verified signed application context as described in prior reports; or separately redesign and approve an identity integration. Do not mix the contracts implicitly.
- **Consequences:** Treating Supabase `auth.uid()` as the custom application's identity when it is not established can make policy checks fail or authorize the wrong principal.
- **Recommendation:** Preserve the custom signed application identity proposal unless a separately reviewed identity redesign is approved; do not rely on `auth.uid()` as application identity merely because the test stack contains Supabase Auth.
- **Required owner:** Application identity owner and security architect; names not identified.
- **Evidence needed:** Approved identity/issuer contract, claim-to-database mapping, token validation boundary, and source/function/policy review.
- **Evidence now:** Step 3/Step 4 document custom JWT and signed context; migration 017 source contains `auth.uid()` references. This is static code/document evidence, not proof of deployed behavior. **Confirmed by inspected source and existing documentation; requires human confirmation.**
- **Approval status:** PENDING.

### D-19 — Visitor-token lifetime and anonymous feedback

- **Decision required:** Approve the visitor capability contract, including absolute expiry and whether feedback requires the matching session token.
- **Options:** Adopt the proposed 24-hour absolute non-sliding expiry and matching-token feedback; or specify a revised bounded capability with equivalent cross-session protection.
- **Consequences:** Extending expiry, accepting tenant-only feedback, or treating raw GUCs as proof can permit replay or cross-session access.
- **Recommendation:** Retain a random one-time bearer token, store only its hash, bind its digest into a signed VISITOR context, require the matching token for the same session, and deny at/after the fixed 24-hour expiry.
- **Required owner:** Product owner for anonymous UX and security owner; names not identified.
- **Evidence needed:** Written acceptance of lifetime and feedback behavior, token lifecycle and response/logging contract, and later synthetic matching/mismatch/expiry/replay tests.
- **Evidence now:** Step 3/3.1/Step 4 carry this as a proposal; no execution evidence exists. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-20 — Guest support tickets

- **Decision required:** Confirm whether guest support remains create-only, with no anonymous ticket listing, reading, update, reply, or separate bearer capability.
- **Options:** Keep create-only as proposed; or approve a separately threat-modeled, narrow follow-up capability.
- **Consequences:** Anonymous read/update capabilities can expose internal notes or allow ticket takeover if not strongly bound and expired.
- **Recommendation:** Keep guest tickets create-only; do not add anonymous read/update/reply capability in this scope.
- **Required owner:** Product/support owner and security owner; names not identified.
- **Evidence needed:** Written product acceptance, exact create-only API contract, and later tests for denied guest list/detail/update/reply.
- **Evidence now:** Step 3 and Step 4 retain create-only as a proposal; no test execution is claimed. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-21 — College chat analytics and raw conversation access

- **Decision required:** Decide whether college administrators receive only approved aggregates or may access any raw conversation content.
- **Options:** Aggregate-only college analytics; or a separately justified, narrowly scoped raw-content workflow with privacy controls.
- **Consequences:** Raw prompts/messages can contain sensitive student information. Aggregate functions must still prevent cross-tenant access and inference beyond approved metrics.
- **Recommendation:** Aggregate-only college analytics; keep raw content owner-scoped except for separately authorized workflows.
- **Required owner:** Product/data owner, privacy owner, and security owner; names not identified.
- **Evidence needed:** Approved metric list, minimum aggregation/privacy constraints, retention and access rules, and later tests showing tenant admins cannot read raw or other-tenant content.
- **Evidence now:** Step 3/3.1/Step 4 recommend aggregate-only access; implementation and database behavior remain unverified. **Proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

### D-22 — Sensitive user-column access and authentication lookup contract

- **Decision required:** Approve the user-column privilege boundary and the exact authentication lookup result required by the backend.
- **Options:** Adopt Step 3.1's column allowlist and seven-field auth lookup function; or approve a revised minimal projection/function contract.
- **Consequences:** Broad ORM entity reads can fetch password/token fields; revoking table privileges without updating projections can break callers. The password hash is necessarily handled by the trusted backend for local verification and must not enter API output/logs.
- **Recommendation:** Keep the auth lookup to the documented seven fields; deny direct runtime reads of stored password/token hashes; use explicit safe projections and narrowly authorized credential functions for writes.
- **Required owner:** Authentication/application owner and database security owner; names not identified.
- **Evidence needed:** Approved column/function allowlist, complete caller inventory, response/logging contract, and later positive/negative tests including the exact result shape.
- **Evidence now:** Step 3.1 documents these source findings and proposes the contract; this Step 5 review did not independently inspect those application call sites, and no database privilege behavior was tested. **Confirmed by existing documentation; proposed but not executed; requires human confirmation.**
- **Approval status:** PENDING.

## 5. Recommended decisions and rationale

The recommendations in D-01 through D-22 are the least-privilege positions already developed in Steps 3, 3.1, and 4, not new implementation instructions. The principal sequencing recommendation is:

1. Obtain written per-environment migration-history evidence before selecting a branch. If history remains uncertain, use Branch B.
2. Resolve and record all design choices, name accountable owners, and accept residual risks at Gate A.
3. Authorize only a bounded isolated implementation at Gate B, with production roles remaining NOLOGIN and the existing database container/volume untouched.
4. Treat database validation and production release as separate later outcomes requiring Gate C evidence and explicit approval.

No recommendation in this section constitutes an approval or permission to act.

## 6. Migration Branch A/B decision requirements

### Branch A — only with positive written evidence

Branch A may be selected only if an accountable database/release owner confirms in writing that migrations 001–022 were never applied, partially applied, released, or deployed in **any** relevant environment. The statement must identify the environments covered and the evidence source. A statement about only the Step 2 test database is insufficient.

If that condition is established, the Step 4 plan's in-place correction approach may be considered for an explicitly approved unreleased chain. This package does not approve edits or execution.

### Branch B — applied, partial, released, or uncertain history

If any migration was applied/released, any attempt was partial, or history cannot be positively established, preserve historical migration files and use a forward-only corrective migration after an approved schema/version inventory. Do not assume migration 022 is the latest applied migration or select the proposed 023 filename before inventory.

No production connection or migration execution is authorized to collect this evidence. An accountable owner may provide existing deployment/change records; any later schema inventory must be separately authorized and non-production unless a distinct approval is obtained.

### Data-destructive boundary

The inspected migration 021 source contains its own `BEGIN`/`COMMIT`, hashes invitation tokens, drops the plaintext invitation token column, and drops `initial_admin_password_hash`. It has no valid post-execution/pre-internal-COMMIT pause. Step 4 requires preflight checks before it begins and fail-closed assertions inside its transaction before its own `COMMIT`. Those checks and recovery behavior remain proposed and unexecuted; no assumptions are made about whether 021 ran in any environment.

## 7. Missing evidence and unresolved questions

### Evidence absent from the inspected material

- A complete, authoritative migration status for each environment and evidence establishing whether any migration was applied, partially applied, released, or deployed.
- Named owners for the decisions, protected-role allowlist, migration-history attestation, environment operation, security review, and release approval.
- The approved worker architecture, authenticated pool identity, claim-function contract, lease/retry policy, and key custody.
- Actual deployed PostgreSQL role attributes, membership closure, object ownership, default ACLs, function ACLs, `search_path`, policies, and RLS behavior.
- The complete inventory of production paths that consume `session_user`, `current_user`, `current_role`, role membership, signed context, or connection identity.
- Approval and results for a direct-login test where required. SET ROLE alone is not such evidence.
- An approved and provisioned disposable Supabase-compatible environment, test principals, and synthetic fixtures.
- Product/privacy decisions for reset-email delivery, notification retention, registration, EDITOR/VIEWER permissions, audit/telemetry fields, visitor capabilities, guest support, and analytics.
- Any independent security review or explicit production release decision.

### Questions for the human decision owners

1. Which environments must the migration-history statement cover, and who can attest to their complete release/application records?
2. Who is accountable for each design decision and who can authorize the later isolated implementation?
3. Is tenant-per-worker feasible, or is a bounded trust cohort/shared pool being requested with accepted blast radius?
4. Does any production authorization path consume `session_user`? If so, which exact path and what approved disposable direct-login principal will represent it?
5. Which keys, role memberships, function owners, and provider/notification data may be accessed by each runtime component?
6. Which product and privacy decisions are accepted, and which are deferred?

### Evidence interpretation

No proposed catalog query, test matrix, migration assertion, worker flow, key rotation procedure, or rollback plan in the prior reports was executed for this Step 5 package. Step 2's historical preflight describes a specific vanilla PostgreSQL target and explicitly says the migration chain did not run there; it does not validate the proposed Supabase-compatible design or any other environment.

## 8. Implementation authorization requirements

Implementation must remain blocked until:

- Gate A is recorded as complete with each applicable D-01–D-22 decision answered, evidence attached or clearly marked unavailable, residual risks accepted, and decision owners named.
- Migration Branch A or B is chosen from the evidence rules above; Branch B applies by default to uncertain history.
- Gate B contains written authorization from the accountable owner that identifies exact files and scope, responsible implementers, approved isolated environment, prohibited production actions, credential boundaries, and rollback/recovery plan.
- Any later changes to roles, credentials, signing keys, migrations, tests, or database environments are explicitly within the approved scope.

Gate A is not implementation authorization. A readiness label in any earlier report is not a substitute for the written Gate B authorization.

## 9. Database validation and production release requirements

Gate C cannot be considered complete without, at minimum:

- Separately approved isolated Supabase-compatible test environment and synthetic-only data.
- Approved migration path and execution record, including Step 4's transaction-021 preflight/in-transaction assertions if that path applies.
- Complete principal/owner inventory and PostgreSQL 17 transitive membership/effective-privilege evidence; fail closed on missing principals or unexamined paths.
- Effective SECURITY DEFINER ACL/default-ACL, owner, PUBLIC/role grant, schema privilege, search-path, nested-call, and RLS verification.
- Positive and negative tenant-isolation tests using the approved runtime-role harness and independent unprivileged negative principal; distinguish ACL denial from an RLS assertion.
- A separately approved direct-login test for every production path relying on `session_user`; until then, each such path remains **UNVALIDATED**.
- Worker claim, lease, retry, duplicate-delivery, crash-recovery, and cross-tenant tests; independent security review; unresolved critical findings dispositioned.
- Written, separate production release approval after review of results, rollback readiness, monitoring, and credential/key operations.

Passing Gate C's isolated database validation requirements does not itself authorize production. Production approval must be explicit and recorded; no such evidence is present.

## 10. Approval checklist — three separate gates

### Gate A — Design approval

- [ ] All applicable D-01–D-22 decisions have a recorded answer, decision owner, evidence, and residual-risk disposition.
- [ ] Security architecture and worker trust boundary are accepted.
- [ ] Migration strategy is selected using per-environment evidence; uncertain history defaults to Branch B.
- [ ] Required implementation, database, security, privacy, operations, and release owners are identified.
- [ ] Prior Step 3/3.1 proposals retained in Step 4 are explicitly accepted, amended, or deferred.

**Gate A status: NOT COMPLETE — decisions and evidence remain pending.**

### Gate B — Implementation authorization

- [ ] Written authorization from the accountable owner.
- [ ] Exact approved implementation scope, files, operators, and environment.
- [ ] Approved isolated test environment and synthetic-data plan.
- [ ] Explicit restrictions, credential/key boundaries, rollback and recovery plan.
- [ ] Confirmation that Gate A completion alone is not being treated as this authorization.

**Gate B status: NOT AUTHORIZED.**

### Gate C — Database validation and production approval

- [ ] Isolated database validation completed with retained execution evidence.
- [ ] Security and tenant-isolation tests passed, including required direct-login and negative-principal cases.
- [ ] Independent security review completed and findings dispositioned.
- [ ] Rollback/recovery readiness and operational monitoring reviewed.
- [ ] Production release explicitly approved by the accountable release owner.

**Gate C status: NOT VALIDATED; PRODUCTION NOT APPROVED.**

Gates A, B, and C are independent approval boundaries. Completing Gate A does not authorize Gate B or Gate C. Completing Gate B does not establish database validation or production approval.

## 11. Explicit safety confirmation

This Step 5 work was limited to reading repository documentation and migration source and creating this requested decision-package document. No application code, SQL, migration, test, configuration, `.env`, credential, signing key, connection string, role, permission, policy, database, test data, Docker container, volume, hosted Supabase project, or deployment was changed. No shell command, test, migration, database command, or SQL statement was executed. No database was connected to, and no database validation or implementation authorization was performed.

The historical Step 2 report describes earlier read-only catalog queries against its isolated vanilla PostgreSQL test target. Those are reported historical actions, not actions performed for this Step 5 package and not validation of the proposed security design.

## Final status

**READY FOR HUMAN DECISION**
