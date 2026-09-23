import { execFileSync } from 'node:child_process';

export default async function globalTeardown() {
  // Cleanup is deliberately opt-in and only accepts the dedicated E2E database.
  if (process.env.AIT_E2E_CLEANUP !== '1' || !process.env.AIT_E2E_DATABASE_URL) return;
  execFileSync('python', ['backend/scripts/cleanup_e2e_data.py'], {
    cwd: '../..',
    env: { ...process.env, DATABASE_URL: process.env.AIT_E2E_DATABASE_URL, AIT_E2E_CLEANUP: '1' },
    stdio: 'inherit',
  });
}
