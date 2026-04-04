from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import get_auth_service, get_current_user
from app.core.rate_limit import auth_limit, limiter
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import APIResponse, ok
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(auth_limit)
async def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[UserResponse]:
    user = await auth_service.register(body)
    return ok(data=user, message="Registration successful")


@router.post("/login", response_model=APIResponse[TokenResponse])
@limiter.limit(auth_limit)
async def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[TokenResponse]:
    user_agent = request.headers.get("user-agent")
    tokens = await auth_service.login(body, user_agent=user_agent)
    return ok(data=tokens)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh(
    body: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[TokenResponse]:
    tokens = await auth_service.refresh(raw_refresh_token=body.refresh_token)
    return ok(data=tokens)


@router.post("/logout", response_model=APIResponse[None])
async def logout(
    body: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> APIResponse[None]:
    await auth_service.logout(raw_refresh_token=body.refresh_token)
    return ok(data=None, message="Logged out successfully")


@router.get("/me", response_model=APIResponse[UserResponse])
async def me(
    current_user: UserResponse = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    return ok(data=current_user)
