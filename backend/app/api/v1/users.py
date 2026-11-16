"""Users Administration API Router."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse, UserUpdateRequest
from app.schemas.support_and_analytics import UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.common import APIResponse
from app.dependencies.auth import require_super_admin, get_current_user

router = APIRouter(prefix="/users", tags=["User Administration"])


@router.get(
    "/preferences",
    response_model=APIResponse[UserPreferencesResponse],
    summary="Get authenticated user's preferences & language",
)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves language preference ('en', 'hi', 'gu'), UI theme, and notification settings."""
    user_prefs = current_user.preferences or {}
    data = UserPreferencesResponse(
        user_id=current_user.id,
        preferred_language=current_user.preferred_language or "en",
        theme=user_prefs.get("theme", "dark"),
        email_notifications=user_prefs.get("email_notifications", True),
        preferences=user_prefs,
    )
    return APIResponse(
        success=True,
        message="User preferences retrieved",
        data=data,
    )


@router.put(
    "/preferences",
    response_model=APIResponse[UserPreferencesResponse],
    summary="Update authenticated user's language & UI preferences",
)
async def update_user_preferences(
    req: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Saves user preferred response language, UI theme, and notification choices."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if req.preferred_language:
        lang = req.preferred_language.lower().strip()
        if lang in ("en", "hi", "gu"):
            user.preferred_language = lang

    prefs = dict(user.preferences or {})
    if req.theme:
        prefs["theme"] = req.theme
    if req.email_notifications is not None:
        prefs["email_notifications"] = req.email_notifications
    if req.extra_preferences:
        prefs.update(req.extra_preferences)

    user.preferences = prefs
    await user_repo.update(user)

    data = UserPreferencesResponse(
        user_id=user.id,
        preferred_language=user.preferred_language,
        theme=prefs.get("theme", "dark"),
        email_notifications=prefs.get("email_notifications", True),
        preferences=prefs,
    )
    return APIResponse(
        success=True,
        message="Preferences updated successfully",
        data=data,
    )


@router.get(
    "",
    response_model=APIResponse[List[UserResponse]],
    summary="List platform users (Super Admin only)",
)
async def list_all_users(
    limit: int = 50,
    offset: int = 0,
    current_admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
):
    """Retrieves paginated platform user accounts."""
    user_repo = UserRepository(session)
    users = await user_repo.list_users(limit=limit, offset=offset)
    return APIResponse(
        success=True,
        message=f"Retrieved {len(users)} users",
        data=[UserResponse.model_validate(u) for u in users],
    )


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Get user account details (Super Admin only)",
)
async def get_user_by_id(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
):
    """Fetches a specific user account profile by primary key."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    return APIResponse(
        success=True,
        message="User profile retrieved",
        data=UserResponse.model_validate(user),
    )


@router.patch(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Update user status or permissions (Super Admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    req: UserUpdateRequest,
    current_admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
):
    """Allows Super Admin to update user active status, name, or role."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if req.full_name is not None:
        user.full_name = req.full_name
    if req.is_active is not None:
        user.is_active = req.is_active
    if req.role is not None:
        user.role = req.role

    updated = await user_repo.update(user)
    return APIResponse(
        success=True,
        message="User updated successfully",
        data=UserResponse.model_validate(updated),
    )

