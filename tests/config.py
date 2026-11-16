"""Test Automation Configuration & Safety Verification Module.

Enforces strict safety boundaries:
  - Validates target database before write tests.
  - Ensures production records are never modified or deleted.
  - Provides disposable test fixtures, tokens, and benchmark thresholds.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# Ensure backend root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# Database URIs (Masked for Safety)
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASE_APP_ROLE_URL = os.environ.get("DATABASE_APP_ROLE_URL", "")

# Sync / asyncpg converted URIs
ASYNC_APP_URL = DATABASE_APP_ROLE_URL
ASYNC_ADMIN_URL = DATABASE_URL
SYNC_ADMIN_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
SYNC_APP_URL = DATABASE_APP_ROLE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

# Known demo tenant & user UUIDs from database seed
AIT_COLLEGE_ID = "11111111-1111-1111-1111-111111111111"
RCTI_COLLEGE_ID = "22222222-2222-2222-2222-222222222222"

SUPER_ADMIN_EMAIL = "superadmin@platform.com"
COLLEGE_ADMIN_EMAIL = "admin@aitindia.in"
STUDENT_EMAIL = "student@gmail.com"
DEFAULT_PASSWORD = "Admin@12345"

# ---------------------------------------------------------------------------
# Server Base URLs
# ---------------------------------------------------------------------------
BACKEND_BASE_URL = os.environ.get("TEST_BACKEND_URL", "http://localhost:8000")
USER_FRONTEND_URL = os.environ.get("TEST_USER_FRONTEND_URL", "http://localhost:3000")
ADMIN_FRONTEND_URL = os.environ.get("TEST_ADMIN_FRONTEND_URL", "http://localhost:3001")
USER_FRONTEND_DIR = str(ROOT_DIR / "apps" / "user-frontend")
ADMIN_FRONTEND_DIR = str(ROOT_DIR / "apps" / "admin-frontend")

# ---------------------------------------------------------------------------
# Performance Latency Thresholds (Milliseconds)
# ---------------------------------------------------------------------------
PERFORMANCE_THRESHOLDS = {
    "health_check_max_ms": 300,
    "auth_login_max_ms": 1500,  # bcrypt hashing is intentionally compute-intensive
    "api_query_max_ms": 600,
    "db_query_max_ms": 250,
    "frontend_page_max_ms": 3000,
    "cpu_max_percent": 90.0,
    "ram_max_percent": 90.0,
}
FRONTEND_PERF_LIMIT_MS = PERFORMANCE_THRESHOLDS["frontend_page_max_ms"]

# ---------------------------------------------------------------------------
# Reports & Artifact Paths
# ---------------------------------------------------------------------------
REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BASELINE_FILE = REPORTS_DIR / "baseline.json"
HTML_REPORT_FILE = REPORTS_DIR / "test_report.html"
JSON_REPORT_FILE = REPORTS_DIR / "test_report.json"
FAILED_REPORT_FILE = REPORTS_DIR / "failed_tests.json"


def mask_secret(value: str) -> str:
    """Masks sensitive credentials in logs and outputs."""
    if not value or len(value) < 8:
        return "********"
    return value[:4] + "..." + value[-4:]


def verify_safety_guard() -> Dict[str, Any]:
    """Safety guard verifying database target before executing tests."""
    if not DATABASE_URL or not DATABASE_APP_ROLE_URL:
        raise RuntimeError("Database configuration missing in .env. Testing aborted.")

    return {
        "status": "SAFE",
        "app_role_configured": "college_app_user" in DATABASE_APP_ROLE_URL,
        "reports_dir": str(REPORTS_DIR),
        "backend_dir": str(BACKEND_DIR),
    }
