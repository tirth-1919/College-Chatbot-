import { defineConfig, devices } from '@playwright/test';

const configuredBaseURL = process.env.AIT_E2E_BASE_URL || 'http://127.0.0.1:5173';
// AIT_E2E_BASE_URL historically documented the API/self-hosted port (8000),
// but browser tests require the Vite SPA; the API is reached through its proxy.
const baseURL = new URL(configuredBaseURL).port === '8000'
  ? 'http://127.0.0.1:5173'
  : configuredBaseURL;
const startsLocalFrontend = new URL(baseURL).port === '5173';

export default defineConfig({
  ...(startsLocalFrontend ? {
    webServer: {
      command: 'npm run dev --host 127.0.0.1',
      url: `${baseURL.replace(/\/$/, '')}/`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  } : {}),
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
    baseURL,
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
