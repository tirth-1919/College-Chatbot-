import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.tenant_service import TenantService


@pytest.mark.asyncio
async def test_student_membership_blocks_selecting_another_college():
    ait_id = uuid.uuid4()
    rcti_id = uuid.uuid4()
    student = User(
        id=uuid.uuid4(),
        email="ait-student@example.invalid",
        hashed_password="unused",
        full_name="AIT Test Student",
        role="STUDENT",
    )
    college = SimpleNamespace(id=rcti_id, is_active=True, status="APPROVED")
    service = TenantService(AsyncMock())
    service.get_active_college = AsyncMock(return_value=college)
    service.membership_repo.list_by_user_id = AsyncMock(
        return_value=[SimpleNamespace(college_id=ait_id)]
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.validate_user_access_to_college(student, rcti_id)

    assert exc_info.value.status_code == 403
    assert "Cross-tenant access denied" in exc_info.value.detail


@pytest.mark.asyncio
async def test_unassigned_student_can_still_access_public_college_information():
    college_id = uuid.uuid4()
    student = User(
        id=uuid.uuid4(),
        email="unassigned-student@example.invalid",
        hashed_password="unused",
        full_name="Unassigned Test Student",
        role="STUDENT",
    )
    college = SimpleNamespace(id=college_id, is_active=True, status="APPROVED")
    service = TenantService(AsyncMock())
    service.get_active_college = AsyncMock(return_value=college)
    service.membership_repo.list_by_user_id = AsyncMock(return_value=[])

    result = await service.validate_user_access_to_college(student, college_id)

    assert result is college
