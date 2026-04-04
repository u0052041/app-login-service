import uuid

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo

    async def register(self, data: RegisterRequest) -> UserResponse:
        if await self._user_repo.get_by_email(data.email):
            raise ConflictError("Email already registered")
        if await self._user_repo.get_by_username(data.username):
            raise ConflictError("Username already taken")

        user = User()
        user.email = data.email
        user.username = data.username
        user.hashed_password = hash_password(data.password)
        user.is_active = True
        user.is_verified = False

        created = await self._user_repo.create(user)
        return UserResponse.model_validate(created)

    async def login(
        self,
        data: LoginRequest,
        user_agent: str | None,
    ) -> TokenResponse:
        user = await self._user_repo.get_by_email(data.email)
        if not user:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("Account is disabled")

        return await self._issue_tokens(user, user_agent)

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:
        token_hash = hash_refresh_token(raw_refresh_token)
        token = await self._token_repo.get_active_by_hash(token_hash)
        if not token:
            raise UnauthorizedError("Invalid or expired refresh token")

        user = await self._user_repo.get_by_id(token.user_id)
        if not user or not user.is_active:
            raise ForbiddenError("Account is disabled")

        await self._token_repo.revoke(token)
        return await self._issue_tokens(user, user_agent=None)

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_refresh_token(raw_refresh_token)
        token = await self._token_repo.get_active_by_hash(token_hash)
        if not token:
            raise UnauthorizedError("Invalid or expired refresh token")
        await self._token_repo.revoke(token)

    async def get_current_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        return UserResponse.model_validate(user)

    async def _issue_tokens(self, user: User, user_agent: str | None) -> TokenResponse:
        settings = get_settings()
        access_token = create_access_token(subject=str(user.id))
        raw_refresh, expires_at = create_refresh_token()

        token = RefreshToken()
        token.token_hash = hash_refresh_token(raw_refresh)
        token.user_id = user.id
        token.expires_at = expires_at
        token.user_agent = user_agent

        await self._token_repo.create(token)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
