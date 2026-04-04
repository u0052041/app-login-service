from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str | None = None
    errors: list[str] | None = None


def ok(data: T, message: str | None = None) -> APIResponse[T]:
    return APIResponse(success=True, data=data, message=message)


def err(message: str, errors: list[str] | None = None) -> APIResponse[None]:
    return APIResponse(success=False, message=message, errors=errors)
