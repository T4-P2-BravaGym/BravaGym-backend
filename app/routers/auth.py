from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
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


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member",
    responses={
        409: {"description": "Email already registered"},
        429: {
            "description": "Too many registrations from this IP",
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
        401: {"description": "Wrong email or password, or inactive user"},
        429: {
            "description": "Too many failed login attempts for this email and IP",
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
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    key = login_rate_key(form.username, client_ip(request))
    login_attempt_limiter.assert_allowed(key)
    try:
        token = auth_service.login(db, email=form.username, password=form.password)
    except UnauthorizedError:
        login_attempt_limiter.record(key)
        raise
    login_attempt_limiter.reset(key)
    return LoginResponse(access_token=token)
