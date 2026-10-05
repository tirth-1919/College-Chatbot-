import fs from 'node:fs';
import path from 'node:path';
import { expect } from '@playwright/test';

export const liveEnabled = process.env.AIT_E2E_ENABLE_LIVE === '1';

export const password = 'E2E-Student-Password-2026!';

export const unique = () =>
  `e2e-student-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@e2e.localtest`;

export function expectations() {
  const fixture =
    process.env.AIT_E2E_FIXTURE ||
    path.join(process.cwd(), 'e2e', '.generated-expectations.json');

  if (!fs.existsSync(fixture)) {
    throw new Error(
      `Missing E2E fixture: ${fixture}. Run backend/scripts/export_e2e_fixture.py first.`
    );
  }

  return JSON.parse(fs.readFileSync(fixture, 'utf8'));
}

export async function signup(page, name = 'E2E AIT Student', options = {}) {
  const email = unique();

  const collegesResponse = await page.request.get(
    '/api/v1/colleges/list-public'
  );

  expect(collegesResponse.ok()).toBeTruthy();

  const colleges = await collegesResponse.json();

  const requestedCollegeId =
    options.collegeId || process.env.AIT_E2E_COLLEGE_ID;

  const requestedCollegeCode =
    options.collegeCode ||
    process.env.AIT_E2E_COLLEGE_CODE ||
    (name.toLowerCase().includes('rcti') ? 'RCTI' : 'AIT');

  const college = colleges.find(item =>
    requestedCollegeId
      ? item.id === requestedCollegeId
      : item.code?.toUpperCase() === requestedCollegeCode.toUpperCase()
  );

  if (!college) {
    throw new Error(
      `No active E2E college matched id=${requestedCollegeId || '<none>'} ` +
      `code=${requestedCollegeCode}. Available: ` +
      `${colleges.map(item => `${item.code}:${item.id}`).join(', ')}`
    );
  }

  // Keep production signup unchanged.
  // Only this live E2E signup request receives college_id.
  await page.route('**/api/v1/auth/signup', async route => {
    const request = route.request();
    const payload = JSON.parse(request.postData() || '{}');

    await route.continue({
      postData: JSON.stringify({
        ...payload,
        college_id: college.id,
      }),
      headers: {
        ...request.headers(),
        'content-type': 'application/json',
      },
    });
  });

  await page.getByRole('button', {
    name: 'Sign In / Sign Up',
  }).click();

  await page.getByRole('button', {
    name: 'Create Account',
  }).click();

  await page.getByPlaceholder('e.g. Anjali Sharma').fill(name);

  await page.getByPlaceholder('name@example.com').fill(email);

  await page.locator('input[type="password"]').fill(password);

  const signupResponsePromise = page
    .waitForResponse(
      response =>
        response.request().method() === 'POST' &&
        response.status() >= 400,
      { timeout: 10_000 }
    )
    .catch(() => null);

  await page.getByRole('button', {
    name: 'Sign Up',
    exact: true,
  }).click();

  const failedResponse = await signupResponsePromise;

  if (failedResponse) {
    let body = '';

    try {
      body = await failedResponse.text();
    } catch {
      body = '<unable to read response body>';
    }

    throw new Error(
      `Signup API failed: ${failedResponse.status()} ${failedResponse.url()}\n` +
      `Response: ${body}`
    );
  }

  await expect(page.getByTitle('Logout')).toBeVisible();

  return {
    email,
    password,
    collegeId: college.id,
    collegeCode: college.code,
  };
}

/**
 * Resolve the active college for a fresh E2E account.
 *
 * Uses the full official college name so the resolver does not
 * treat short codes such as "AIT" as ambiguous.
 */
export async function resolveCollegeForE2E(page, college) {
  const collegeNames = {
    AIT: 'Ahmedabad Institute of Technology',
    RCTI: 'R.C. Technical Institute',
  };

  const normalizedCollege =
    collegeNames[college?.toUpperCase?.()] || college;

  if (!normalizedCollege) {
    throw new Error(
      'resolveCollegeForE2E requires a college name or supported college code.'
    );
  }

  const resolveResponsePromise = page.waitForResponse(
    response =>
      response.request().method() === 'POST' &&
      response.url().includes('/api/v1/college-context/resolve'),
    { timeout: 30_000 }
  );

  await page.locator('textarea.composer-textarea').fill(normalizedCollege);

  await page.getByTitle('Send query').click();

  const resolveResponse = await resolveResponsePromise;

  expect(resolveResponse.status()).toBe(200);

  const resolveData = await resolveResponse.json();

  if (resolveData.status === 'AMBIGUOUS') {
    throw new Error(
      `College resolution was ambiguous for "${normalizedCollege}". ` +
      `Response: ${JSON.stringify(resolveData)}`
    );
  }

  expect(resolveData.status).toBe('RESOLVED');
  expect(resolveData.college?.id).toBeTruthy();

  const composer = page.locator('textarea.composer-textarea');

  await expect(composer).toBeVisible({
    timeout: 10_000,
  });

  await expect(composer).toBeEnabled({
    timeout: 10_000,
  });

  return {
    collegeId: resolveData.college.id,
    college: resolveData.college,
  };
}

export async function sendAndWaitForAnswer(page, question) {
  const priorUserCount = await page.locator('.message-row.user').count();
  const composer = page.locator('textarea.composer-textarea');

  await expect(composer).toBeVisible({
    timeout: 10_000,
  });

  await expect(composer).toBeEnabled({
    timeout: 10_000,
  });

  await composer.fill(question);

  await page.getByTitle('Send query').click();

  const submittedQuestion = page
    .locator('.message-row.user')
    .filter({ hasText: question })
    .last();

  // Anchor the answer to this question rather than to the assistant count:
  // the preceding college-resolution message is also an assistant row.
  await expect(page.locator('.message-row.user')).toHaveCount(
    priorUserCount + 1,
    { timeout: 30_000 }
  );

  await expect(submittedQuestion).toBeVisible({
    timeout: 30_000,
  });

  // The send button changes back only after the SSE stream emits completion.
  await expect(page.getByTitle('Send query')).toBeVisible({
    timeout: 120_000,
  });

  const answer = submittedQuestion.locator(
    'xpath=following-sibling::div[contains(concat(" ", normalize-space(@class), " "), " message-row ") and contains(concat(" ", normalize-space(@class), " "), " assistant ")]'
  ).last();

  await expect(answer).toBeVisible({
    timeout: 30_000,
  });

  await expect(answer).not.toContainText('Thinking...', {
    timeout: 120_000,
  });

  await expect(answer).not.toHaveText(/^\s*$/);

  await expect(answer).not.toContainText(
    /traceback|stack trace|api[_ -]?key|bearer ey/i
  );

  return answer;
}

export function collectBrowserFailures(page, failures) {
  page.on('console', message => {
    const text = message.text();

    // Expected authentication noise.
    if (/No refresh token available/i.test(text)) {
      return;
    }

    if (/Failed to load resource.*401/i.test(text)) {
      return;
    }

    if (message.type() === 'error') {
      failures.push(`console: ${text}`);
    }
  });

  page.on('pageerror', error => {
    failures.push(`uncaught: ${error.message}`);
  });

  page.on('response', response => {
    if (response.status() >= 500) {
      failures.push(
        `HTTP ${response.status()}: ${response.url()}`
      );
    }
  });
}