#!/usr/bin/env python
"""
College Chatbot Platform Management & Test Automation CLI.

Available Test Commands:
  python manage.py test-all          - Run full application test suite
  python manage.py test-frontend     - Test frontend routes, Next.js pages & UI
  python manage.py test-backend      - Test backend services, models & unit tests
  python manage.py test-api          - Test API endpoints and HTTP status codes
  python manage.py test-database     - Test database engine, RLS policies & isolation
  python manage.py test-auth         - Test authentication, JWT tokens & RBAC permissions
  python manage.py test-security     - Test security controls (SSRF, XSS, SQLi, headers)
  python manage.py test-integration  - Test end-to-end multi-tenant workflows
  python manage.py test-performance  - Benchmark latency, throughput & host telemetry
  python manage.py test-regression   - Check against performance and stability baseline
  python manage.py test-coverage     - Measure statement code coverage
  python manage.py test-failed       - Retest only previously failing tests
"""

import sys
import argparse
from pathlib import Path

# Set up project path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.runner import main as run_tests


VALID_COMMANDS = {
    "test-all": "Execute the complete end-to-end application test suite",
    "test-frontend": "Test frontend routes, Next.js rendering, and Playwright UI",
    "test-backend": "Test backend services, models, and pytest unit suite",
    "test-api": "Test all API endpoints and validate HTTP status codes",
    "test-database": "Test database connections, RLS policies, and multi-tenant isolation",
    "test-auth": "Test authentication, password hashing, JWT, and RBAC authorization",
    "test-security": "Test security defenses: SSRF, XSS, SQLi, uploads, and headers",
    "test-integration": "Test end-to-end user journeys across Student, Admin, SuperAdmin",
    "test-performance": "Benchmark latency thresholds, round-trips, and CPU/RAM load",
    "test-regression": "Detect regression in test outcomes or latency against baseline",
    "test-coverage": "Calculate code statement coverage across backend codebase",
    "test-failed": "Re-execute tests that failed in the preceding test run",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python manage.py",
        description="College Chatbot Master Management & Automated Testing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python manage.py test-all\n"
               "  python manage.py test-api\n"
               "  python manage.py test-security\n"
               "  python manage.py test-database\n"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="test-all",
        help="Command to execute (e.g. test-all, test-frontend, test-backend, test-database, etc.)"
    )
    return parser


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        parser = build_parser()
        parser.print_help()
        print("\nSupported Commands:")
        for cmd, desc in VALID_COMMANDS.items():
            print(f"  {cmd:<20} {desc}")
        sys.exit(0)

    command = sys.argv[1] if len(sys.argv) > 1 else "test-all"

    if command not in VALID_COMMANDS:
        print(f"[!] Unknown command '{command}'.")
        print("Supported commands are:")
        for cmd in VALID_COMMANDS:
            print(f"  - {cmd}")
        print("\nRun 'python manage.py --help' for details.")
        sys.exit(1)

    exit_code = run_tests(command)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

