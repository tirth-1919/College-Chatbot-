/**
 * CampusAI Unified Development Runner.
 * Starts Backend API, Student Web Portal, and Admin Web Portal concurrently.
 * Zero external dependencies required.
 */

const { spawn, spawnSync, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');

const ROOT_DIR = path.resolve(__dirname, '..');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const USER_FRONTEND_DIR = path.join(ROOT_DIR, 'apps', 'user-frontend');
const ADMIN_FRONTEND_DIR = path.join(ROOT_DIR, 'apps', 'admin-frontend');

// ANSI Color Helpers
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  red: '\x1b[31m',
};

// Debugger ports (localhost-only, dev-only)
const DEBUG_PORTS = {
  backend: 5678,       // debugpy (Python/FastAPI)
  userFrontend: 9229,  // Node.js --inspect (user portal)
  adminFrontend: 9230, // Node.js --inspect (admin portal)
};

function printBanner() {
  console.log(`
${colors.cyan}${colors.bright}========================================================================${colors.reset}
${colors.cyan}${colors.bright}   AI FAQ COLLEGE CHAT BOT - UNIFIED SAAS DEVELOPMENT RUNNER           ${colors.reset}
${colors.cyan}${colors.bright}========================================================================${colors.reset}
  ${colors.green}● Backend API (FastAPI):${colors.reset}          http://localhost:8000
  ${colors.green}● Interactive Docs (Swagger):${colors.reset}    http://localhost:8000/docs
  ${colors.blue}● Student / User Portal:${colors.reset}        http://localhost:3000
    ${colors.dim}↳ Auto-Login Student:${colors.reset}       http://localhost:3000/login?autologin=true
  ${colors.magenta}● Admin & Super Admin Portal:${colors.reset}   http://localhost:3001
    ${colors.dim}↳ Auto-Login Super Admin:${colors.reset}   http://localhost:3001/login?autologin=superadmin
    ${colors.dim}↳ Auto-Login College Admin:${colors.reset} http://localhost:3001/login?autologin=collegeadmin
${colors.cyan}------------------------------------------------------------------------${colors.reset}
  ${colors.yellow}● Debuggers (attach from VS Code):${colors.reset}
    ${colors.dim}↳ Python/FastAPI (debugpy):${colors.reset}  127.0.0.1:${DEBUG_PORTS.backend}
    ${colors.dim}↳ User Frontend (Node):${colors.reset}      127.0.0.1:${DEBUG_PORTS.userFrontend}
    ${colors.dim}↳ Admin Frontend (Node):${colors.reset}     127.0.0.1:${DEBUG_PORTS.adminFrontend}
  Press ${colors.bright}Ctrl + C${colors.reset} at any time to gracefully stop all services.
${colors.cyan}========================================================================${colors.reset}
`);
}

// Track child processes for clean termination
const processes = [];

function checkDependencies(dir, name) {
  const nodeModules = path.join(dir, 'node_modules');
  if (!fs.existsSync(nodeModules)) {
    console.log(`${colors.yellow}[INFO] ${name} dependencies not found. Auto-installing packages in ${path.relative(ROOT_DIR, dir)}...${colors.reset}`);
    try {
      execSync('npm install', { cwd: dir, stdio: 'inherit' });
      console.log(`${colors.green}[SUCCESS] ${name} packages installed successfully.${colors.reset}\n`);
      return true;
    } catch (err) {
      console.log(`${colors.red}[ERROR] Auto-install failed for ${name}: ${err.message}${colors.reset}`);
      return false;
    }
  }
  return true;
}

function checkPython() {
  try {
    const res = execSync('python --version', { stdio: ['ignore', 'pipe', 'ignore'], timeout: 2000 }).toString();
    if (res.toLowerCase().includes('python')) {
      return 'python';
    }
  } catch (e) {
    try {
      const resPy = execSync('py --version', { stdio: ['ignore', 'pipe', 'ignore'], timeout: 2000 }).toString();
      if (resPy.toLowerCase().includes('python')) {
        return 'py';
      }
    } catch (e2) {}
  }

  // Common Windows installation locations
  if (process.platform === 'win32') {
    const localApp = process.env.LOCALAPPDATA || '';
    const candidates = [
      path.join(ROOT_DIR, '.venv', 'Scripts', 'python.exe'),
      path.join(ROOT_DIR, 'backend', '.venv', 'Scripts', 'python.exe'),
      path.join(ROOT_DIR, 'backend', 'venv', 'Scripts', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python313', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python312', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python311', 'python.exe'),
      path.join(localApp, 'Programs', 'Python', 'Python310', 'python.exe'),
      'C:\\Python313\\python.exe',
      'C:\\Python312\\python.exe',
      'C:\\Python311\\python.exe',
      'C:\\Python310\\python.exe',
      path.join(ROOT_DIR, 'backend', 'venv', 'Scripts', 'python.exe'),
      path.join(ROOT_DIR, 'backend', '.venv', 'Scripts', 'python.exe'),
    ];
    for (const p of candidates) {
      if (fs.existsSync(p)) {
        return `"${p}"`;
      }
    }
  }

  return null;
}

function startProcess(prefix, color, command, args, cwd, extraEnv = {}) {
  console.log(`${color}[${prefix}] Starting: ${command} ${args.join(' ')}${colors.reset}`);

  const isWindows = process.platform === 'win32';
  const proc = spawn(isWindows && command === 'npm' ? 'npm.cmd' : command, args, {
    cwd,
    shell: true,
    env: { ...process.env, FORCE_COLOR: '1', ...extraEnv },
    stdio: ['ignore', 'pipe', 'pipe'],
  });

  processes.push({ prefix, color, proc });

  proc.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach((line) => {
      if (line.trim()) {
        console.log(`${color}[${prefix}]${colors.reset} ${line}`);
      }
    });
  });

  proc.stderr.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach((line) => {
      if (line.trim()) {
        console.log(`${color}[${prefix}]${colors.reset} ${line}`);
      }
    });
  });

  proc.on('close', (code) => {
    if (code !== 0 && code !== null) {
      console.log(`${color}[${prefix}] Process exited with code ${code}${colors.reset}`);
    }
  });

  proc.on('error', (err) => {
    console.log(`${colors.red}[${prefix}] Failed to start: ${err.message}${colors.reset}`);
  });

  return proc;
}

function freePort(port) {
  if (process.platform !== 'win32') return;
  try {
    const res = spawnSync('powershell.exe', [
      '-NoProfile',
      '-Command',
      `Get-NetTCPConnection -LocalPort ${port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess`
    ], { encoding: 'utf8', timeout: 4000 });

    if (res.stdout) {
      const pids = res.stdout.trim().split(/\r?\n/);
      const killed = new Set();
      for (const p of pids) {
        const pid = p.trim();
        if (/^\d+$/.test(pid) && pid !== '0' && pid !== process.pid.toString() && !killed.has(pid)) {
          killed.add(pid);
          try {
            spawnSync('taskkill', ['/pid', pid, '/f', '/t'], { stdio: 'ignore' });
          } catch (e) {}
        }
      }
    }
  } catch (e) {}
}

let isCleaningUp = false;
function cleanup() {
  if (isCleaningUp) return;
  isCleaningUp = true;
  console.log(`\n${colors.yellow}Shutting down all active services...${colors.reset}`);
  processes.forEach(({ prefix, color, proc }) => {
    try {
      if (process.platform === 'win32') {
        spawnSync('taskkill', ['/pid', proc.pid.toString(), '/f', '/t'], { stdio: 'ignore' });
      } else {
        proc.kill('SIGTERM');
      }
      console.log(`${color}[${prefix}] Stopped.${colors.reset}`);
    } catch (err) {}
  });
  // Ensure debugger and app ports are fully cleared
  freePort(DEBUG_PORTS.backend);
  freePort(8000);
  freePort(3000);
  freePort(3001);

  process.exit(0);
}

process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

// Parse arguments
const args = process.argv.slice(2);
const targetArg = args.find((a) => a.startsWith('--target='));
const target = targetArg ? targetArg.split('=')[1] : 'all';

printBanner();

// 1. Start Backend API (with debugpy on 127.0.0.1:5678)
if (target === 'all' || target === 'backend') {
  freePort(DEBUG_PORTS.backend);
  freePort(8000);
  const pyCmd = checkPython();
  if (pyCmd) {
    // Launch via debugpy so VS Code can attach to the Python process.
    // --listen binds to localhost only (never 0.0.0.0).
    // No --wait-for-client so the server starts immediately without blocking.
    // --reload is preserved on uvicorn for hot-reload during development.
    console.log(`${colors.yellow}[BACKEND] debugpy listening on 127.0.0.1:${DEBUG_PORTS.backend} (attach from VS Code when ready)${colors.reset}`);
    startProcess(
      'BACKEND', colors.green,
      pyCmd,
      [
        '-m', 'debugpy',
        '--listen', `127.0.0.1:${DEBUG_PORTS.backend}`,
        '-m', 'uvicorn', 'app.main:app',
        '--reload',
        '--port', '8000',
      ],
      BACKEND_DIR
    );
  } else {
    console.log(`${colors.yellow}[BACKEND] Python runtime not detected or execution alias stub active.${colors.reset}`);
    console.log(`${colors.yellow}[BACKEND] To start FastAPI backend manually: cd backend && python -m uvicorn app.main:app --reload --port 8000${colors.reset}\n`);
  }
}

// 2. Start Student Frontend (Port 3000)
if (target === 'all' || target === 'user') {
  freePort(3000);
  checkDependencies(USER_FRONTEND_DIR, 'Student Frontend');
  startProcess('STUDENT', colors.blue, 'npm', ['run', 'dev'], USER_FRONTEND_DIR);
}

// 3. Start Admin Frontend (Port 3001)
if (target === 'all' || target === 'admin') {
  freePort(3001);
  checkDependencies(ADMIN_FRONTEND_DIR, 'Admin Frontend');
  startProcess('ADMIN', colors.magenta, 'npm', ['run', 'dev'], ADMIN_FRONTEND_DIR);
}

// 4. Automatic Browser Launch with Auto-Login (when --open or --autologin passed)
function openBrowser(url) {
  try {
    if (process.platform === 'win32') {
      spawn('cmd.exe', ['/c', 'start', '""', url], { stdio: 'ignore', detached: true }).unref();
    } else if (process.platform === 'darwin') {
      spawn('open', [url], { stdio: 'ignore', detached: true }).unref();
    } else {
      spawn('xdg-open', [url], { stdio: 'ignore', detached: true }).unref();
    }
  } catch (err) {}
}

function waitForUrl(url, timeoutMs = 45000) {
  const start = Date.now();
  return new Promise((resolve) => {
    function poll() {
      const req = http.get(url, (res) => {
        resolve(true);
      });
      req.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          resolve(false);
        } else {
          setTimeout(poll, 400);
        }
      });
      req.setTimeout(800, () => {
        req.destroy();
      });
    }
    poll();
  });
}

const shouldOpen = args.includes('--open') || args.includes('--autologin');
if (shouldOpen) {
  console.log(`${colors.cyan}[LAUNCHER] Auto-login active. Waiting for student and admin web portals to compile and listen...${colors.reset}`);

  if (target === 'all' || target === 'user') {
    waitForUrl('http://127.0.0.1:3000').then((ready) => {
      if (ready) {
        console.log(`${colors.green}[BROWSER] Student Portal ready! Opening http://localhost:3000/login?autologin=true${colors.reset}`);
        openBrowser('http://localhost:3000/login?autologin=true');
      } else {
        console.log(`${colors.yellow}[BROWSER] Student Portal did not respond within timeout.${colors.reset}`);
      }
    });
  }

  if (target === 'all' || target === 'admin') {
    waitForUrl('http://127.0.0.1:3001').then((ready) => {
      if (ready) {
        setTimeout(() => {
          console.log(`${colors.magenta}[BROWSER] Admin Portal ready! Opening http://localhost:3001/login?autologin=superadmin${colors.reset}`);
          openBrowser('http://localhost:3001/login?autologin=superadmin');
        }, 800);
      } else {
        console.log(`${colors.yellow}[BROWSER] Admin Portal did not respond within timeout.${colors.reset}`);
      }
    });
  }
}

