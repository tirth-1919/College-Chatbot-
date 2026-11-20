"""Provision isolated authentication fixtures for the automated API suites."""

import uuid

import asyncpg
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.middleware.rate_limit import rate_limiter
from app.security.password import hash_password
from tests.config import (
    ASYNC_ADMIN_URL,
    AIT_COLLEGE_ID,
    COLLEGE_ADMIN_EMAIL,
    DEFAULT_PASSWORD,
    STUDENT_EMAIL,
    SUPER_ADMIN_EMAIL,
    verify_safety_guard,
)


class TestFixtureError(RuntimeError):
    """Raised when an isolated test identity cannot be prepared safely."""


async def _ensure_super_admin_fixture() -> None:
    if settings.ENVIRONMENT.strip().lower() != "test":
        raise TestFixtureError("Super Admin fixture setup is restricted to ENVIRONMENT=test.")
    if verify_safety_guard().get("status") != "SAFE":
        raise TestFixtureError("The isolated database safety guard did not confirm SAFE.")

    connection = await asyncpg.connect(
        ASYNC_ADMIN_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    )
    try:
        identity = await connection.fetchrow(
            "SELECT current_database() AS database_name, current_user AS role_name"
        )
        if identity["database_name"] != "postgres" or identity["role_name"] != "postgres":
            raise TestFixtureError("Super Admin fixture setup reached an unexpected database identity.")

        await connection.execute(
            """
            INSERT INTO users (id, email, hashed_password, full_name, role, is_verified, is_active)
            VALUES ($1, $2, $3, $4, 'SUPER_ADMIN', TRUE, TRUE)
            ON CONFLICT (email) DO NOTHING
            """,
            uuid.uuid4(),
            SUPER_ADMIN_EMAIL,
            hash_password(DEFAULT_PASSWORD),
            "Isolated Test Super Admin",
        )
        fixture = await connection.fetchrow(
            "SELECT role FROM users WHERE email = $1",
            SUPER_ADMIN_EMAIL,
        )
        if not fixture or fixture["role"] != "SUPER_ADMIN":
            raise TestFixtureError("The dedicated Super Admin fixture conflicts with an existing account.")
    finally:
        await connection.close()


async def _register_or_authenticate(
    client: AsyncClient,
    email: str,
    full_name: str,
    allowed_roles: set[str],
) -> str:
    registration = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": DEFAULT_PASSWORD, "full_name": full_name},
    )
    if registration.status_code == 201:
        data = registration.json().get("data", {})
        if data.get("role") != "STUDENT":
            raise TestFixtureError("Public registration returned an unexpected role.")
        return data["user_id"]
    if registration.status_code != 400:
        raise TestFixtureError(
            f"Could not register a dedicated test identity (HTTP {registration.status_code})."
        )

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    data = login.json().get("data", {}) if login.status_code == 200 else {}
    if login.status_code != 200 or data.get("role") not in allowed_roles:
        raise TestFixtureError(
            f"An existing dedicated test identity could not authenticate with its expected role (HTTP {login.status_code})."
        )
    return data["user_id"]


async def _ensure_membership(
    client: AsyncClient,
    headers: dict[str, str],
    user_id: str,
    role_in_college: str,
) -> None:
    response = await client.get(
        f"/api/v1/memberships/college/{AIT_COLLEGE_ID}",
        headers=headers,
    )
    if response.status_code != 200:
        raise TestFixtureError(
            f"Could not inspect AIT test memberships (HTTP {response.status_code})."
        )

    memberships = response.json().get("data", [])
    existing = next(
        (membership for membership in memberships if membership.get("user_id") == user_id),
        None,
    )
    if existing:
        if existing.get("role_in_college") != role_in_college:
            raise TestFixtureError("A dedicated test identity has an unexpected AIT membership.")
        return

    created = await client.post(
        "/api/v1/memberships",
        headers=headers,
        json={
            "college_id": AIT_COLLEGE_ID,
            "user_id": user_id,
            "role_in_college": role_in_college,
        },
    )
    data = created.json().get("data", {}) if created.status_code == 201 else {}
    if (
        created.status_code != 201
        or data.get("user_id") != user_id
        or data.get("role_in_college") != role_in_college
    ):
        raise TestFixtureError(
            f"Could not create the least-privilege AIT test membership (HTTP {created.status_code})."
        )


async def provision_test_accounts() -> None:
    """Create missing synthetic identities without changing existing accounts."""
    await _ensure_super_admin_fixture()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        super_admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": SUPER_ADMIN_EMAIL, "password": DEFAULT_PASSWORD},
        )
        if super_admin_login.status_code != 200:
            raise TestFixtureError(
                f"The isolated Super Admin fixture could not authenticate (HTTP {super_admin_login.status_code})."
            )
        super_admin_data = super_admin_login.json().get("data", {})
        if super_admin_data.get("role") != "SUPER_ADMIN":
            raise TestFixtureError("The isolated Super Admin fixture has an unexpected role.")
        headers = {"Authorization": f"Bearer {super_admin_data['access_token']}"}

        student_id = await _register_or_authenticate(
            client,
            STUDENT_EMAIL,
            "Isolated AIT Test Student",
            {"STUDENT"},
        )
        admin_id = await _register_or_authenticate(
            client,
            COLLEGE_ADMIN_EMAIL,
            "Isolated AIT Test College Admin",
            {"STUDENT", "COLLEGE_ADMIN"},
        )

        await _ensure_membership(client, headers, student_id, "VIEWER")
        await _ensure_membership(client, headers, admin_id, "ADMIN")

        for email, expected_role in (
            (STUDENT_EMAIL, "STUDENT"),
            (COLLEGE_ADMIN_EMAIL, "COLLEGE_ADMIN"),
        ):
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": DEFAULT_PASSWORD},
            )
            data = login.json().get("data", {}) if login.status_code == 200 else {}
            if login.status_code != 200 or data.get("role") != expected_role:
                raise TestFixtureError(
                    f"A dedicated test identity did not retain its expected role (HTTP {login.status_code})."
                )

    rate_limiter.reset()
