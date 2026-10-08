"""Controller for users: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-05): PATCH /users/{id}/role
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require_roles
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.user import UserOut, UserPage, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]

CurrentAdmin = Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))]


@router.get(
    "",
    response_model=UserPage,
    summary="List users for administration",
    description=(
        "Paginated list of users for admins. Optional filters: role, is_active and a "
        "case-insensitive search q in first name, last name and email. "
        "Ordered by last name, first name and id."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Only admin and superadmin can list users"},
        422: {"description": "Unknown role, size over 100 or invalid query parameters"},
    },
)
def list_users(
        admin: CurrentAdmin,  # only used to check the role
        db: DbSession,
        role: Annotated[RoleName | None, Query(description="Filter by role")] = None,
        is_active: Annotated[bool | None, Query(description="true = active, false = deactivated")] = None,
        q: Annotated[
            str | None,
            Query(max_length=60, description="Search in first name, last name and email"),
        ] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserPage:
    users, total = user_service.list_users(
        db, role=role, is_active=is_active, q=q, page=page, size=size
    )
    # model_validate reads each SQLAlchemy User; UserOut picks only the safe fields
    return UserPage(
        items=[UserOut.model_validate(user) for user in users],
        total=total,
        page=page,
        size=size,
    )


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
        db: DbSession,
) -> UserOut:
    return user_service.update_me(db, current_user, changes)
