from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import oauth2_scheme
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.openapi import error
from app.core.rate_limit import (
    TOO_MANY_ATTEMPTS,
    client_ip,
    login_attempt_limiter,
    login_rate_key,
    register_attempt_limiter,
    register_rate_key,
)
from app.schemas.auth import LoginResponse, UserCreate
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE = "brava.refresh"
AUTH_COOKIE_PATH = "/api/v1/auth"


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = {*get_settings().cors_origins, str(request.base_url).rstrip("/")}
    if origin is not None and origin not in allowed:
        raise PermissionDeniedError("Origen de la petición no permitido.")
    if origin is None and request.headers.get("sec-fetch-site") == "cross-site":
        raise PermissionDeniedError("Origen de la petición no permitido.")


def _check_session_request(
    request: Request,
    csrf: Annotated[
        str | None,
        Header(
            alias="X-Brava-CSRF",
            description="Send 1 for refresh/logout",
            examples=["1"],
        ),
    ] = None,
) -> None:
    _check_origin(request)
    if csrf != "1":
        raise PermissionDeniedError("Falta la comprobación de seguridad de la sesión.")


def _session_cookie(response: Response, token: str | None) -> None:
    options = {
        "path": AUTH_COOKIE_PATH,
        "httponly": True,
        "secure": get_settings().environment != "local",
        "samesite": "lax",
    }
    if token is None:
        response.delete_cookie(REFRESH_COOKIE, **options)
    else:
        response.set_cookie(
            REFRESH_COOKIE,
            token,
            max_age=get_settings().refresh_token_expire_days * 86400,
            **options,
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _invalid_session(exc: UnauthorizedError) -> JSONResponse:
    response = JSONResponse(
        status_code=401,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )
    _session_cookie(response, None)
    return response


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member",
    responses={
        409: error("Email already registered"),
        429: {
            **error("Too many registrations from this IP"),
            "content": {
                "application/json": {
                    "example": {
                        "detail": TOO_MANY_ATTEMPTS,
                        "code": "rate_limited",
                    }
                }
            },
        },
    },
)
def register(
    request: Request,
    data: UserCreate,
    db: Annotated[Session, Depends(get_db)],
):
    key = register_rate_key(client_ip(request))
    register_attempt_limiter.assert_allowed(key)
    user = auth_service.register(db, data)
    register_attempt_limiter.record(key)
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in and get an access token",
    responses={
        401: error("Wrong email or password, or inactive user"),
        403: error("Untrusted browser origin"),
        429: {
            **error("Too many failed login attempts for this email and IP"),
            "content": {
                "application/json": {
                    "example": {
                        "detail": TOO_MANY_ATTEMPTS,
                        "code": "rate_limited",
                    }
                }
            },
        },
    },
)
def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    _check_origin(request)
    key = login_rate_key(form.username, client_ip(request))
    login_attempt_limiter.assert_allowed(key)
    try:
        tokens = auth_service.login(db, email=form.username, password=form.password)
    except UnauthorizedError:
        login_attempt_limiter.record(key)
        raise
    login_attempt_limiter.reset(key)
    _session_cookie(response, tokens.refresh_token)
    return LoginResponse(access_token=tokens.access_token)


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Rotate the refresh cookie and get a new access token",
    dependencies=[Depends(_check_session_request)],
    responses={
        200: {
            "description": "New access token and rotated HttpOnly refresh cookie",
            "content": {
                "application/json": {
                    "example": {"access_token": "<access JWT>", "token_type": "bearer"}
                }
            },
        },
        401: error("Missing, invalid, expired or revoked session"),
        403: error("Untrusted origin or missing X-Brava-CSRF: 1"),
    },
)
def refresh(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
):
    try:
        if not refresh_token:
            raise UnauthorizedError(auth_service.INVALID_SESSION_TOKEN)
        tokens = auth_service.refresh_session(db, refresh_token)
    except UnauthorizedError as exc:
        return _invalid_session(exc)
    _session_cookie(response, tokens.refresh_token)
    return LoginResponse(access_token=tokens.access_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke the current access and refresh tokens and clear the cookie",
    description="Send the bearer access token, refresh cookie and X-Brava-CSRF: 1. "
    "An expired access token is accepted only with its owner's valid refresh cookie.",
    dependencies=[Depends(_check_session_request)],
    responses={
        204: {
            "description": "Session revoked; refresh cookie removed; no response body"
        },
        401: error("Missing or invalid session, or token owners differ"),
        403: error("Untrusted origin or missing X-Brava-CSRF: 1"),
    },
)
def logout(
    db: Annotated[Session, Depends(get_db)],
    access_token: Annotated[str | None, Depends(oauth2_scheme)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    try:
        if not access_token or not refresh_token:
            raise UnauthorizedError(auth_service.INVALID_SESSION_TOKEN)
        auth_service.logout_session(db, access_token, refresh_token)
    except UnauthorizedError as exc:
        return _invalid_session(exc)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _session_cookie(response, None)
    return response
