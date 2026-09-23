import fs from 'node:fs';
import path from 'node:path';
import { expect } from '@playwright/test';

export const liveEnabled = process.env.AIT_E2E_ENABLE_LIVE === '1';
export const password = 'E2E-Student-Password-2026!';
export const unique = () => `e2e-student-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@e2e.localtest`;

export function expectations() {
  const fixture = process.env.AIT_E2E_FIXTURE || path.join(process.cwd(), 'e2e', '.generated-expectations.json');
  if (!fs.existsSync(fixture)) throw new Error(`Missing E2E fixture: ${fixture}. Run backend/scripts/export_e2e_fixture.py first.`);
  return JSON.parse(fs.readFileSync(fixture, 'utf8'));
}

export async function signup(page, name = 'E2E AIT Student') {
  const email = unique();
  await page.getByRole('button', { name: 'Sign In / Sign Up' }).click();
  await page.getByRole('button', { name: 'Create Account' }).click();
  await page.getByPlaceholder('e.g. Anjali Sharma').fill(name);
  await page.getByPlaceholder('name@aitindia.in').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Sign Up', exact: true }).click();
  await expect(page.getByTitle('Logout')).toBeVisible();
  return { email, password };
}

export async function sendAndWaitForAnswer(page, question) {
  const prior = await page.locator('.message-row.assistant').count();
  await page.locator('textarea.composer-textarea').fill(question);
  await page.getByTitle('Send query').click();
  await expect(page.locator('.message-row.user').last()).toContainText(question);
  const answer = page.locator('.message-row.assistant').nth(prior);
  await expect(answer).toBeVisible({ timeout: 30_000 });
  await expect(answer).not.toContainText('Thinking...', { timeout: 120_000 });
  await expect(answer).not.toHaveText(/^\s*$/);
  await expect(answer).not.toContainText(/traceback|stack trace|api[_ -]?key|bearer ey/i);
  return answer;
}

export function collectBrowserFailures(page, failures) {
  page.on('console', message => {
    const text = message.text();
    // Expected auth noise: tests deliberately trigger bad logins, invalid
    // tokens and expired sessions — the resulting 401/refresh messages are
    // part of the asserted behavior, not defects.
    if (/No refresh token available/i.test(text)) return;
    if (/Failed to load resource.*401/i.test(text)) return;
    if (message.type() === 'error') failures.push(`console: ${text}`);
  });
  page.on('pageerror', error => failures.push(`uncaught: ${error.message}`));
  page.on('response', response => { if (response.status() >= 500) failures.push(`HTTP ${response.status()}: ${response.url()}`); });
}
