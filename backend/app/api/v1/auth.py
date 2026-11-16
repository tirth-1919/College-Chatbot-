"""Authentication API Router.

Endpoints for user registration, login, logout, token refresh, password reset,
profile inspection, and email verification with brute-force rate limiting.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    VerifyEmailRequest,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.user import UserResponse
from app.schemas.registration import AcceptInvitationRequest, CollegeAdminInvitationResponse
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService
from app.repositories.registration_repository import RegistrationRepository
from app.repositories.college_repository import CollegeRepository
from app.dependencies.auth import get_current_user, get_optional_current_user
from app.middleware.rate_limit import rate_limit
from app.core.config import settings
from app.security.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=APIResponse[dict],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def register_user(
    req: RegisterRequest,
    session: AsyncSession = Depends(get_db),
):
    """Creates a new student, college administrator, or system user account."""
    auth_service = AuthService(session)
    user, membership = await auth_service.register(req)

    return APIResponse(
        success=True,
        message="Registration successful. Please verify your email address.",
        data={
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role,
            "verification_token": user.verification_token if settings.ENVIRONMENT == "development" else None,
            "college_id": str(membership.college_id) if membership else None,
        },
    )


@router.post(
    "/login",
    response_model=APIResponse[TokenResponse],
    summary="Authenticate and receive JWT token",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def login_user(
    req: LoginRequest,
    session: AsyncSession = Depends(get_db),
):
    """Validates user credentials and issues a signed JWT access token and refresh token."""
    auth_service = AuthService(session)
    token_response = await auth_service.authenticate(req)

    return APIResponse(
        success=True,
        message="Authentication successful",
        data=token_response,
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenResponse],
    summary="Exchange refresh token for a new access token",
)
async def refresh_access_token(
    req: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
):
    """Validates an unexpired refresh token and returns a freshly signed access token."""
    auth_service = AuthService(session)
    token_response = await auth_service.refresh_access_token(req.refresh_token)

    return APIResponse(
        success=True,
        message="Access token refreshed successfully",
        data=token_response,
    )


@router.post(
    "/logout",
    response_model=APIResponse[bool],
    summary="Terminate session and discard client credentials",
)
async def logout_user():
    """Client-side session termination instruction."""
    return APIResponse(
        success=True,
        message="Session terminated successfully. Please clear client-stored tokens.",
        data=True,
    )


@router.post(
    "/forgot-password",
    response_model=APIResponse[bool],
    summary="Request a password reset link/token",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
async def forgot_password_endpoint(
    req: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Generates password reset token without revealing whether email exists in the platform."""
    auth_service = AuthService(session)
    await auth_service.request_password_reset(req.email)
    return APIResponse(
        success=True,
        message="If an account with that email exists, password reset instructions have been sent.",
        data=True,
    )


@router.post(
    "/reset-password",
    response_model=APIResponse[bool],
    summary="Reset password using verification token",
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
)
async def reset_password_endpoint(
    req: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
):
    """Verifies reset code and establishes new password."""
    auth_service = AuthService(session)
    await auth_service.reset_password(req.email, req.token, req.new_password)
    return APIResponse(
        success=True,
        message="Password has been successfully reset. You may now log in with your new credentials.",
        data=True,
    )


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Get current authenticated user profile",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Returns the authenticated user's account profile and permissions."""
    return APIResponse(
        success=True,
        message="Profile retrieved",
        data=UserResponse.model_validate(current_user),
    )


@router.post(
    "/verify-email",
    response_model=APIResponse[bool],
    summary="Verify user email address",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def verify_email_address(
    req: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
):
    """Validates a 6-to-8 character email verification token."""
    auth_service = AuthService(session)
    is_verified = await auth_service.verify_email(req.email, req.token)
    return APIResponse(
        success=True,
        message="Email successfully verified",
        data=is_verified,
    )


@router.get(
    "/invitations/{token}",
    response_model=APIResponse[CollegeAdminInvitationResponse],
    summary="Validate and inspect administrator invitation token",
)
async def get_invitation_info(
    token: str,
    session: AsyncSession = Depends(get_db),
):
    """Allows invited administrators to view invitation details before setting password."""
    reg_repo = RegistrationRepository(session)
    invite = await reg_repo.get_invitation_by_token(token)
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation link is invalid or has expired.")

    college_repo = CollegeRepository(session)
    col = await college_repo.get_by_id(invite.college_id)
    college_name = col.name if col else "College Institution"

    res_data = CollegeAdminInvitationResponse.model_validate(invite)
    res_data.college_name = college_name

    return APIResponse(
        success=True,
        message="Invitation token is valid",
        data=res_data,
    )


@router.post(
    "/accept-invitation",
    response_model=APIResponse[TokenResponse],
    summary="Accept administrator invitation, set password, and receive access token",
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
)
async def accept_administrator_invitation(
    req: AcceptInvitationRequest,
    current_user: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Activates a new account or promotes the signed-in invitee atomically."""
    reg_repo = RegistrationRepository(session)
    if current_user and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify the existing account before accepting a college administrator invitation.",
        )
    if current_user is None and not req.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A password is required to create a new administrator account.",
        )

    success, msg, user, college_id, is_existing_user = await reg_repo.accept_invitation(
        token=req.invitation_token,
        full_name=req.full_name,
        password=req.password,
        authenticated_user_id=current_user.id if current_user else None,
    )

    if not success or not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    if is_existing_user:
        if not current_user or current_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sign in to the invited account before accepting this invitation.",
            )
        access_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            college_id=str(college_id),
            additional_claims={"email": user.email, "full_name": user.full_name},
        )
        refresh_token = create_access_token(
            subject=str(user.id),
            role=user.role,
            college_id=str(college_id),
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            additional_claims={"token_type": "refresh"},
        )
        token_response = TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            college_id=college_id,
            is_verified=user.is_verified,
            refresh_token=refresh_token,
        )
    else:
        if not req.password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A password is required to create a new administrator account.",
            )
        token_response = await AuthService(session).authenticate(
            LoginRequest(email=user.email, password=req.password)
        )

    return APIResponse(
        success=True,
        message="Administrator credentials created and authenticated successfully.",
        data=token_response,
    )
