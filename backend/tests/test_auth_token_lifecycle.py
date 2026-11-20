"""Database-free tests for access-token and refresh-token handling."""

import uuid
from datetime import timedelta
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.dependencies.auth import get_current_user, get_optional_current_user
from app.security.jwt import create_access_token, decode_token
from app.services.auth_service import AuthService


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _refresh_token(user_id: uuid.UUID, *, expires_delta: Optional[timedelta] = None) -> str:
    return create_access_token(
        subject=str(user_id),
        role="STUDENT",
        expires_delta=expires_delta or timedelta(days=1),
        additional_claims={"token_type": "refresh"},
    )


@pytest.mark.asyncio
async def test_valid_access_token_resolves_active_user():
    user_id = uuid.uuid4()
    user = SimpleNamespace(id=user_id, role="STUDENT", is_active=True)
    token = create_access_token(subject=str(user_id), role="STUDENT")
    session = AsyncMock()

    with patch(
        "app.dependencies.auth.set_rls_context", new=AsyncMock()
    ), patch(
        "app.dependencies.auth.UserRepository.get_by_id",
        new=AsyncMock(return_value=user),
    ):
        resolved = await get_current_user(_credentials(token), session)

    assert resolved is user
    assert decode_token(token)["token_type"] == "access"


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected():
    token = create_access_token(
        subject=str(uuid.uuid4()),
        role="STUDENT",
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_credentials(token), AsyncMock())

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_cannot_authenticate_as_an_access_token():
    token = _refresh_token(uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(_credentials(token), AsyncMock())

    assert exc_info.value.status_code == 401
    assert await get_optional_current_user(_credentials(token), AsyncMock()) is None


@pytest.mark.asyncio
async def test_inactive_account_revokes_access_and_refresh_use():
    user_id = uuid.uuid4()
    inactive_user = SimpleNamespace(id=user_id, role="STUDENT", is_active=False)
    session = AsyncMock()

    with patch(
        "app.dependencies.auth.set_rls_context", new=AsyncMock()
    ), patch(
        "app.dependencies.auth.UserRepository.get_by_id",
        new=AsyncMock(return_value=inactive_user),
    ):
        with pytest.raises(HTTPException) as access_error:
            await get_current_user(
                _credentials(create_access_token(subject=str(user_id), role="STUDENT")),
                session,
            )
        assert access_error.value.status_code == 403
        assert await get_optional_current_user(
            _credentials(create_access_token(subject=str(user_id), role="STUDENT")),
            session,
        ) is None

    auth_service = AuthService(session)
    auth_service.user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=inactive_user))
    with patch("app.services.auth_service.set_rls_context", new=AsyncMock()):
        with pytest.raises(HTTPException) as refresh_error:
            await auth_service.refresh_access_token(_refresh_token(user_id))

    assert refresh_error.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_refresh_token_issues_a_new_access_token():
    user_id = uuid.uuid4()
    user = SimpleNamespace(
        id=user_id,
        email="student@example.test",
        full_name="Test Student",
        role="STUDENT",
        is_verified=True,
        is_active=True,
    )
    session = AsyncMock()
    auth_service = AuthService(session)
    auth_service.user_repo = SimpleNamespace(get_by_id=AsyncMock(return_value=user))
    refresh_token = _refresh_token(user_id)

    with patch("app.services.auth_service.set_rls_context", new=AsyncMock()):
        result = await auth_service.refresh_access_token(refresh_token)

    access_payload = decode_token(result.access_token)
    assert access_payload["sub"] == str(user_id)
    assert access_payload["token_type"] == "access"
    assert result.refresh_token == refresh_token


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected():
    auth_service = AuthService(AsyncMock())
    expired_refresh = _refresh_token(
        uuid.uuid4(),
        expires_delta=timedelta(minutes=-1),
    )

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(expired_refresh)

    assert exc_info.value.status_code == 401
