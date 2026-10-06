from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


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