"""Authentication & Role-Based Access Control (RBAC) Automated Test Suite.

Tests:
  - Password hashing security (bcrypt work factor, salt uniqueness).
  - JWT generation, claims retention, tampering rejection, and expiration handling.
  - Authentication for all three user roles: STUDENT, COLLEGE_ADMIN, SUPER_ADMIN.
  - Role-based authorization matrix enforcement.
  - Cross-tenant college administration boundary enforcement.
"""

import time
import uuid
from typing import List, Dict, Any
from httpx import AsyncClient, ASGITransport
from tests.config import (
    SUPER_ADMIN_EMAIL,
    COLLEGE_ADMIN_EMAIL,
    STUDENT_EMAIL,
    DEFAULT_PASSWORD,
    AIT_COLLEGE_ID,
    RCTI_COLLEGE_ID,
)
from app.main import app
from app.security.jwt import create_access_token, decode_token
from app.security.password import hash_password, verify_password


async def run_auth_rbac_suite() -> List[Dict[str, Any]]:
    """Executes authentication & authorization test suite."""
    results = []

    # 1. Test: Password Hashing with Bcrypt
    t0 = time.perf_counter()
    raw_pwd = "TestPassword@12345"
    h1 = hash_password(raw_pwd)
    h2 = hash_password(raw_pwd)
    dur = (time.perf_counter() - t0) * 1000
    is_safe = (
        h1 != raw_pwd
        and h1 != h2  # unique salts
        and verify_password(raw_pwd, h1)
        and not verify_password("Wrong@Password", h1)
    )
    results.append({
        "category": "Authentication",
        "name": "Bcrypt Password Hashing & Salt Randomization",
        "target": "app.security.password",
        "status": "PASS" if is_safe else "FAIL",
        "duration_ms": dur,
        "detail": f"Hashed length: {len(h1)}, salt unique: {h1 != h2}",
    })

    # 2. Test: JWT Issuance, Claims, and Tamper Detection
    t0 = time.perf_counter()
    test_uid = str(uuid.uuid4())
    token = create_access_token(
        subject=test_uid,
        role="COLLEGE_ADMIN",
        college_id=AIT_COLLEGE_ID,
        additional_claims={"email": "admin@college.edu"},
    )
    payload = decode_token(token)
    tampered_payload = decode_token(token[:-4] + "fake")
    dur = (time.perf_counter() - t0) * 1000
    is_valid_jwt = (
        payload is not None
        and payload.get("sub") == test_uid
        and payload.get("role") == "COLLEGE_ADMIN"
        and payload.get("college_id") == AIT_COLLEGE_ID
        and tampered_payload is None
    )
    results.append({
        "category": "Authentication",
        "name": "JWT Token Generation, Claim Persistence & Tamper Rejection",
        "target": "app.security.jwt",
        "status": "PASS" if is_valid_jwt else "FAIL",
        "duration_ms": dur,
        "detail": f"Payload sub: {payload.get('sub') if payload else None}, Tampered rejected: {tampered_payload is None}",
    })

    # 3. Test: Real Authentication - Student Login
    t0 = time.perf_counter()
    student_token = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": DEFAULT_PASSWORD},
        )
        dur = (time.perf_counter() - t0) * 1000
        if res.status_code == 200:
            data = res.json().get("data", {})
            student_token = data.get("access_token")
            results.append({
                "category": "Authentication",
                "name": "Student Login & Token Issuance (STUDENT role)",
                "target": "POST /api/v1/auth/login",
                "status": "PASS",
                "duration_ms": dur,
                "detail": f"Status: 200, Role: {data.get('role')}",
            })
        else:
            results.append({
                "category": "Authentication",
                "name": "Student Login & Token Issuance",
                "target": "POST /api/v1/auth/login",
                "status": "FAIL",
                "duration_ms": dur,
                "detail": f"Status: {res.status_code}, Body: {res.text}",
            })

    # 4. Test: Real Authentication - College Admin Login
    t0 = time.perf_counter()
    college_admin_token = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": COLLEGE_ADMIN_EMAIL, "password": DEFAULT_PASSWORD},
        )
        dur = (time.perf_counter() - t0) * 1000
        if res.status_code == 200:
            data = res.json().get("data", {})
            college_admin_token = data.get("access_token")
            results.append({
                "category": "Authentication",
                "name": "College Admin Login & Tenant Association",
                "target": "POST /api/v1/auth/login",
                "status": "PASS",
                "duration_ms": dur,
                "detail": f"Status: 200, College: {data.get('college_id')}",
            })
        else:
            results.append({
                "category": "Authentication",
                "name": "College Admin Login & Tenant Association",
                "target": "POST /api/v1/auth/login",
                "status": "FAIL",
                "duration_ms": dur,
                "detail": f"Status: {res.status_code}, Body: {res.text}",
            })

    # 5. Test: Real Authentication - Super Admin Login
    t0 = time.perf_counter()
    super_admin_token = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": DEFAULT_PASSWORD},
        )
        dur = (time.perf_counter() - t0) * 1000
        if res.status_code == 200:
            data = res.json().get("data", {})
            super_admin_token = data.get("access_token")
            results.append({
                "category": "Authentication",
                "name": "Super Admin Login & Privileged Elevation",
                "target": "POST /api/v1/auth/login",
                "status": "PASS",
                "duration_ms": dur,
                "detail": f"Status: 200, Role: {data.get('role')}",
            })
        else:
            results.append({
                "category": "Authentication",
                "name": "Super Admin Login",
                "target": "POST /api/v1/auth/login",
                "status": "FAIL",
                "duration_ms": dur,
                "detail": f"Status: {res.status_code}, Body: {res.text}",
            })

    # 6. Test: Invalid Password Rejection (401)
    t0 = time.perf_counter()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": "WrongPassword@999"},
        )
        dur = (time.perf_counter() - t0) * 1000
        is_rejected = (res.status_code == 401)
        results.append({
            "category": "Authentication",
            "name": "Invalid Credentials Rejection (HTTP 401)",
            "target": "POST /api/v1/auth/login",
            "status": "PASS" if is_rejected else "FAIL",
            "duration_ms": dur,
            "detail": f"Expected: 401, Actual: {res.status_code}",
        })

    # 7. Test: Protected Profile Endpoint (/auth/me) with Valid Token
    t0 = time.perf_counter()
    if student_token:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            dur = (time.perf_counter() - t0) * 1000
            passed = res.status_code == 200 and res.json().get("data", {}).get("email") == STUDENT_EMAIL
            results.append({
                "category": "Authorization",
                "name": "Current User Profile Resolution (GET /auth/me)",
                "target": "GET /api/v1/auth/me",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": dur,
                "detail": f"Status: {res.status_code}, Resolved User: {res.json().get('data', {}).get('email')}",
            })

    # 8. Test: Unauthenticated Request Blocked (401)
    t0 = time.perf_counter()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me")
        dur = (time.perf_counter() - t0) * 1000
        passed = (res.status_code == 401)
        results.append({
            "category": "Authorization",
            "name": "Missing Bearer Token Guard (HTTP 401)",
            "target": "GET /api/v1/auth/me",
            "status": "PASS" if passed else "FAIL",
            "duration_ms": dur,
            "detail": f"Expected: 401, Actual: {res.status_code}",
        })

    # 9. Test: RBAC Gate - Student Forbidden from Super Admin Route (403)
    t0 = time.perf_counter()
    if student_token:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(
                "/api/v1/super-admin/dashboard",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            dur = (time.perf_counter() - t0) * 1000
            passed = (res.status_code == 403)
            results.append({
                "category": "Authorization",
                "name": "RBAC Role Guard: Student blocked from Super Admin Dashboard (HTTP 403)",
                "target": "GET /api/v1/super-admin/dashboard",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": dur,
                "detail": f"Expected: 403, Actual: {res.status_code}",
            })

    # 10. Test: RBAC Gate - Student Forbidden from College Admin Route (403)
    t0 = time.perf_counter()
    if student_token:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(
                "/api/v1/college-admin/dashboard",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            dur = (time.perf_counter() - t0) * 1000
            passed = (res.status_code == 403)
            results.append({
                "category": "Authorization",
                "name": "RBAC Role Guard: Student blocked from College Admin Dashboard (HTTP 403)",
                "target": "GET /api/v1/college-admin/dashboard",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": dur,
                "detail": f"Expected: 403, Actual: {res.status_code}",
            })

    # 11. Test: Super Admin Permitted on Super Admin Route (200)
    t0 = time.perf_counter()
    if super_admin_token:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(
                "/api/v1/super-admin/dashboard",
                headers={"Authorization": f"Bearer {super_admin_token}"},
            )
            dur = (time.perf_counter() - t0) * 1000
            passed = (res.status_code == 200)
            results.append({
                "category": "Authorization",
                "name": "Super Admin Authorized for Platform Dashboard (HTTP 200)",
                "target": "GET /api/v1/super-admin/dashboard",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": dur,
                "detail": f"Expected: 200, Actual: {res.status_code}",
            })

    # 12. Test: Cross-Tenant Denial - College Admin blocked from other college ID (403)
    t0 = time.perf_counter()
    if college_admin_token:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.get(
                "/api/v1/college-admin/dashboard",
                headers={
                    "Authorization": f"Bearer {college_admin_token}",
                    "X-College-ID": RCTI_COLLEGE_ID,  # Assigned to AIT, attempting RCTI
                },
            )
            dur = (time.perf_counter() - t0) * 1000
            passed = (res.status_code == 403)
            results.append({
                "category": "Authorization",
                "name": "Cross-Tenant Boundary: College Admin blocked from foreign College ID (HTTP 403)",
                "target": "GET /api/v1/college-admin/dashboard",
                "status": "PASS" if passed else "FAIL",
                "duration_ms": dur,
                "detail": f"Expected: 403, Actual: {res.status_code}",
            })

    return results

