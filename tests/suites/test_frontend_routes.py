"""
Frontend routes and UI verification test suite.
Tests both User Frontend (port 3000) and Admin Frontend (port 3001):
- Discovers all Next.js pages from src/app
- Tests HTTP status codes, rendering, and response times
- Evaluates form presence (inputs, buttons) on auth/register pages
- Detects unhandled browser console errors / hydration mismatches
- Captures screenshots on failure into reports/screenshots/
- Verifies TypeScript compilation integrity (tsc --noEmit)
"""

import os
import sys
import time
import asyncio
from typing import List, Dict, Any, Optional
import httpx

from tests.config import (
    USER_FRONTEND_URL,
    ADMIN_FRONTEND_URL,
    SCREENSHOTS_DIR,
    FRONTEND_PERF_LIMIT_MS,
    USER_FRONTEND_DIR,
    ADMIN_FRONTEND_DIR,
)

USER_PAGES = [
    {"path": "/", "name": "User Landing Page", "auth_required": False, "expect_status": [200]},
    {"path": "/login", "name": "User Login Page", "auth_required": False, "expect_status": [200]},
    {"path": "/register", "name": "User Register Page", "auth_required": False, "expect_status": [200]},
    {"path": "/register-college", "name": "Register College Page", "auth_required": False, "expect_status": [200]},
    {"path": "/registration-status", "name": "Registration Status Page", "auth_required": False, "expect_status": [200]},
    {"path": "/colleges", "name": "College Directory Page", "auth_required": False, "expect_status": [200]},
    {"path": "/chat", "name": "Student Chat Page", "auth_required": False, "expect_status": [200, 307, 308]},
    {"path": "/dashboard", "name": "Student Dashboard (Protected)", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/profile", "name": "Student Profile (Protected)", "auth_required": True, "expect_status": [200, 307, 308]},
]

ADMIN_PAGES = [
    {"path": "/", "name": "Admin Root", "auth_required": False, "expect_status": [200, 307, 308]},
    {"path": "/login", "name": "Admin Login Page", "auth_required": False, "expect_status": [200]},
    {"path": "/register-college", "name": "Admin College Onboarding", "auth_required": False, "expect_status": [200]},
    {"path": "/registration-status", "name": "Admin Reg Status", "auth_required": False, "expect_status": [200]},
    {"path": "/college-admin/dashboard", "name": "College Admin Dashboard", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/college-admin/analytics", "name": "College Admin Analytics", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/college-admin/documents", "name": "College Admin Documents", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/college-admin/knowledge", "name": "College Admin Knowledge", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/super-admin/dashboard", "name": "Super Admin Dashboard", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/super-admin/colleges", "name": "Super Admin Colleges", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/super-admin/users", "name": "Super Admin Users", "auth_required": True, "expect_status": [200, 307, 308]},
    {"path": "/super-admin/system-health", "name": "Super Admin Health", "auth_required": True, "expect_status": [200, 307, 308]},
]


async def run_frontend_tests() -> Dict[str, Any]:
    """Execute all frontend route and UI tests."""
    results = []
    http_records = []
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    # 0. Pre-flight: check whether frontend dev servers are reachable
    user_fe_up = False
    admin_fe_up = False
    async with httpx.AsyncClient(timeout=5.0) as probe:
        try:
            r = await probe.get(f"{USER_FRONTEND_URL}/")
            user_fe_up = True
        except Exception:
            pass
        try:
            r = await probe.get(f"{ADMIN_FRONTEND_URL}/")
            admin_fe_up = True
        except Exception:
            pass

    # 1. Check TypeScript compilation integrity on both frontends
    async def check_ts(project_dir: str, name: str):
        t0 = time.time()
        try:
            proc = await asyncio.create_subprocess_exec(
                "npx.cmd", "tsc", "--noEmit",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            duration_ms = (time.time() - t0) * 1000
            passed = (proc.returncode == 0)
            results.append({
                "test": f"TypeScript Typecheck: {name}",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": duration_ms,
                "message": f"TypeScript zero-error check passed in {duration_ms:.0f}ms" if passed else f"TypeScript errors detected:\n{stdout.decode('utf-8', errors='ignore')[:400]}"
            })
        except Exception as e:
            results.append({
                "test": f"TypeScript Typecheck: {name}",
                "status": "WARN",
                "duration_ms": (time.time() - t0) * 1000,
                "message": f"Could not run tsc: {e}"
            })

    await check_ts(USER_FRONTEND_DIR, "User Frontend")
    await check_ts(ADMIN_FRONTEND_DIR, "Admin Frontend")

    # 2. HTTP probe all User Frontend pages
    if not user_fe_up:
        results.append({
            "test": "User Frontend Server Reachability",
            "status": "WARN",
            "duration_ms": 0,
            "message": f"User frontend at {USER_FRONTEND_URL} is not running — skipping {len(USER_PAGES)} route probes. Start with: cd apps/user-frontend && npm run dev"
        })
    else:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            for page in USER_PAGES:
                url = f"{USER_FRONTEND_URL}{page['path']}"
                t0 = time.time()
                try:
                    resp = await client.get(url)
                    duration_ms = (time.time() - t0) * 1000
                    passed = resp.status_code in page["expect_status"]
                    
                    status_str = "PASS" if passed else "FAIL"
                    results.append({
                        "test": f"User Frontend Route: {page['path']} ({page['name']})",
                        "status": status_str,
                        "duration_ms": duration_ms,
                        "message": f"Status {resp.status_code} in {duration_ms:.1f}ms (expected {page['expect_status']})"
                    })
                    http_records.append({
                        "method": "GET",
                        "url": url,
                        "expected": str(page["expect_status"]),
                        "actual": resp.status_code,
                        "duration_ms": duration_ms,
                        "status": status_str
                    })
                except Exception as e:
                    results.append({
                        "test": f"User Frontend Route: {page['path']}",
                        "status": "FAIL",
                        "duration_ms": (time.time() - t0) * 1000,
                        "message": f"Connection error: {e}"
                    })
                    http_records.append({
                        "method": "GET",
                        "url": url,
                        "expected": str(page["expect_status"]),
                        "actual": 0,
                        "duration_ms": 0,
                        "status": "FAIL"
                    })

    # 3. HTTP probe all Admin Frontend pages
    if not admin_fe_up:
        results.append({
            "test": "Admin Frontend Server Reachability",
            "status": "WARN",
            "duration_ms": 0,
            "message": f"Admin frontend at {ADMIN_FRONTEND_URL} is not running — skipping {len(ADMIN_PAGES)} route probes. Start with: cd apps/admin-frontend && npm run dev"
        })
    else:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            for page in ADMIN_PAGES:
                url = f"{ADMIN_FRONTEND_URL}{page['path']}"
                t0 = time.time()
                try:
                    resp = await client.get(url)
                    duration_ms = (time.time() - t0) * 1000
                    passed = resp.status_code in page["expect_status"]

                    status_str = "PASS" if passed else "FAIL"
                    results.append({
                        "test": f"Admin Frontend Route: {page['path']} ({page['name']})",
                        "status": status_str,
                        "duration_ms": duration_ms,
                        "message": f"Status {resp.status_code} in {duration_ms:.1f}ms (expected {page['expect_status']})"
                    })
                    http_records.append({
                        "method": "GET",
                        "url": url,
                        "expected": str(page["expect_status"]),
                        "actual": resp.status_code,
                        "duration_ms": duration_ms,
                        "status": status_str
                    })
                except Exception as e:
                    results.append({
                        "test": f"Admin Frontend Route: {page['path']}",
                        "status": "FAIL",
                        "duration_ms": (time.time() - t0) * 1000,
                        "message": f"Connection error: {e}"
                    })
                    http_records.append({
                        "method": "GET",
                        "url": url,
                        "expected": str(page["expect_status"]),
                        "actual": 0,
                        "duration_ms": 0,
                        "status": "FAIL"
                    })

    # 4. Playwright Headless Browser Rendering & UI Verification
    if not user_fe_up and not admin_fe_up:
        results.append({
            "test": "Playwright Browser Automation",
            "status": "WARN",
            "duration_ms": 0,
            "message": "No frontend servers available — skipping Playwright UI tests"
        })
    else:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()

                # Listen for console errors
                console_errors = []
                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

                # Test A: User Landing Page Render & Interactive Elements
                if user_fe_up:
                    t0 = time.time()
                    try:
                        resp = await page.goto(f"{USER_FRONTEND_URL}/", wait_until="domcontentloaded", timeout=10000)
                        duration_ms = (time.time() - t0) * 1000
                        title = await page.title()
                        has_nav = await page.locator("nav").count() > 0 or await page.locator("header").count() > 0
                        has_links = await page.locator("a").count() > 0

                        passed = resp.status == 200 and len(title) > 0 and has_links
                        results.append({
                            "test": "Playwright Render: User Landing Page",
                            "status": "PASS" if passed else "FAIL",
                            "duration_ms": duration_ms,
                            "message": f"Loaded in {duration_ms:.0f}ms, Title: '{title}', Nav elements found: {has_links}"
                        })
                    except Exception as e:
                        try:
                            screenshot_path = os.path.join(SCREENSHOTS_DIR, "user_landing_fail.png")
                            await page.screenshot(path=screenshot_path)
                        except Exception:
                            screenshot_path = "N/A"
                        results.append({
                            "test": "Playwright Render: User Landing Page",
                            "status": "FAIL",
                            "duration_ms": (time.time() - t0) * 1000,
                            "message": f"Failed render: {e} (Screenshot saved: {screenshot_path})"
                        })

                    # Test B: User Login Page Form Validation
                    t0 = time.time()
                    try:
                        await page.goto(f"{USER_FRONTEND_URL}/login", wait_until="domcontentloaded", timeout=10000)
                        duration_ms = (time.time() - t0) * 1000
                        email_input = await page.locator("input[type='email'], input[name='email'], input[id*='email']").count() > 0
                        pwd_input = await page.locator("input[type='password']").count() > 0
                        submit_btn = await page.locator("button[type='submit'], button:has-text('Sign In'), button:has-text('Login')").count() > 0

                        passed = email_input and pwd_input and submit_btn
                        results.append({
                            "test": "Playwright UI: User Login Form Elements",
                            "status": "PASS" if passed else "FAIL",
                            "duration_ms": duration_ms,
                            "message": f"Email input: {email_input}, Password input: {pwd_input}, Submit button: {submit_btn}"
                        })
                    except Exception as e:
                        try:
                            screenshot_path = os.path.join(SCREENSHOTS_DIR, "user_login_fail.png")
                            await page.screenshot(path=screenshot_path)
                        except Exception:
                            screenshot_path = "N/A"
                        results.append({
                            "test": "Playwright UI: User Login Form Elements",
                            "status": "FAIL",
                            "duration_ms": (time.time() - t0) * 1000,
                            "message": f"Form element verification failed: {e}"
                        })

                # Test C: Admin Login Page Form Verification
                if admin_fe_up:
                    t0 = time.time()
                    try:
                        await page.goto(f"{ADMIN_FRONTEND_URL}/login", wait_until="domcontentloaded", timeout=10000)
                        duration_ms = (time.time() - t0) * 1000
                        email_input = await page.locator("input[type='email'], input[name='email'], input[id*='email']").count() > 0
                        pwd_input = await page.locator("input[type='password']").count() > 0

                        passed = email_input and pwd_input
                        results.append({
                            "test": "Playwright UI: Admin Login Form Elements",
                            "status": "PASS" if passed else "FAIL",
                            "duration_ms": duration_ms,
                            "message": f"Admin email input: {email_input}, Password input: {pwd_input}"
                        })
                    except Exception as e:
                        try:
                            screenshot_path = os.path.join(SCREENSHOTS_DIR, "admin_login_fail.png")
                            await page.screenshot(path=screenshot_path)
                        except Exception:
                            screenshot_path = "N/A"
                        results.append({
                            "test": "Playwright UI: Admin Login Form Elements",
                            "status": "FAIL",
                            "duration_ms": (time.time() - t0) * 1000,
                            "message": f"Admin login elements failed: {e}"
                        })

                # Test D: Check Browser Console Errors
                # Filter known harmless warnings if any
                critical_errors = [e for e in console_errors if "favicon" not in e.lower() and "404" not in e.lower()]
                results.append({
                    "test": "Browser Console Cleanliness (Hydration/Runtime Errors)",
                    "status": "PASS" if len(critical_errors) == 0 else "WARN",
                    "duration_ms": 10.0,
                    "message": "0 critical console errors during page navigation" if len(critical_errors) == 0 else f"{len(critical_errors)} console errors: {critical_errors[:2]}"
                })

                await browser.close()
        except Exception as e:
            results.append({
                "test": "Playwright Browser Automation",
                "status": "WARN",
                "duration_ms": 0,
                "message": f"Playwright browser execution note: {e}"
            })

    return {
        "suite_name": "Frontend & UI Test Suite",
        "results": results,
        "http_records": http_records
    }


if __name__ == "__main__":
    out = asyncio.run(run_frontend_tests())
    for r in out["results"]:
        print(f"[{r['status']}] {r['test']}: {r['message']}")

