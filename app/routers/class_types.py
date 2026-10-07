"""Controller for class types: receives the request, checks permissions, calls the service.

CRUD for /class-types (HU-11.1). DELETE soft-deactivates (is_active=false).
Keep endpoints thin: no business rules and no complex queries here.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.classes import (
    ClassTypeCreate,
    ClassTypeOut,
    ClassTypePage,
    ClassTypeUpdate,
)
from app.services import session_service

router = APIRouter(prefix="/class-types", tags=["class types"])

DbSession = Annotated[Session, Depends(get_db)]
TrainerOrSuperadmin = Annotated[
    User, Depends(require_roles(RoleName.TRAINER, RoleName.SUPERADMIN))
]


@router.get(
    "",
    response_model=ClassTypePage,
    summary="List class types",
    description=(
        "Public catalogue of class types. By default only active types are returned. "
        "Includes extra_price_cents and is_personal_training for the schedule forms."
    ),
)
def list_class_types(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    active_only: Annotated[
        bool,
        Query(description="If true, hide deactivated class types"),
    ] = True,
) -> ClassTypePage:
    items, total = session_service.list_class_types(
        db, active_only=active_only, page=page, size=size
    )
    return ClassTypePage(
        items=[ClassTypeOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=ClassTypeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a class type",
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not a trainer or superadmin"},
        409: {"description": "A class type with that name already exists"},
    },
)
def create_class_type(
    body: ClassTypeCreate,
    _: TrainerOrSuperadmin,
    db: DbSession,
) -> ClassTypeOut:
    return ClassTypeOut.model_validate(session_service.create_class_type(db, body))


@router.patch(
    "/{class_type_id}",
    response_model=ClassTypeOut,
    summary="Update a class type",
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not a trainer or superadmin"},
        404: {"description": "Class type not found"},
        409: {"description": "A class type with that name already exists"},
    },
)
def update_class_type(
    class_type_id: int,
    body: ClassTypeUpdate,
    _: TrainerOrSuperadmin,
    db: DbSession,
) -> ClassTypeOut:
    return ClassTypeOut.model_validate(
        session_service.update_class_type(db, class_type_id, body)
    )


@router.delete(
    "/{class_type_id}",
    response_model=ClassTypeOut,
    summary="Deactivate a class type",
    description="Soft delete: sets is_active=false. Existing sessions keep the type.",
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not a trainer or superadmin"},
        404: {"description": "Class type not found"},
    },
)
def deactivate_class_type(
    class_type_id: int,
    _: TrainerOrSuperadmin,
    db: DbSession,
) -> ClassTypeOut:
    return ClassTypeOut.model_validate(
        session_service.deactivate_class_type(db, class_type_id)
    )
