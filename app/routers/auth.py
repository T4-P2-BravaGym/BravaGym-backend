from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import LoginResponse, UserCreate
from app.schemas.user import UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member",
    responses={409: {"description": "Email already registered"}},
)
def register(data: UserCreate, db: Annotated[Session, Depends(get_db)]):
    return auth_service.register(db, data)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in and get an access token",
    responses={401: {"description": "Wrong email or password, or inactive user"}},
)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    token = auth_service.login(db, email=form.username, password=form.password)
    return LoginResponse(access_token=token)
