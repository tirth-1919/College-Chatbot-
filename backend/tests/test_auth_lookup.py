import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.auth import login_user
from app.dependencies.auth import get_current_user
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
async def test_college_admin_login_resolves_membership_when_rls_hides_orm_row():
    password = "ValidPassword123!"
    account = AuthUserLookup(
        id=uuid.uuid4(),
        email="admin@college.example",
        hashed_password=hash_password(password),
        full_name="College Admin",
        role="COLLEGE_ADMIN",
        is_verified=True,
        is_active=True,
    )
    college_id = uuid.uuid4()
    college = SimpleNamespace(
        id=college_id,
        name="Example College",
        status="APPROVED",
        is_active=True,
    )
    service = AuthService(AsyncMock())
    service.user_repo.get_auth_account_by_email = AsyncMock(return_value=account)
    service.membership_repo.get_by_user_id = AsyncMock(return_value=None)
    service.membership_repo.user_belongs_to_college = AsyncMock(return_value=True)
    service.college_repo.list_colleges = AsyncMock(return_value=[college])
    service.college_repo.get_by_id = AsyncMock(return_value=college)

    with patch("app.services.auth_service.set_rls_context", new=AsyncMock()):
        response = await service.authenticate(
            LoginRequest(email=account.email, password=password)
        )

    assert response.role == "COLLEGE_ADMIN"
    assert response.college_id == college_id
    service.membership_repo.user_belongs_to_college.assert_awaited_once_with(
        account.id, college_id
    )


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


@pytest.mark.asyncio
async def test_current_user_resolves_rls_hidden_college_admin_from_signed_claims():
    user_id = uuid.uuid4()
    account = AuthUserLookup(
        id=user_id,
        email="admin@college.example",
        hashed_password=hash_password("ValidPassword123!"),
        full_name="College Admin",
        role="COLLEGE_ADMIN",
        is_verified=True,
        is_active=True,
    )
    repository = MagicMock()
    repository.get_by_id = AsyncMock(return_value=None)
    repository.get_auth_account_by_email = AsyncMock(return_value=account)
    session = AsyncMock()
    credentials = MagicMock(credentials="signed-token")

    with (
        patch("app.dependencies.auth.decode_token", return_value={
            "sub": str(user_id),
            "email": account.email,
            "role": account.role,
        }),
        patch("app.dependencies.auth.UserRepository", return_value=repository),
        patch("app.dependencies.auth.set_rls_context", new=AsyncMock()),
    ):
        user = await get_current_user(auth_credentials=credentials, session=session)

    assert user.id == user_id
    assert user.role == "COLLEGE_ADMIN"
    repository.get_auth_account_by_email.assert_awaited_once_with(account.email)


@pytest.mark.asyncio
async def test_current_user_rejects_auth_lookup_with_different_signed_identity():
    account = AuthUserLookup(
        id=uuid.uuid4(),
        email="admin@college.example",
        hashed_password=hash_password("ValidPassword123!"),
        full_name="College Admin",
        role="COLLEGE_ADMIN",
        is_verified=True,
        is_active=True,
    )
    repository = MagicMock()
    repository.get_by_id = AsyncMock(return_value=None)
    repository.get_auth_account_by_email = AsyncMock(return_value=account)

    with (
        patch("app.dependencies.auth.decode_token", return_value={
            "sub": str(uuid.uuid4()),
            "email": account.email,
            "role": account.role,
        }),
        patch("app.dependencies.auth.UserRepository", return_value=repository),
        patch("app.dependencies.auth.set_rls_context", new=AsyncMock()),
        pytest.raises(HTTPException) as exc_info,
    ):
        await get_current_user(
            auth_credentials=MagicMock(credentials="signed-token"),
            session=AsyncMock(),
        )

    assert exc_info.value.status_code == 404
