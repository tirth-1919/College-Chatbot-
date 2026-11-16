"""College Memberships API Router."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.membership import CollegeMembership
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.college_repository import CollegeRepository
from app.repositories.user_repository import UserRepository
from app.schemas.membership import MembershipCreateRequest, MembershipResponse
from app.schemas.common import APIResponse
from app.dependencies.auth import require_role, require_super_admin
from app.services.tenant_service import TenantService
from app.database.session import set_rls_context

router = APIRouter(prefix="/memberships", tags=["Tenant Memberships"])


@router.post(
    "",
    response_model=APIResponse[MembershipResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign user to college tenant (Super Admin only)",
)
async def create_membership(
    req: MembershipCreateRequest,
    current_admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
):
    """Establishes an administrative link between a user and a college tenant."""
    membership_repo = MembershipRepository(session)
    college_repo = CollegeRepository(session)
    user_repo = UserRepository(session)

    college = await college_repo.get_by_id(req.college_id)
    if not college:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="College not found.")

    user = await user_repo.get_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    existing = await membership_repo.get_membership(req.college_id, req.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already holds a membership with this college.",
        )

    # Automatically set user's role to COLLEGE_ADMIN if currently STUDENT
    if user.role == "STUDENT":
        user.role = "COLLEGE_ADMIN"
        await user_repo.update(user)

    membership = CollegeMembership(
        id=uuid.uuid4(),
        college_id=req.college_id,
        user_id=req.user_id,
        role_in_college=req.role_in_college,
        is_primary=True,
    )

    created = await membership_repo.create(membership)
    return APIResponse(
        success=True,
        message="College membership assigned successfully",
        data=MembershipResponse.model_validate(created),
    )


@router.get(
    "/college/{college_id}",
    response_model=APIResponse[List[MembershipResponse]],
    summary="List memberships for a specific college",
)
async def list_college_memberships(
    college_id: uuid.UUID,
    current_user: User = Depends(require_role("COLLEGE_ADMIN", "SUPER_ADMIN")),
    session: AsyncSession = Depends(get_db),
):
    """Lists memberships only for the authenticated admin's authorized college."""
    college = await TenantService(session).validate_user_access_to_college(
        current_user,
        college_id,
    )
    await set_rls_context(
        session,
        college_id=college.id,
        user_id=current_user.id,
        is_super_admin=(current_user.role == "SUPER_ADMIN"),
    )
    membership_repo = MembershipRepository(session)
    memberships = await membership_repo.list_by_college(college_id)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(memberships)} memberships",
        data=[MembershipResponse.model_validate(m) for m in memberships],
    )

