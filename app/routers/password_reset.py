"""Public recovery endpoints, with validation errors that never echo secrets."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.openapi import error
from app.core.password_reset_delivery import (
    deliver_password_reset,
    get_reset_email_sender,
    get_reset_session_factory,
)
from app.schemas.password_reset import (
    PasswordResetAccepted,
    PasswordResetConfirm,
    PasswordResetRequest,
)
from app.services.password_reset_service import ACCEPTED_DETAIL, confirm_password_reset


class PrivateValidationRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def safe_handler(request: Request):
            try:
                return await original(request)
            except RequestValidationError:
                return JSONResponse(
                    status_code=422,
                    content={
                        "detail": "Revisa los datos del formulario.",
                        "code": "validation_error",
                    },
                    headers={"Cache-Control": "no-store"},
                )

        return safe_handler


router = APIRouter(
    prefix="/auth/password-reset", tags=["auth"], route_class=PrivateValidationRoute
)


@router.post(
    "",
    status_code=202,
    response_model=PasswordResetAccepted,
    summary="Request a password recovery link",
    responses={
        202: {
            "description": "Same response for every valid email",
            "content": {"application/json": {"example": {"detail": ACCEPTED_DETAIL}}},
        },
        422: error("Invalid input; values are not echoed"),
    },
)
def request_reset(
    data: PasswordResetRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    session_factory: Annotated[object, Depends(get_reset_session_factory)],
    sender: Annotated[object, Depends(get_reset_email_sender)],
) -> PasswordResetAccepted:
    background_tasks.add_task(
        deliver_password_reset,
        str(data.email),
        session_factory,
        sender,
        get_settings().frontend_url,
    )
    response.headers["Cache-Control"] = "no-store"
    return PasswordResetAccepted(detail=ACCEPTED_DETAIL)


@router.post(
    "/confirm",
    status_code=204,
    response_model=None,
    summary="Set a new password using a single-use recovery token",
    responses={
        204: {
            "description": "Password changed and every old session invalidated; no body"
        },
        400: {
            **error("Invalid, expired or already-used link"),
            "content": {
                "application/json": {
                    "example": {
                        "detail": "El enlace no es válido o ha caducado. Solicita uno nuevo.",
                        "code": "bad_request",
                    }
                }
            },
        },
        422: error("Invalid input; secrets are not echoed"),
    },
)
def confirm_reset(
    data: PasswordResetConfirm, db: Annotated[Session, Depends(get_db)]
) -> Response:
    confirm_password_reset(db, data.token, data.new_password)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
