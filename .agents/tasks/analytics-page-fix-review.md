# Super-Admin Analytics Page Crash Fix — Review

## Verdict: APPROVED (no blockers)

## Files reviewed
- `apps/admin-frontend/src/app/super-admin/analytics/page.tsx` (changed)
- `apps/admin-frontend/src/services/super-admin-service.ts` (changed)
- `apps/admin-frontend/src/app/super-admin/analytics/page.test.tsx` (new)
- `apps/admin-frontend/src/types/admin.ts` (unchanged `UsageAnalytics` type)
- `apps/admin-frontend/src/lib/api-client.ts` (unchanged `adminApiRequest` contract)
- `apps/admin-frontend/src/components/DashboardCard.tsx` (unchanged caller)
- Backend (read-only, to confirm field agreement / no changes):
  - `backend/app/schemas/super_admin.py` (`UsageAnalyticsResponse`)
  - `backend/app/schemas/support_and_analytics.py` (`AIUsageMetrics`, `PlatformAnalyticsResponse`)
  - `backend/app/api/v1/super_admin.py` (`GET /super-admin/analytics`)
  - `backend/app/api/v1/analytics.py` (`GET /analytics/platform`)
  - `backend/app/services/analytics_service.py`
- `.agents/tasks/analytics-page-fix-report.md`

Note: the workspace is not a git repository (no `.git` anywhere in the tree), so changes were inspected directly from the working tree, not from a diff. Modification timestamps confirm only the three frontend files were touched for this task (2026-11-15 09:57); all backend analytics files are older (2026-11-11 14:21).

## Root cause confirmed
The page reads a flat `UsageAnalytics` shape (`data.total_tokens`, `data.top_colleges`, etc.), but `superAdminService.getUsageAnalytics` preferred `GET /analytics/platform`, whose `PlatformAnalyticsResponse` nests token/latency metrics under `ai_metrics`, names the query total `total_questions_asked`, and exposes colleges as `top_active_colleges` (which carry no per-college `tokens`). When that endpoint succeeded, the service returned the raw nested object; the page then set `analytics` to that truthy object, so `analytics || {defaults}` did not apply, and `data.total_tokens.toLocaleString()` threw on `undefined`. Confirmed against the backend schemas and the service's pre-fix logic described in the report.

## Fix verification

### Loading / error / partial data — no crash path
- `page.tsx:23` initializes `isLoading` to `true`; `fetchAnalytics` toggles it around the request and clears it in `finally` (`page.tsx:25-35`).
- `page.tsx:89` renders `{isLoading ? <spinner/> : <> cards </>}`; the metric cards and breakdown grids only render when `isLoading` is false, so `.toLocaleString()` / `.map()` are never reached against not-yet-loaded data.
- `page.tsx:46-58` `data = analytics || {hardcoded defaults}` — `analytics` is `null` until a successful fetch, so on initial load / fetch failure `data` is the complete defaults object, never `undefined`.
- On fetch failure the catch block only logs (`page.tsx:31-33`); `setAnalytics` is not called, so the last successful value (or the defaults on first load) is retained.

### Defensive guards (every `data.*` / `c.*` access)
- `data.total_tokens` → `(data.total_tokens ?? 0).toLocaleString()` (`page.tsx:110`) — the reported crash line; now safe even if the field were undefined.
- `data.top_colleges.map` → `(data.top_colleges || []).map` (`page.tsx:177`).
- `c.tokens.toLocaleString()` → `(c.tokens ?? 0).toLocaleString()` (`page.tsx:181`).
- `data.total_queries` → `data.total_queries ?? 0` (`page.tsx:103`).
- `data.average_latency_ms` / `data.fallback_rate_percent` / `data.estimated_cost_usd` → each `?? 0` (`page.tsx:119,126,133`).
- `c.queries` / `c.percent` → `?? 0` (`page.tsx:181,184,187`); `c.name` left as a string (never throws).
- `DashboardCard` renders `{value}` directly with no method call, so guarded string/number values cannot crash downstream (`DashboardCard.tsx:43`).

### Service normalization — frontend type ↔ backend response agreement
- `super-admin-service.ts:155-179` `getUsageAnalytics` now normalizes the platform response into the flat `UsageAnalytics` (the type at `types/admin.ts`): `total_queries ← total_questions_asked`, `total_tokens/prompt_tokens/completion_tokens/average_latency_ms/fallback_rate_percent/estimated_cost_usd ← ai_metrics.*`, and `top_active_colleges` mapped to `{name, queries, tokens, percent}`, every field `?? 0` (name → `"Unknown"`). Return type annotated so both the normalized path and the fallback path conform to the same contract.
- The fallback `GET /super-admin/analytics` (`super_admin.py:793-808`) already returns `UsageAnalyticsResponse` (flat, with `top_colleges` dicts of `name/queries/tokens/percent`), which matches `UsageAnalytics` exactly — so the page always receives an agreed flat shape regardless of which endpoint answered.
- `getUsageAnalytics` is the only analytics-data hook the page uses; grep confirms it is called only by this page and the new test, so the normalization changes no other consumer.
- `getPlatformAnalytics` (the near-duplicate) was correctly left untouched (zero callers; out of scope).

## Scope / safety checks
- Only three frontend files changed; backend analytics schema/route/service files are unchanged (timestamp-confirmed) — no DB migrations, no schema/RLS/auth/role/tenant changes, no crawler functionality touched.
- `apps/admin-frontend/package.json` adds no dependencies; the new test uses only already-present `vitest`/`jsdom`/`react-dom` + a `vi.mock("next/link")` stub. No secrets exposed.
- Visible fields and styling preserved: all five metric cards, the tenant consumption breakdown, and the five-tier citation grounding distribution render unchanged; the hardcoded defaults object and hardcoded tier percentages are untouched. The only incidental edit is removal of a pre-existing unused `AlertTriangle` import from the file under edit — no display/behavior effect.
- Disclosed limitation (acceptable per task): on the platform source, per-college `tokens` default to `0` because the platform endpoint does not provide per-college token counts; the real per-college breakdown still shows when the fallback endpoint is the source. This is the task-sanctioned safe fallback and not a regression (the platform path previously crashed rather than rendering).

## Verification evidence (read from the report; not re-run)
- Vitest render tests: 7/7 PASS (3 existing `college-admin-service.test.ts` + 4 new analytics-page tests covering full platform response, partial response, empty data object, and total fetch failure). The new tests mount the real `AnalyticsPage` with mocked `fetch`/`localStorage` and assert no throw.
- `next build`: PASS, including "Linting and checking validity of types" and static prerender of `/super-admin/analytics` — type validity is covered by the build.
- Standalone `next lint` not run: the project has no ESLint config (pre-existing gap); type/lint checking is still covered by the `next build` step. Not a blocker.
- Live dev-server smoke test: not performed (requires a live super-admin session and backend; step rules forbid launching watch mode). Component-level render via vitest is the strongest available verification and is honestly distinguished from a live smoke test in the report.

Required verification (typecheck via build + tests) is present and recorded; no missing required evidence blocks approval.

## Conclusion
The crash is fixed at its source (service now returns the flat shape the page expects), with defense-in-depth page guards and a loading state that prevents rendering cards against undefined/partial/loading/error data. No behavior, fields, styling, or scope boundaries were violated. No blockers.
