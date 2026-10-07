"""Controller for users: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-04, HU-05, HU-06): GET/PATCH /users/me, GET /users, PATCH /users/{id}/role
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.schemas.user import UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get my profile",
    responses={401: {"description": "Not logged in"}},
)
def get_me(current_user: CurrentUser) -> UserOut:
    return current_user


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update my profile (name, phone and email)",
    responses={401: {"description": "Not logged in"}, 409: {"description": "Email already in use"}},
)
def update_me(
        changes: UserUpdate,
        current_user: CurrentUser,
        db: Annotated[Session, Depends(get_db)],
) -> UserOut:
    return user_service.update_me(db, current_user, changes)
