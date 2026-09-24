import { test, expect } from '@playwright/test';
import { collectBrowserFailures, expectations, liveEnabled, signup, sendAndWaitForAnswer } from './support.mjs';

test.beforeEach(async ({ page }) => {
  test.skip(!liveEnabled, 'Set AIT_E2E_ENABLE_LIVE=1 only against a dedicated E2E instance.');
  const browserFailures = [];
  collectBrowserFailures(page, browserFailures);
  page.__browserFailures = browserFailures;
  await page.goto('/');
  await expect(page.getByText('AI FAQ College Chat Bot').first()).toBeVisible();
});

test.afterEach(async ({ page }) => {
  expect(page.__browserFailures || [], 'Browser console errors, uncaught exceptions, or 5xx responses').toEqual([]);
});

// ── College-switch final behavior (spec §1-§15) ─────────────────────────────
// Flow: AIT conversation → mention RCTI → switch prompt → [Switch] →
// conversation.college_id = RCTI in the DB → persisted onboarding assistant
// message (NO auto-answer) → switch prompt gone → default college unchanged.
// Tenant isolation is verified server-side (no AIT data after the switch).
test('college switch persists conversation tenant, asks onboarding, and keeps default', async ({ page }) => {
  test.skip(!liveEnabled, 'Set AIT_E2E_ENABLE_LIVE=1 only against a dedicated E2E instance.');
  await signup(page);

  // 1. Establish the AIT context in this conversation
  await sendAndWaitForAnswer(page, 'AIT');

  // 2. Mention RCTI → the backend issues the college_switch_prompt block
  const answer = await sendAndWaitForAnswer(page, 'What about R.C. Technical Institute?');
  await expect(answer).toContainText(/Would you like to switch this conversation/i);
  const switchButton = answer.getByRole('button', { name: 'Switch', exact: true });
  await expect(switchButton).toBeVisible();

  // Capture the current assistant count so we can locate the onboarding message
  const priorAssistants = await page.locator('.message-row.assistant').count();

  // 3. Click [Switch] → POST /api/v1/user/college-context/switch happens
  //    through the UI; the switch prompt must disappear (§8).
  await switchButton.click();
  await expect(switchButton).toBeHidden({ timeout: 30_000 });

  // 4. The persisted onboarding message replaces the prompt (§12/§14):
  //    "You're now connected to R.C. Technical Institute. What information
  //    would you like to know about R.C. Technical Institute?" — NO auto-answer.
  const onboarding = page.locator('.message-row.assistant').nth(priorAssistants);
  await expect(onboarding).toContainText(/You're now connected to R\.?C\.? Technical Institute/i, { timeout: 30_000 });
  await expect(onboarding).toContainText(/What information would you like to know about/i);
  await expect(onboarding).not.toContainText(/BCA|fee|located|principal/i);

  // 5. Refresh persistence (§9): the backend still reports RCTI for this conv
  const convId = await page.evaluate(() => window.location.pathname);
  const state = await page.evaluate(async () => {
    const token = localStorage.getItem('ait_auth_token');
    const list = await fetch('/api/v1/conversations', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json());
    const current = list[0];
    const ctx = await fetch(`/api/v1/college-context/me?conversation_id=${current.id}`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json());
    return { conv: current, ctx };
  });
  expect(state.ctx.conversation_college).toBeTruthy();
  expect(state.ctx.conversation_college.code).toBe('RCTI');
  expect(state.ctx.default_college === null || state.ctx.default_college.code !== 'RCTI').toBeTruthy();

  // 6. Next question uses the new tenant automatically (§6): no re-prompt,
  //    no re-onboarding.
  const next = await sendAndWaitForAnswer(page, 'Where is the college?');
  await expect(next).not.toContainText(/Which college information do you want/i);
  await expect(next).not.toContainText(/Would you like to switch this conversation/i);
});

test('student authentication survives refresh, rejects bad login, and logs out', async ({ page }) => {
  const credentials = await signup(page);
  await page.reload();
  await expect(page.getByTitle('Logout')).toBeVisible();
  await page.getByTitle('Logout').click();
  await expect(page.getByRole('button', { name: 'Sign In / Sign Up' })).toBeVisible();
  const denied = await page.request.get('/api/v1/conversations');
  expect(denied.status()).toBe(401);
  await page.getByRole('button', { name: 'Sign In / Sign Up' }).click();
  await page.getByPlaceholder('name@example.com').fill(credentials.email);
  await page.locator('input[type="password"]').fill('wrong-password');
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await expect(page.getByText(/invalid|credentials/i)).toBeVisible();
  await page.locator('input[type="password"]').fill(credentials.password);
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await expect(page.getByTitle('Logout')).toBeVisible();

  await page.evaluate(() => localStorage.setItem('ait_auth_token', 'invalid-e2e-token'));
  await page.reload();
  await expect(page.getByRole('button', { name: 'Sign In / Sign Up' })).toBeVisible();
});

test('basic chat streams visible answers and persists them after refresh', async ({ page }) => {
  await signup(page);
  for (const question of ['hy', 'ai means', 'machine learning']) await sendAndWaitForAnswer(page, question);
  await expect(page.locator('.conversation-item').first()).toBeVisible();
  await page.reload();
  await page.locator('.conversation-item').first().click();
  await expect(page.locator('.message-row.user')).toHaveCount(3);
  await expect(page.locator('.message-row.assistant')).toHaveCount(3);
});

test('institutional facts match the verified database fixture and display source authority', async ({ page }) => {
  await signup(page);
  const expected = expectations();
  const fee = await sendAndWaitForAnswer(page, 'What is the BCA fee for 2026-27?');
  await expect(fee).toContainText(expected.bca_fee);
  await expect(fee.getByLabel('Answer verification')).toBeVisible();
  await expect(fee.getByLabel('Sources')).toBeVisible();
  const faculty = await sendAndWaitForAnswer(page, 'What is the verified DBMS faculty?');
  await expect(faculty).toContainText(expected.dbms_faculty);
  await expect(faculty.getByLabel('Sources')).toBeVisible();
  const ai = await sendAndWaitForAnswer(page, 'Does AIT offer AI?');
  if (expected.has_ai_offering) await expect(ai.getByLabel('Answer verification')).toBeVisible();
  else await expect(ai).toContainText(/couldn.t verify|not available/i);
});

test('general and unverified institutional questions do not receive a false verified badge', async ({ page }) => {
  await signup(page);
  const general = await sendAndWaitForAnswer(page, 'What is AI?');
  await expect(general.getByText('General AI Academic Knowledge')).toBeVisible();
  await expect(general.getByText('Verified AIT Institutional Fact')).toHaveCount(0);
  const unverified = await sendAndWaitForAnswer(page, 'Tell me an unverified fact about AIT.');
  await expect(unverified.getByText('Verified AIT Institutional Fact')).toHaveCount(0);
});

test('conversation persists, feedback sends once, and mobile composer remains usable', async ({ page, isMobile }) => {
  await signup(page);
  await sendAndWaitForAnswer(page, 'What is BCA?');
  await expect(page.locator('.conversation-item').first()).toBeVisible();
  const feedback = page.waitForResponse(response => response.url().includes('/chat/feedback') && response.request().method() === 'POST');
  await page.getByTitle('Helpful').last().click();
  await expect((await feedback).ok()).toBeTruthy();
  await expect(page.getByTitle('Helpful').last()).toBeDisabled();
  await page.reload();
  await expect(page.locator('.conversation-item').first()).toBeVisible();
  if (isMobile) {
    await expect(page.locator('textarea.composer-textarea')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  }
});

test('multilingual and follow-up context remain visible in one student conversation', async ({ page }) => {
  await signup(page);
  for (const question of ['BCA shu chhe?', 'BCA kya hai?', 'What is BCA?', 'What subjects are in it?', 'Which semester has AI?']) {
    await sendAndWaitForAnswer(page, question);
  }
  await expect(page.locator('.message-row.user')).toHaveCount(5);
  await expect(page.locator('.message-row.assistant')).toHaveCount(5);
});

function knownGap(title, reason) {
  test.describe(title, () => {
    test.fixme(true, reason);
    test('is not executable in this environment', () => {});
  });
}

knownGap('document RAG: uploaded XLSX unique value is answered with User Document Context provenance',
  'Requires a deterministic local provider fixture before this can be marked PASS.');
knownGap('voice: microphone recognition and TTS playback',
  'NOT TESTABLE in standard CI without a controlled microphone and audio device.');
knownGap('stop generation and retry',
  'Requires a controlled slow/failing provider fixture; do not mutate a live provider to test it.');
knownGap('provider/key rotation, free-only policy, and admin changes without restart',
  'Requires an isolated admin test environment and non-production provider credentials.');
knownGap('rename and archive conversation actions',
  'FAIL: the student UI currently exposes pin and delete but no rename or archive control.');
