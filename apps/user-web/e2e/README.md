# Real-user acceptance tests

These Playwright tests drive the rendered student UI, including signup/login,
session restore, chat streaming, authority labels, conversation persistence,
feedback, and a mobile viewport. They are intentionally opt-in: they must run
only against a dedicated database and never against the normal local database.

```powershell
$env:DATABASE_URL = 'sqlite:///./backend/ait_e2e.db'
$env:AIT_E2E_BASE_URL = 'http://127.0.0.1:8000'
$env:AIT_E2E_ENABLE_LIVE = '1'
$env:AIT_E2E_DATABASE_URL = $env:DATABASE_URL
$env:AIT_E2E_CLEANUP = '1'
python backend/scripts/export_e2e_fixture.py
python user.py
# In another terminal:
Set-Location apps/user-web
npm run dev
npm run test:e2e
```

Install a browser once with `npx playwright install chromium`. The cleanup step
refuses any database URL that does not contain `ait_e2e` and removes only users
whose email starts with `e2e-student-`.

The `fixme` cases are explicit acceptance gaps, not passing checks: document
RAG provenance, voice/audio hardware, stop/retry under a controlled slow
provider, and admin/provider mutation journeys need isolated fixtures.

The fixture is derived from the dedicated database at runtime; no AIT fee or
faculty answer is embedded in the browser test. `test-results/acceptance-results.json`
and `playwright-report/` are the evidence for each run. A skipped test is not a
PASS: report it as **NOT TESTABLE** until its stated environment is available.
