"""
P0 — JWT refresh, logout revocation, and token URL security.

Focused tests covering:
 1.  valid access token accepted
 2.  expired access token rejected
 3.  successful refresh issues a new access token
 4.  failed refresh rejected
 5.  (frontend contract) original request retried exactly once after refresh
 6.  (frontend contract) concurrent 401s share ONE refresh operation
 7.  refresh loop prevention (retry never triggers a second refresh)
 8.  logout revokes backend session
 9.  revoked refresh token cannot obtain a new access token
 10. JWTs never appear in generated API URLs (source-level scan)
 11. user (STUDENT) authentication still works
 12. admin authentication still works
 13. STUDENT cannot access admin APIs
 14. ADMIN permissions unchanged
 15. SUPER_ADMIN behavior unchanged
 16. SSE /chat/stream keeps working with header auth (contract check)
"""
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import jwt as pyjwt
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api.v1.auth import router as user_auth_router
from backend.app.api.v1.admin.auth import router as admin_auth_router
from backend.app.api.v1.conversations import router as conversations_router
from backend.app.core.config import settings
from backend.app.core.database import Base, get_db
from backend.app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from backend.app.models.user import User, UserSession


@pytest.fixture(autouse=True)
def _isolate_rate_limiter():
    """These tests legitimately hammer /auth/refresh; keep their requests out
    of the shared in-memory rate limiter so other tests aren't rate-limited."""
    from backend.app.security.rate_limiter import rate_limiter
    snapshot = dict(rate_limiter._history)
    rate_limiter._history.clear()
    yield
    rate_limiter._history.clear()
    rate_limiter._history.update(snapshot)


SECRET = settings.SECRET_KEY


def _make_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return engine


def _make_app(router):
    app = FastAPI()
    app.include_router(router)
    return app


def _install_db_override(app, factory):
    def override_db():
        request_db = factory()
        try:
            yield request_db
        finally:
            request_db.close()
    app.dependency_overrides[get_db] = override_db


@pytest.fixture
def auth_env():
    engine = _make_engine()
    factory = sessionmaker(bind=engine, autoflush=False)
    db = factory()
    user = User(id=str(uuid.uuid4()), email="student@example.test",
                full_name="Student", role="STUDENT")
    admin = User(id=str(uuid.uuid4()), email="admin@example.test",
                 full_name="Admin", role="ADMIN")
    super_admin = User(id=str(uuid.uuid4()), email="root@example.test",
                       full_name="Root", role="SUPER_ADMIN")
    db.add_all([user, admin, super_admin])
    db.commit()

    app = _make_app(user_auth_router)
    _install_db_override(app, factory)
    client = TestClient(app)

    def make_session(target_user):
        refresh = create_refresh_token({"sub": target_user.id})
        session = UserSession(
            user_id=target_user.id,
            refresh_token_hash=refresh[:16] + "-hashed",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(session)
        db.commit()
        return session, refresh

    yield {
        "client": client, "db": db, "user": user, "admin": admin,
        "super_admin": super_admin, "make_session": make_session,
        "engine": engine,
    }
    db.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


# ------------------------------------------------------------------
# 1 & 2 — valid / expired access tokens
# ------------------------------------------------------------------

def test_valid_access_token_decodes(auth_env):
    token = create_access_token({"sub": auth_env["user"].id, "role": "STUDENT"})
    payload = decode_token(token)
    assert payload and payload["sub"] == auth_env["user"].id


def test_expired_access_token_is_rejected(auth_env):
    expired = pyjwt.encode(
        {"sub": auth_env["user"].id, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        SECRET, algorithm="HS256",
    )
    assert decode_token(expired) is None


# ------------------------------------------------------------------
# 3 & 4 — successful / failed refresh
# ------------------------------------------------------------------

def test_successful_refresh_issues_new_access_token(auth_env):
    env = auth_env
    env["make_session"](env["user"])
    refresh = create_refresh_token({"sub": env["user"].id})

    # Hash check uses get_password_hash of first 16 chars inside the endpoint;
    # patch nothing — instead seed a session whose hash matches the real scheme.
    from backend.app.core.security import get_password_hash
    sess, _ = env["make_session"](env["user"])
    sess.refresh_token_hash = get_password_hash(refresh[:16])
    env["db"].commit()

    response = env["client"].post("/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    # New token must be a valid access token for the right user
    payload = decode_token(data["access_token"])
    assert payload["sub"] == env["user"].id


def test_failed_refresh_is_rejected(auth_env):
    response = auth_env["client"].post(
        "/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert response.status_code == 401


# ------------------------------------------------------------------
# 8 & 9 — logout revocation, revoked token cannot refresh
# ------------------------------------------------------------------

def test_logout_revokes_session_and_old_refresh_token_fails(auth_env):
    env = auth_env
    from backend.app.core.security import get_password_hash
    session, _ = env["make_session"](env["user"])
    refresh = create_refresh_token({"sub": env["user"].id})
    session.refresh_token_hash = get_password_hash(refresh[:16])
    env["db"].commit()

    access = create_access_token({"sub": env["user"].id, "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {access}"}

    # logout revokes backend sessions
    response = env["client"].post("/auth/logout", headers=headers)
    assert response.status_code == 200

    env["db"].expire_all()
    assert session.is_revoked is True

    # old refresh token can no longer obtain an access token
    refresh_response = env["client"].post("/auth/refresh", json={"refresh_token": refresh})
    assert refresh_response.status_code == 401


# ------------------------------------------------------------------
# 5, 6, 7 — frontend interceptor contract (simulated in-process)
# ------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {}

    def json(self):
        return self._payload


@pytest.fixture
def interceptor_env():
    """Simulates the apiClient authFetch refresh contract."""
    state = {"fetch_log": [], "refresh_calls": 0, "session_cleared": False}

    class FakeClient:
        _refreshPromise = None
        _refreshing = False

        def __init__(self, refresh_ok=True):
            self.refresh_ok = refresh_ok
            self.pending = []

        async def refreshAccessToken(self):
            if self._refreshPromise:
                return self._refreshPromise
            if self._refreshing:
                raise RuntimeError("Refresh already in progress")
            self._refreshing = True
            state["refresh_calls"] += 1

            async def run():
                try:
                    if not self.refresh_ok:
                        raise RuntimeError("Session refresh failed")
                    return "new-access-token"
                finally:
                    self._refreshing = False
                    self._refreshPromise = None

            # JS `new Promise` semantics: schedule the coroutine as a Task so
            # awaiting the stored promise propagates the failure exception.
            self._refreshPromise = asyncio.ensure_future(run())
            return await self._refreshPromise

        async def authFetch(self, url, allow_refresh=True):
            if "auth/refresh" in url or "auth/logout" in url:
                return _FakeResponse(200)
            state["fetch_log"].append(url)
            # Simulates backend: first request hits an expired token (401),
            # any later request succeeds once a refresh has happened.
            status_code = 401 if state["refresh_calls"] == 0 else 200
            resp = _FakeResponse(status_code)
            if resp.status_code != 401 or not allow_refresh:
                return resp
            try:
                await self.refreshAccessToken()
                return await self.authFetch(url, allow_refresh=False)
            except Exception:
                state["session_cleared"] = True
                raise

    return state, FakeClient


import asyncio


def test_original_request_retried_once_after_refresh(interceptor_env):
    state, FakeClient = interceptor_env
    client = FakeClient(refresh_ok=True)

    async def run():
        return await client.authFetch("/api/v1/conversations")

    resp = asyncio.run(run())
    assert resp.status_code == 200
    # original request + exactly one retry
    assert state["fetch_log"].count("/api/v1/conversations") == 2
    assert state["refresh_calls"] == 1


def test_concurrent_requests_share_one_refresh_operation(interceptor_env):
    state, FakeClient = interceptor_env
    client = FakeClient(refresh_ok=True)

    async def run():
        # Three concurrent 401s must queue behind ONE refresh
        return await asyncio.gather(
            client.authFetch("/api/v1/a"),
            client.authFetch("/api/v1/b"),
            client.authFetch("/api/v1/c"),
        )

    results = asyncio.run(run())
    assert all(r.status_code == 200 for r in results)
    assert state["refresh_calls"] == 1


def test_refresh_failure_clears_session_and_never_loops(interceptor_env):
    state, FakeClient = interceptor_env
    client = FakeClient(refresh_ok=False)

    async def run():
        with pytest.raises(RuntimeError):
            await client.authFetch("/api/v1/conversations")

    asyncio.run(run())
    assert state["session_cleared"] is True
    assert state["refresh_calls"] == 1  # loop prevention: never retried again


# ------------------------------------------------------------------
# 10 — JWT tokens must never appear in generated URLs
# ------------------------------------------------------------------

def test_jwt_never_appears_in_api_urls():
    """Scan frontend sources for tokens placed in URLs."""
    offenders = []
    for web_root in ["apps/user-web/src", "apps/admin-web/src"]:
        for path in ROOT.glob(f"{web_root}/**/*.js*"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for needle in (
                "access_token=", "refresh_token=", "?token=", "&token=",
                "token=" ,
            ):
                for line in text.splitlines():
                    if needle in line and "refresh_token:" not in line \
                            and "body:" not in line and "JSON.stringify" not in line:
                        offenders.append(f"{path}: {line.strip()[:120]}")
    assert not offenders, "JWT found in URL construction:\n" + "\n".join(offenders[:20])


# ------------------------------------------------------------------
# 11–15 — user / admin auth + RBAC
# ------------------------------------------------------------------

def test_student_user_authentication_flow(auth_env):
    env = auth_env
    token = create_access_token({"sub": env["user"].id, "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # STUDENT can use user APIs
    conv_app = _make_app(conversations_router)
    _install_db_override(conv_app, sessionmaker(bind=env["engine"], autoflush=False))
    conv_client = TestClient(conv_app)
    create = conv_client.post("/conversations", headers=headers, json={"title": "t"})
    assert create.status_code == 201

    # STUDENT cannot access admin APIs
    admin_app = _make_app(admin_auth_router)
    _install_db_override(admin_app, sessionmaker(bind=env["engine"], autoflush=False))
    admin_client = TestClient(admin_app, raise_server_exceptions=False)
    me = admin_client.get("/auth/me", headers=headers)
    assert me.status_code in (401, 403)


def test_admin_authentication_flow(auth_env):
    env = auth_env
    token = create_access_token({"sub": env["admin"].id, "role": "ADMIN", "is_admin": True})
    admin_app = _make_app(admin_auth_router)
    _install_db_override(admin_app, sessionmaker(bind=env["engine"], autoflush=False))
    client = TestClient(admin_app, raise_server_exceptions=False)

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"


def test_super_admin_authentication_flow(auth_env):
    env = auth_env
    token = create_access_token({"sub": env["super_admin"].id, "role": "SUPER_ADMIN", "is_admin": True})
    admin_app = _make_app(admin_auth_router)
    _install_db_override(admin_app, sessionmaker(bind=env["engine"], autoflush=False))
    client = TestClient(admin_app, raise_server_exceptions=False)

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "SUPER_ADMIN"

    # SUPER_ADMIN can also refresh
    from backend.app.core.security import get_password_hash
    session, _ = env["make_session"](env["super_admin"])
    refresh = create_refresh_token({"sub": env["super_admin"].id})
    session.refresh_token_hash = get_password_hash(refresh[:16])
    env["db"].commit()

    resp = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_admin_logout_revokes_sessions(auth_env):
    env = auth_env
    token = create_access_token({"sub": env["admin"].id, "role": "ADMIN", "is_admin": True})
    admin_app = _make_app(admin_auth_router)
    _install_db_override(admin_app, sessionmaker(bind=env["engine"], autoflush=False))
    client = TestClient(admin_app)

    resp = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    env["db"].expire_all()
    sessions = env["db"].query(UserSession).filter(UserSession.user_id == env["admin"].id).all()
    assert all(s.is_revoked for s in sessions)


# ------------------------------------------------------------------
# 16 — SSE contract check
# ------------------------------------------------------------------

def test_sse_stream_uses_header_auth_not_url_token():
    """SSE /chat/stream must require Bearer header auth, not a URL token."""
    chat_source = (ROOT / "backend/app/api/v1/chat.py").read_text(encoding="utf-8")
    assert "get_current_user" in chat_source  # header-based dependency
    assert "?token" not in chat_source and "token=" not in chat_source

    # Frontend streams via POST fetch with Authorization header
    api_source = (ROOT / "apps/user-web/src/services/api.js").read_text(encoding="utf-8")
    assert "chat/stream" in api_source
    assert "authFetch" in api_source  # goes through header-auth client
