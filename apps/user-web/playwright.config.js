import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.AIT_E2E_BASE_URL;

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/acceptance-results.json' }],
  ],
  use: {
    baseURL: baseURL || 'http://127.0.0.1:8000',
    // CI may provide a centrally managed Chromium instead of Playwright's
    // downloaded revision. Local developers normally leave this unset.
    launchOptions: process.env.AIT_E2E_CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.AIT_E2E_CHROMIUM_EXECUTABLE }
      : undefined,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  globalTeardown: './e2e/global-teardown.mjs',
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
});
