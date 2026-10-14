"""Controller for users: receives the request, checks permissions, calls the service, returns a schema (HU-04, HU-05, HU-06, HU-31)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentUser, require_roles
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.user import RoleUpdate, UserAdminUpdate, UserOut, UserPage, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[Session, Depends(get_db)]

CurrentAdmin = Annotated[
    User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))
]


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
    is_active: Annotated[
        bool | None, Query(description="true = active, false = deactivated")
    ] = None,
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
    responses={
        401: {"description": "Not logged in"},
        409: {"description": "Email already in use"},
    },
)
def update_me(
    changes: UserUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> UserOut:
    return user_service.update_me(db, current_user, changes)


@router.patch(
    "/{user_id}/role",
    response_model=UserOut,
    summary="Change a user's role (RN-18, RN-19)",
    responses={
        401: {"description": "Not logged in"},
        403: {
            "description": "Not admin, or an admin trying to give or remove admin/superadmin"
        },
        404: {"description": "The user does not exist"},
        409: {"description": "Changing your own role, or removing the last superadmin"},
    },
)
def change_role(
    user_id: int, data: RoleUpdate, actor: CurrentAdmin, db: DbSession
) -> UserOut:
    return user_service.change_role(db, actor, user_id, data.role)


# The /{user_id} routes go after /me: FastAPI would read "me" as an id otherwise
ADMIN_ERRORS = {
    401: {"description": "Not logged in"},
    403: {
        "description": "Not admin, or an admin trying to manage an admin or superadmin"
    },
    404: {"description": "The user does not exist"},
}


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="Get a user (admin)",
    responses=ADMIN_ERRORS,
)
def get_user(user_id: int, admin: CurrentAdmin, db: DbSession) -> UserOut:
    return user_service.get_user(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    summary="Edit a user's name, phone and email (admin)",
    responses={**ADMIN_ERRORS, 409: {"description": "Email already in use"}},
)
def update_user(
    user_id: int, changes: UserAdminUpdate, admin: CurrentAdmin, db: DbSession
) -> UserOut:
    return user_service.update_user(db, admin, user_id, changes)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a user (soft delete, admin)",
    description=(
        "Sets is_active=false and deactivated_at, cancels her active subscription and future "
        "bookings (as an approved cancellation, HU-20). The row is kept and she can no longer log in."
    ),
    responses={
        **ADMIN_ERRORS,
        409: {"description": "Deactivating yourself, or the last superadmin"},
    },
)
def deactivate_user(user_id: int, admin: CurrentAdmin, db: DbSession) -> None:
    user_service.deactivate_user(db, admin, user_id)
