"""Unit tests for AuthService — all repos are mocked with AsyncMock."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService


def _make_user(
    *,
    is_active: bool = True,
    email: str = "alice@example.com",
    username: str = "alice",
) -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = email
    u.username = username
    u.hashed_password = "$2b$12$fakehash"
    u.is_active = is_active
    u.is_verified = False
    u.created_at = datetime.now(UTC)
    u.updated_at = datetime.now(UTC)
    return u


def _make_refresh_token(user_id: uuid.UUID) -> RefreshToken:
    t = RefreshToken()
    t.id = uuid.uuid4()
    t.token_hash = "abc123" * 10
    t.user_id = user_id
    t.expires_at = datetime.now(UTC) + timedelta(days=7)
    t.revoked_at = None
    t.created_at = datetime.now(UTC)
    return t


def _make_service(user_repo: AsyncMock, token_repo: AsyncMock) -> AuthService:
    return AuthService(user_repo=user_repo, token_repo=token_repo)


class TestRegister:
    async def test_register_success(self) -> None:
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None
        user_repo.get_by_username.return_value = None
        created_user = _make_user()
        user_repo.create.return_value = created_user
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        result = await service.register(
            RegisterRequest(email="alice@example.com", username="alice", password="Secret123!")
        )

        assert result.email == created_user.email
        user_repo.create.assert_called_once()

    async def test_register_duplicate_email_raises_conflict(self) -> None:
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = _make_user()
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(ConflictError, match="Email"):
            await service.register(
                RegisterRequest(email="alice@example.com", username="alice", password="Secret123!")
            )

    async def test_register_duplicate_username_raises_conflict(self) -> None:
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None
        user_repo.get_by_username.return_value = _make_user()
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(ConflictError, match="Username"):
            await service.register(
                RegisterRequest(email="new@example.com", username="alice", password="Secret123!")
            )


class TestLogin:
    async def test_login_success_returns_token_pair(self) -> None:
        user = _make_user()
        from app.core.security import hash_password
        user.hashed_password = hash_password("Secret123!")

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        token_repo = AsyncMock()
        token_repo.create.return_value = _make_refresh_token(user.id)

        service = _make_service(user_repo, token_repo)
        result = await service.login(
            LoginRequest(email="alice@example.com", password="Secret123!"),
            user_agent=None,
        )

        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"

    async def test_login_user_not_found_raises_unauthorized(self) -> None:
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.login(
                LoginRequest(email="nobody@example.com", password="Secret123!"),
                user_agent=None,
            )

    async def test_login_wrong_password_raises_unauthorized(self) -> None:
        user = _make_user()
        from app.core.security import hash_password
        user.hashed_password = hash_password("correct_password")

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.login(
                LoginRequest(email="alice@example.com", password="wrong_password"),
                user_agent=None,
            )

    async def test_login_inactive_user_raises_forbidden(self) -> None:
        user = _make_user(is_active=False)
        from app.core.security import hash_password
        user.hashed_password = hash_password("Secret123!")

        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = user
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(ForbiddenError):
            await service.login(
                LoginRequest(email="alice@example.com", password="Secret123!"),
                user_agent=None,
            )


class TestRefresh:
    async def test_refresh_success_rotates_tokens(self) -> None:
        user = _make_user()
        token = _make_refresh_token(user.id)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        token_repo = AsyncMock()
        token_repo.get_active_by_hash.return_value = token
        token_repo.create.return_value = _make_refresh_token(user.id)

        service = _make_service(user_repo, token_repo)
        result = await service.refresh(raw_refresh_token="some_raw_token")

        token_repo.revoke.assert_called_once_with(token)
        assert result.access_token

    async def test_refresh_invalid_token_raises_unauthorized(self) -> None:
        user_repo = AsyncMock()
        token_repo = AsyncMock()
        token_repo.get_active_by_hash.return_value = None

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.refresh(raw_refresh_token="invalid_token")

    async def test_refresh_inactive_user_raises_forbidden(self) -> None:
        user = _make_user(is_active=False)
        token = _make_refresh_token(user.id)

        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        token_repo = AsyncMock()
        token_repo.get_active_by_hash.return_value = token

        service = _make_service(user_repo, token_repo)
        with pytest.raises(ForbiddenError):
            await service.refresh(raw_refresh_token="some_raw_token")


class TestLogout:
    async def test_logout_revokes_token(self) -> None:
        user = _make_user()
        token = _make_refresh_token(user.id)

        user_repo = AsyncMock()
        token_repo = AsyncMock()
        token_repo.get_active_by_hash.return_value = token

        service = _make_service(user_repo, token_repo)
        await service.logout(raw_refresh_token="some_raw_token")

        token_repo.revoke.assert_called_once_with(token)

    async def test_logout_invalid_token_raises_unauthorized(self) -> None:
        user_repo = AsyncMock()
        token_repo = AsyncMock()
        token_repo.get_active_by_hash.return_value = None

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.logout(raw_refresh_token="invalid_token")


class TestGetCurrentUser:
    async def test_get_current_user_success(self) -> None:
        user = _make_user()
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        result = await service.get_current_user(user_id=user.id)

        assert result.id == user.id

    async def test_get_current_user_not_found_raises_unauthorized(self) -> None:
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = None
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.get_current_user(user_id=uuid.uuid4())

    async def test_get_current_user_inactive_raises_unauthorized(self) -> None:
        user = _make_user(is_active=False)
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user
        token_repo = AsyncMock()

        service = _make_service(user_repo, token_repo)
        with pytest.raises(UnauthorizedError):
            await service.get_current_user(user_id=user.id)
