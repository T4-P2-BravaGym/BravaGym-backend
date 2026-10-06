import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):

    status_code = 400
    code = "bad_request"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class UnauthorizedError(AppError):

    status_code = 401
    code = "unauthorized"
    headers = {"WWW-Authenticate": "Bearer"}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "forbidden"


class ConflictError(AppError):

    status_code = 409
    code = "conflict"


class ValidationAppError(AppError):
    """Business/input validation that should surface as HTTP 422."""

    status_code = 422
    code = "validation_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unexpected error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Ha ocurrido un error inesperado.", "code": "internal_error"},
        )