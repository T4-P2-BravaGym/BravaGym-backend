"""Controller for routines: receives the request, checks permissions, calls the service, returns a schema."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.openapi import error, errors
from app.models import User
from app.models.enums import RoleName
from app.schemas.routine import (
    RoutineCreate,
    RoutineLineIn,
    RoutineOut,
    RoutineUpdate,
    TrainerRoutineOut,
)
from app.services import routine_service

# Every endpoint needs a login and a role, so 401 and 403 are documented for all of them
router = APIRouter(prefix="/routines", tags=["routines"], responses=errors(401, 403))


CurrentTrainer = Annotated[
    User, Depends(require_roles(RoleName.TRAINER, RoleName.SUPERADMIN))
]
DbSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/me",
    response_model=RoutineOut,
    summary="Get my active routine with its exercises grouped by day",
    responses={404: error("The member has no active routine")},
)
def get_my_routine(
    member: Annotated[User, Depends(require_roles(RoleName.MEMBER))],
    db: Annotated[Session, Depends(get_db)],
) -> RoutineOut:
    return routine_service.my_routine(db, member)


@router.post(
    "",
    response_model=TrainerRoutineOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a routine for a member (her previous routine becones inactive)",
    responses={
        404: error("The member or an exercise does not exist"),
        409: error("Two lines share the same day and position"),
    },
)
def create_routine(data: RoutineCreate, trainer: CurrentTrainer, db: DbSession):
    return routine_service.create_routine(db, trainer, data)


@router.get(
    "",
    response_model=list[TrainerRoutineOut],
    summary="List routines, optionally by member",
)
def list_routines(
    _trainer: CurrentTrainer,
    db: DbSession,
    member_id: Annotated[int | None, Query(ge=1)] = None,
):
    return routine_service.list_routines(db, member_id)


@router.get(
    "/{routine_id}",
    response_model=TrainerRoutineOut,
    summary="Get one routine",
    responses={404: error("The routine does not exist")},
)
def get_routine(routine_id: int, _trainer: CurrentTrainer, db: DbSession):
    return routine_service.get_routine(db, routine_id)


@router.patch(
    "/{routine_id}",
    response_model=TrainerRoutineOut,
    summary="Update the name, start date or notes of a routine",
    responses={404: error("The routine does not exist")},
)
def update_routine(
    routine_id: int, data: RoutineUpdate, _trainer: CurrentTrainer, db: DbSession
):
    return routine_service.update_routine(db, routine_id, data)


@router.delete(
    "/{routine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a routine (it is not deleted)",
    responses={404: error("The routine does not exist")},
)
def deactivate_routine(
    routine_id: int, _trainer: CurrentTrainer, db: DbSession
) -> None:
    routine_service.deactivate_routine(db, routine_id)


@router.post(
    "/{routine_id}/exercises",
    response_model=TrainerRoutineOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an exercise line to a routine",
    responses={
        404: error("The routine or the exercise does not exist"),
        409: error("That day and position are already taken"),
    },
)
def add_line(
    routine_id: int, line: RoutineLineIn, _trainer: CurrentTrainer, db: DbSession
):
    return routine_service.add_line(db, routine_id, line)


@router.delete(
    "/{routine_id}/exercises/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an exercise line from a routine",
    responses={404: error("The line is not in that routine")},
)
def delete_line(
    routine_id: int, item_id: int, _trainer: CurrentTrainer, db: DbSession
) -> None:
    routine_service.delete_line(db, routine_id, item_id)
