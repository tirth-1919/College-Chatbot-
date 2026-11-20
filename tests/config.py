"""Test Automation Configuration & Safety Verification Module.

Enforces strict safety boundaries:
  - Strictly requires isolated test configuration (.env.test.local).
  - Validates target database before write tests.
  - Ensures production records and hosted databases are NEVER targeted.
  - Enforces loopback-only connection guards on 127.0.0.1:54322.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

# Ensure backend root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ---------------------------------------------------------------------------
# Strict Isolated Environment Loading (Fail-Closed)
# ---------------------------------------------------------------------------
TEST_ENV_FILE = ROOT_DIR / ".env.test.local"
if not TEST_ENV_FILE.is_file():
    raise RuntimeError(
        f"FATAL: Required isolated test configuration '{TEST_ENV_FILE}' not found. "
        "Testing aborted to prevent fallback to production or hosted database configuration."
    )

# Purge pre-existing connection variables to prevent environment bleed
os.environ.pop("DATABASE_URL", None)
os.environ.pop("DATABASE_APP_ROLE_URL", None)
os.environ.pop("REDIS_URL", None)

# Load strictly from isolated test configuration with override=True
load_dotenv(TEST_ENV_FILE, override=True)

# ---------------------------------------------------------------------------
# Hardened Fail-Closed Database Connection Validation
# ---------------------------------------------------------------------------
PERMITTED_SCHEMES = {"postgresql+asyncpg", "postgresql"}
PERMITTED_HOST = "127.0.0.1"
PERMITTED_DB_PORT = 54322
PERMITTED_DB_NAME = "postgres"
EXPECTED_TEST_USERS = {"college_app_user", "postgres"}
EXPECTED_TEST_PASSWORDS = {"DISPOSABLE_LOCAL_APP_PASSWORD", "DISPOSABLE_LOCAL_DEV_PASSWORD"}
PROHIBITED_CLOUD_DOMAINS = ("supabase.co", "pooler.supabase.com", "aws.com", "rds.amazonaws.com")


def assert_disposable_loopback_target(url: str, expected_user: Optional[str] = None) -> None:
    """Enforces strict fail-closed connection boundaries for test execution.
    
    Validates:
      - Clean URL parsing without exception or credential leakage
      - Driver scheme strictly in ('postgresql+asyncpg', 'postgresql')
      - Host strictly IPv4 literal '127.0.0.1' (localhost forbidden)
      - Port strictly 54322
      - Database strictly 'postgres'
      - User and password strictly match disposable local test fixtures
      - Rejects query parameters, multiple comma-separated hosts, and cloud domains.
    """
    if not url or not isinstance(url, str) or not url.strip():
        raise RuntimeError("FATAL: Database connection URL is empty or malformed. Test execution aborted.")

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        raise RuntimeError(f"FATAL: Database connection URL parsing failed: {exc}. Execution terminated.") from exc

    # 1. Driver Scheme Validation
    if parsed.scheme not in PERMITTED_SCHEMES:
        raise RuntimeError(
            f"FATAL: Prohibited driver scheme '{parsed.scheme}'. Only {PERMITTED_SCHEMES} permitted."
        )

    # 2. Hostname Validation (Strict IPv4 loopback literal)
    if parsed.hostname != PERMITTED_HOST:
        raise RuntimeError(
            f"FATAL: Prohibited database host '{parsed.hostname}'. "
            f"Tests strictly require literal '{PERMITTED_HOST}'. 'localhost' and external hosts are forbidden."
        )

    # 3. Port Validation
    if parsed.port != PERMITTED_DB_PORT:
        raise RuntimeError(
            f"FATAL: Prohibited port '{parsed.port}'. Disposable test stack must run on {PERMITTED_DB_PORT}."
        )

    # 4. Database Name Validation
    db_name = (parsed.path or "").lstrip("/")
    if db_name != PERMITTED_DB_NAME:
        raise RuntimeError(
            f"FATAL: Prohibited database '{db_name}'. Expected disposable database '{PERMITTED_DB_NAME}'."
        )

    # 5. Credentials Validation
    username = parsed.username
    password = parsed.password
    if username not in EXPECTED_TEST_USERS:
        raise RuntimeError(f"FATAL: Prohibited test user '{username}'. Only disposable test principals permitted.")
    if expected_user and username != expected_user:
        raise RuntimeError(f"FATAL: Expected database user '{expected_user}', found '{username}'.")
    if password not in EXPECTED_TEST_PASSWORDS:
        raise RuntimeError("FATAL: Unrecognized database password. Production credentials strictly forbidden.")

    # 6. Query Parameter & Multiple Host Rejection
    if parsed.query:
        raise RuntimeError(f"FATAL: Prohibited query parameters detected in test connection URL: '{parsed.query}'.")
    if "," in (parsed.netloc or ""):
        raise RuntimeError("FATAL: Multiple hosts detected in connection URL. Routing ambiguity forbidden.")

    # 7. Hosted Supabase & Cloud Rejection
    raw_lower = url.lower()
    if any(cloud in raw_lower for cloud in PROHIBITED_CLOUD_DOMAINS):
        raise RuntimeError("FATAL: Hosted cloud Supabase or cloud endpoint detected! Execution terminated.")


def assert_disposable_redis_target(url: str) -> None:
    """Enforces strict fail-closed loopback boundaries for test Redis instance."""
    if not url:
        return
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("redis", "rediss"):
        raise RuntimeError(f"FATAL: Prohibited Redis scheme '{parsed.scheme}'.")
    if parsed.hostname != PERMITTED_HOST:
        raise RuntimeError(f"FATAL: Prohibited Redis host '{parsed.hostname}'. Expected '{PERMITTED_HOST}'.")
    if parsed.port != 63799:
        raise RuntimeError(f"FATAL: Prohibited Redis port '{parsed.port}'. Expected 63799.")


# ---------------------------------------------------------------------------
# Database URIs & Immediate Import-Time Guard Enforcement
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASE_APP_ROLE_URL = os.environ.get("DATABASE_APP_ROLE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")

# Immediate validation: fails module import if targets are not compliant
assert_disposable_loopback_target(DATABASE_URL, expected_user="postgres")
assert_disposable_loopback_target(DATABASE_APP_ROLE_URL, expected_user="college_app_user")
assert_disposable_redis_target(REDIS_URL)

# Backend application settings must never inherit the test-only admin URL.
os.environ["DATABASE_URL"] = DATABASE_APP_ROLE_URL

# Sync / asyncpg converted URIs
ASYNC_APP_URL = DATABASE_APP_ROLE_URL
ASYNC_ADMIN_URL = DATABASE_URL
SYNC_ADMIN_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
SYNC_APP_URL = DATABASE_APP_ROLE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

# Known demo tenant & user UUIDs from database seed
AIT_COLLEGE_ID = "11111111-1111-1111-1111-111111111111"
RCTI_COLLEGE_ID = "22222222-2222-2222-2222-222222222222"

SUPER_ADMIN_EMAIL = "campusai-test-superadmin@example.com"
COLLEGE_ADMIN_EMAIL = "campusai-test-college-admin@example.com"
STUDENT_EMAIL = "campusai-test-student@example.com"
DEFAULT_PASSWORD = "Admin@12345"

# ---------------------------------------------------------------------------
# Server Base URLs
# ---------------------------------------------------------------------------
BACKEND_BASE_URL = os.environ.get("TEST_BACKEND_URL", "http://127.0.0.1:8000")
USER_FRONTEND_URL = os.environ.get("TEST_USER_FRONTEND_URL", "http://127.0.0.1:3000")
ADMIN_FRONTEND_URL = os.environ.get("TEST_ADMIN_FRONTEND_URL", "http://127.0.0.1:3001")
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
    """Safety guard dynamically re-verifying database target before executing tests."""
    assert_disposable_loopback_target(DATABASE_URL, expected_user="postgres")
    assert_disposable_loopback_target(DATABASE_APP_ROLE_URL, expected_user="college_app_user")
    assert_disposable_redis_target(REDIS_URL)

    return {
        "status": "SAFE",
        "app_role_configured": "college_app_user" in DATABASE_APP_ROLE_URL,
        "target_host": PERMITTED_HOST,
        "target_port": PERMITTED_DB_PORT,
        "reports_dir": str(REPORTS_DIR),
        "backend_dir": str(BACKEND_DIR),
    }
