import base64
import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.v1.auth import accept_administrator_invitation
from app.api.v1.chat import _assert_session_ownership
from app.core.config import settings
from app.database.session import set_rls_context
from app.repositories.registration_repository import RegistrationRepository
from app.schemas.auth import RegisterRequest
from app.schemas.registration import AcceptInvitationRequest
from app.services.auth_service import AuthService


@pytest.mark.parametrize("role", ["COLLEGE_ADMIN", "SUPER_ADMIN", "GLOBAL_SUPER_ADMIN"])
@pytest.mark.asyncio
async def test_public_registration_rejects_privileged_roles(role):
    service = AuthService(AsyncMock())
    service.user_repo.get_auth_account_by_email = AsyncMock()
    request = RegisterRequest(
        email="new.user@example.edu",
        password="SecurePassword123!",
        full_name="New User",
        role=role,
    )

    with pytest.raises(HTTPException) as exc:
        await service.register(request)

    assert exc.value.status_code == 403
    service.user_repo.get_auth_account_by_email.assert_not_awaited()


@pytest.mark.asyncio
async def test_public_student_registration_sets_self_rls_context():
    service = AuthService(AsyncMock())
    service.user_repo.get_auth_account_by_email = AsyncMock(return_value=None)
    service.user_repo.create = AsyncMock(side_effect=lambda user: user)
    request = RegisterRequest(
        email="new.user@example.edu",
        password="SecurePassword123!",
        full_name="New User",
    )

    with patch("app.services.auth_service.set_rls_context", new=AsyncMock()) as set_context:
        user, membership = await service.register(request)

    assert user.role == "STUDENT"
    assert membership is None
    set_context.assert_awaited_once_with(
        service.session,
        college_id=None,
        user_id=user.id,
        is_super_admin=False,
    )
    service.user_repo.create.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_invitation_acceptance_uses_database_result_and_fails_closed():
    session = AsyncMock()
    repository = RegistrationRepository(session)
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = None
    session.execute.return_value = result

    with patch(
        "app.repositories.registration_repository.set_rls_context",
        new=AsyncMock(),
    ) as set_context:
        accepted = await repository.accept_invitation(
            "synthetic-expired-token", "Test Admin", "SyntheticPassword123!"
        )

    assert accepted == (False, "Invitation could not be accepted.", None, None, False)
    query, params = session.execute.await_args.args
    assert "accept_college_admin_invitation" in str(query)
    assert params["token"] == "synthetic-expired-token"
    assert params["full_name"] == "Test Admin"
    assert params["password_hash"] != "SyntheticPassword123!"
    set_context.assert_not_awaited()


def test_invitation_acceptance_allows_signed_in_user_without_new_password():
    request = AcceptInvitationRequest.model_validate({
        "invitation_token": "synthetic-invitation-token",
        "full_name": "Existing User",
    })
    assert request.password is None


@pytest.mark.asyncio
async def test_invitation_acceptance_requires_password_for_new_accounts():
    request = AcceptInvitationRequest.model_validate({
        "invitation_token": "synthetic-invitation-token",
        "full_name": "New User",
    })
    with pytest.raises(HTTPException) as exc:
        await accept_administrator_invitation(
            request,
            current_user=None,
            session=AsyncMock(),
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_rls_context_is_hmac_signed_and_transaction_local():
    session = AsyncMock()
    signing_key = bytes(range(32))
    with patch.object(settings, "RLS_CONTEXT_SECRET", SecretStr(signing_key.hex())):
        await set_rls_context(
            session,
            college_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            user_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            is_super_admin=True,
        )

    statement, params = session.execute.await_args.args
    assert "set_config" in str(statement)
    assert ", true)" in str(statement)
    assert params["college_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert params["user_id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert params["is_super"] == "1"
    assert params["email_verification"] == "0"
    payload = (
        f"v1|{params['user_id']}|{params['college_id']}|{params['is_super']}|"
        f"{params['email_verification']}|{params['expires_at']}"
    )
    expected_signature = base64.urlsafe_b64encode(
        hmac.new(signing_key, payload.encode("utf-8"), hashlib.sha256).digest()
    ).decode("ascii").rstrip("=")
    assert hmac.compare_digest(params["signature"], expected_signature)
    assert params["visitor_token"] == ""


@pytest.mark.asyncio
async def test_rls_context_fails_closed_without_configured_secret():
    session = AsyncMock()
    with patch.object(settings, "RLS_CONTEXT_SECRET", None):
        with pytest.raises(RuntimeError, match="RLS_CONTEXT_SECRET must be configured"):
            await set_rls_context(
                session,
                college_id=None,
                user_id=None,
                is_super_admin=False,
            )
    session.execute.assert_not_awaited()


def test_chat_session_access_requires_exact_user_ownership():
    owner_id = uuid.uuid4()
    session = MagicMock(user_id=owner_id)

    with pytest.raises(HTTPException) as exc:
        _assert_session_ownership(session, None)
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _assert_session_ownership(session, MagicMock(id=uuid.uuid4(), role="STUDENT"))
    assert exc.value.status_code == 403

    _assert_session_ownership(session, MagicMock(id=owner_id, role="STUDENT"))


def test_anonymous_chat_session_requires_matching_visitor_token():
    visitor_token = "one-time-session-capability"
    session = MagicMock(
        user_id=None,
        visitor_token_hash=hashlib.sha256(visitor_token.encode("utf-8")).hexdigest(),
    )

    _assert_session_ownership(session, None, visitor_token)
    with pytest.raises(HTTPException) as exc:
        _assert_session_ownership(session, None, "another-session-token")
    assert exc.value.status_code == 403


def test_super_admin_chat_access_requires_authenticated_super_admin_object():
    session = MagicMock(user_id=uuid.uuid4())
    _assert_session_ownership(session, MagicMock(id=uuid.uuid4(), role="SUPER_ADMIN"))
