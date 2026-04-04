import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer()


def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_token_repo(session: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    token_repo: RefreshTokenRepository = Depends(get_token_repo),
) -> AuthService:
    return AuthService(user_repo=user_repo, token_repo=token_repo)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    payload = decode_access_token(credentials.credentials)
    user_id = uuid.UUID(payload["sub"])
    return await auth_service.get_current_user(user_id=user_id)
