import { test, expect } from '@playwright/test';
import {
  liveEnabled,
  signup,
  sendAndWaitForAnswer,
  resolveCollegeForE2E,
  collectBrowserFailures,
} from './support.mjs';

test.describe('AI FAQ College Chat Bot - New Question Answer Tests', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(
      !liveEnabled,
      'Set AIT_E2E_ENABLE_LIVE=1 only against a dedicated E2E instance.'
    );

    const browserFailures = [];
    collectBrowserFailures(page, browserFailures);
    page.__browserFailures = browserFailures;

    await page.goto('/');

    await expect(
      page.getByText('AI FAQ College Chat Bot').first()
    ).toBeVisible();
  });

  test.afterEach(async ({ page }) => {
    expect(
      page.__browserFailures || []
    ).toEqual([]);
  });

  test('AIT transportation information returns a relevant answer', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'AIT');

    const answer = await sendAndWaitForAnswer(
      page,
      'What transportation or bus facility information is available for Ahmedabad Institute of Technology?'
    );

    // The answer must actually address transportation/bus information.
    await expect(answer).toContainText(
      /bus|transport|vehicle|route|pickup|drop/i
    );

    // Prevent unrelated institutional content from being accepted.
    await expect(answer).not.toContainText(
      /placement|company|faculty|library|walkathon|hackathon|de-addiction|celebrated various days/i
    );

    // Do not accept a generic verification failure as a successful answer.
    await expect(answer).not.toContainText(
      /could not be verified|no verified information/i
    );
  });

  test('RCTI institute committee question returns relevant information', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'RCTI');

    const answer = await sendAndWaitForAnswer(
      page,
      'What information does R.C. Technical Institute provide about its institute committees?'
    );

    await expect(answer).toContainText(
      /committee|committees/i
    );

    await expect(answer).not.toContainText(
      /AIT|Ahmedabad Institute of Technology/i
    );
  });

  test('AIT BCA fee question returns the expected 2026-27 fee', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'AIT');

    const answer = await sendAndWaitForAnswer(
      page,
      'What is the BCA tuition fee at Ahmedabad Institute of Technology for the 2026-27 academic year?'
    );

    await expect(answer).toContainText(
      /32,000|₹32,000/i
    );
  });

  test('RCTI Semester 5 BCA fee question returns the expected fee', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'RCTI');

    const answer = await sendAndWaitForAnswer(
      page,
      'How much is the BCA Semester 5 fee at R.C. Technical Institute for 2026-27?'
    );

    await expect(answer).toContainText(
      /48,000|₹48,000/i
    );

    await expect(answer).not.toContainText(
      /Ahmedabad Institute of Technology|AIT/i
    );
  });

  test('frontend and backend question receives general programming guidance', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'AIT');

    const answer = await sendAndWaitForAnswer(
      page,
      'What is the difference between frontend and backend development?'
    );

    await expect(answer).toContainText(
      /frontend/i
    );

    await expect(answer).toContainText(
      /backend/i
    );

    await expect(answer).not.toContainText(
      /AIT Placement|RCTI Placement|college placement/i
    );
  });

  test('REST API beginner question receives programming guidance', async ({ page }) => {
    await signup(page);
    await resolveCollegeForE2E(page, 'AIT');

    const answer = await sendAndWaitForAnswer(
      page,
      'What programming concepts should a beginner learn before creating a REST API?'
    );

    await expect(answer).toContainText(
      /programming|function|variable|HTTP|API|JSON/i
    );

    await expect(answer).not.toContainText(
      /AIT Placement|RCTI Placement|library|faculty/i
    );
  });
});