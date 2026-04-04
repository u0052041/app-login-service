"""Factory helpers for creating test data directly via SQLAlchemy session."""

import uuid
from datetime import UTC, datetime, timedelta

from app.core.security import hash_password
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def create_user(
    session,
    *,
    email: str = "alice@example.com",
    username: str = "alice",
    password: str = "Secret123!",
    is_active: bool = True,
    is_verified: bool = False,
) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = email
    user.username = username
    user.hashed_password = hash_password(password)
    user.is_active = is_active
    user.is_verified = is_verified
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def create_refresh_token(
    session,
    *,
    user_id: uuid.UUID,
    token_hash: str = "testhash" * 8,
    days: int = 7,
    revoked: bool = False,
) -> RefreshToken:
    token = RefreshToken()
    token.id = uuid.uuid4()
    token.token_hash = token_hash
    token.user_id = user_id
    token.expires_at = datetime.now(UTC) + timedelta(days=days)
    token.revoked_at = datetime.now(UTC) if revoked else None
    session.add(token)
    await session.flush()
    await session.refresh(token)
    return token
