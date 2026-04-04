class AppError(Exception):
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class ConflictError(AppError):
    status_code = 409
    detail = "Resource already exists"


class UnauthorizedError(AppError):
    status_code = 401
    detail = "Unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    detail = "Forbidden"


class NotFoundError(AppError):
    status_code = 404
    detail = "Resource not found"
