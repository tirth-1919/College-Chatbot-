import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import college_admin


@pytest.mark.asyncio
async def test_college_admin_resigns_verified_tenant_context():
    user_id = uuid.uuid4()
    college_id = uuid.uuid4()
    session = AsyncMock()
    user = SimpleNamespace(id=user_id, role="COLLEGE_ADMIN")
    membership = SimpleNamespace(college_id=college_id)
    college = SimpleNamespace(id=college_id)

    with (
        patch.object(college_admin, "MembershipRepository") as membership_repo,
        patch.object(college_admin, "CollegeRepository") as college_repo,
        patch.object(college_admin, "set_rls_context", new_callable=AsyncMock) as set_context,
    ):
        membership_repo.return_value.get_by_user_id = AsyncMock(return_value=membership)
        college_repo.return_value.get_by_id = AsyncMock(return_value=college)

        result = await college_admin.get_authorized_college(
            x_college_id=str(college_id),
            current_user=user,
            session=session,
        )

    assert result is college
    set_context.assert_awaited_once_with(
        session,
        college_id=college_id,
        user_id=user_id,
        is_super_admin=False,
    )


@pytest.mark.asyncio
async def test_super_admin_resigns_context_for_requested_tenant():
    user_id = uuid.uuid4()
    college_id = uuid.uuid4()
    session = AsyncMock()
    user = SimpleNamespace(id=user_id, role="SUPER_ADMIN")
    college = SimpleNamespace(id=college_id)

    with (
        patch.object(college_admin, "CollegeRepository") as college_repo,
        patch.object(college_admin, "set_rls_context", new_callable=AsyncMock) as set_context,
    ):
        college_repo.return_value.get_by_id = AsyncMock(return_value=college)

        result = await college_admin.get_authorized_college(
            x_college_id=str(college_id),
            current_user=user,
            session=session,
        )

    assert result is college
    set_context.assert_awaited_once_with(
        session,
        college_id=college_id,
        user_id=user_id,
        is_super_admin=True,
    )


@pytest.mark.asyncio
async def test_college_admin_cannot_sign_context_for_another_tenant():
    user_id = uuid.uuid4()
    assigned_college_id = uuid.uuid4()
    requested_college_id = uuid.uuid4()
    session = AsyncMock()
    user = SimpleNamespace(id=user_id, role="COLLEGE_ADMIN")
    membership = SimpleNamespace(college_id=assigned_college_id)

    with (
        patch.object(college_admin, "MembershipRepository") as membership_repo,
        patch.object(college_admin, "CollegeRepository"),
        patch.object(college_admin, "set_rls_context", new_callable=AsyncMock) as set_context,
    ):
        membership_repo.return_value.get_by_user_id = AsyncMock(return_value=membership)

        with pytest.raises(HTTPException) as exc_info:
            await college_admin.get_authorized_college(
                x_college_id=str(requested_college_id),
                current_user=user,
                session=session,
            )

    assert exc_info.value.status_code == 403
    set_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_college_admin_resolves_assignment_when_rls_hides_membership_row():
    user_id = uuid.uuid4()
    college_id = uuid.uuid4()
    session = AsyncMock()
    user = SimpleNamespace(id=user_id, role="COLLEGE_ADMIN")
    college = SimpleNamespace(id=college_id)

    with (
        patch.object(college_admin, "MembershipRepository") as membership_repo,
        patch.object(college_admin, "CollegeRepository") as college_repo,
        patch.object(college_admin, "set_rls_context", new_callable=AsyncMock) as set_context,
    ):
        membership_repo.return_value.get_by_user_id = AsyncMock(return_value=None)
        membership_repo.return_value.user_belongs_to_college = AsyncMock(return_value=True)
        college_repo.return_value.get_by_id = AsyncMock(return_value=college)

        result = await college_admin.get_authorized_college(
            x_college_id=str(college_id),
            current_user=user,
            session=session,
        )

    assert result is college
    membership_repo.return_value.user_belongs_to_college.assert_awaited_once_with(
        user_id, college_id
    )
    set_context.assert_awaited_once_with(
        session,
        college_id=college_id,
        user_id=user_id,
        is_super_admin=False,
    )
