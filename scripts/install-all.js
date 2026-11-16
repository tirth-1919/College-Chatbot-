/**
 * Multi-package installer.
 * Installs dependencies for user-frontend and admin-frontend.
 */

const { execSync } = require('child_process');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..');
const USER_FRONTEND_DIR = path.join(ROOT_DIR, 'apps', 'user-frontend');
const ADMIN_FRONTEND_DIR = path.join(ROOT_DIR, 'apps', 'admin-frontend');

console.log('====================================================');
console.log('  CAMPUSAI: INSTALLING FRONTEND DEPENDENCIES');
console.log('====================================================\n');

try {
  console.log('[1/2] Installing dependencies for apps/user-frontend...');
  execSync('npm install', { cwd: USER_FRONTEND_DIR, stdio: 'inherit' });
  console.log('  ✓ apps/user-frontend installed successfully.\n');

  console.log('[2/2] Installing dependencies for apps/admin-frontend...');
  execSync('npm install', { cwd: ADMIN_FRONTEND_DIR, stdio: 'inherit' });
  console.log('  ✓ apps/admin-frontend installed successfully.\n');

  console.log('====================================================');
  console.log('ALL DEPENDENCIES INSTALLED SUCCESSFULLY!');
  console.log('You can now run: npm run dev');
  console.log('====================================================');
} catch (err) {
  console.error('\nInstallation failed:', err.message);
  process.exit(1);
}

