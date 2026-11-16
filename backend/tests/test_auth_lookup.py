import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.auth import login_user
from app.repositories.user_repository import AuthUserLookup, UserRepository
from app.schemas.auth import LoginRequest
from app.security.password import hash_password, verify_password
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_auth_lookup_returns_only_minimal_authentication_fields():
    user_id = uuid.uuid4()
    password_hash = hash_password("ValidPassword123!")
    session = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = {
        "id": user_id,
        "email": "user@example.edu",
        "hashed_password": password_hash,
        "full_name": "Test User",
        "role": "STUDENT",
        "is_verified": True,
        "is_active": True,
    }
    session.execute.return_value = result

    account = await UserRepository(session).get_auth_account_by_email(" USER@example.edu ")

    assert account is not None
    assert set(vars(account)) == {
        "id",
        "email",
        "hashed_password",
        "full_name",
        "role",
        "is_verified",
        "is_active",
    }
    assert password_hash not in repr(account)
    statement, params = session.execute.await_args.args
    sql = str(statement)
    assert "SELECT *" not in sql
    assert "verification_token" not in sql
    assert "preferences" not in sql
    assert params == {"email": "user@example.edu"}


@pytest.mark.asyncio
async def test_login_verifies_password_using_the_narrow_lookup():
    password = "ValidPassword123!"
    account = AuthUserLookup(
        id=uuid.uuid4(),
        email="user@example.edu",
        hashed_password=hash_password(password),
        full_name="Test User",
        role="STUDENT",
        is_verified=True,
        is_active=True,
    )
    service = AuthService(AsyncMock())
    service.user_repo.get_auth_account_by_email = AsyncMock(return_value=account)

    with patch("app.services.auth_service.set_rls_context", new=AsyncMock()):
        response = await service.authenticate(
            LoginRequest(email=account.email, password=password)
        )

    assert response.user_id == account.id
    assert response.email == account.email
    assert verify_password(password, account.hashed_password)


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_with_narrow_lookup():
    account = AuthUserLookup(
        id=uuid.uuid4(),
        email="user@example.edu",
        hashed_password=hash_password("ValidPassword123!"),
        full_name="Test User",
        role="STUDENT",
        is_verified=True,
        is_active=True,
    )
    service = AuthService(AsyncMock())
    service.user_repo.get_auth_account_by_email = AsyncMock(return_value=account)

    with pytest.raises(HTTPException) as exc:
        await service.authenticate(
            LoginRequest(email=account.email, password="WrongPassword123!")
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_api_response_does_not_include_password_hash(caplog):
    password = "ValidPassword123!"
    account = AuthUserLookup(
        id=uuid.uuid4(),
        email="user@example.edu",
        hashed_password=hash_password(password),
        full_name="Test User",
        role="STUDENT",
        is_verified=True,
        is_active=True,
    )
    auth_service = AuthService(AsyncMock())
    auth_service.user_repo.get_auth_account_by_email = AsyncMock(return_value=account)
    with (
        patch("app.services.auth_service.set_rls_context", new=AsyncMock()),
        patch("app.api.v1.auth.AuthService", return_value=auth_service),
    ):
        api_response = await login_user(
            LoginRequest(email=account.email, password=password),
            session=AsyncMock(),
        )

    serialized = api_response.model_dump_json()
    assert account.hashed_password not in serialized
    assert "hashed_password" not in serialized
    assert account.hashed_password not in caplog.text
