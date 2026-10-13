"""Controller for exercises: receives the request, checks permissions, calls the service, returns a schema."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.routine import ExerciseCreate, ExerciseOut, ExerciseUpdate
from app.services import exercise_service

router = APIRouter(prefix="/exercises", tags=["exercises"])

# Reusable type aliases so every endpoint stays short (DRY)
# Only trainers and superadmin manage the catalog (docs/api.md)
CurrentTrainer = Annotated[User, Depends(require_roles(RoleName.TRAINER, RoleName.SUPERADMIN))]
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[ExerciseOut], summary="List the exercise catalog")
def list_exercises(_trainer: CurrentTrainer, db: DbSession):
    return exercise_service.list_exercises(db)


@router.get(
    "/{exercise_id}",
    response_model=ExerciseOut,
    summary="Get one exercise",
    responses={404: {"description": "The exercise does not exist"}},
)
def get_exercise(exercise_id: int, _trainer: CurrentTrainer, db: DbSession):
    return exercise_service.get_exercise(db, exercise_id)


@router.post(
    "",
    response_model=ExerciseOut,
    status_code=status.HTTP_201_CREATED,  # 201 = created, not just 200 OK
    summary="Add an exercise to the catalog",
    responses={409: {"description": "An exercise with that name already exists"}},
)
def create_exercise(data: ExerciseCreate, _trainer: CurrentTrainer, db: DbSession):
    return exercise_service.create_exercise(db, data)


@router.patch(
    "/{exercise_id}",
    response_model=ExerciseOut,
    summary="Update an exercise",
    responses={404: {"description": "The exercise does not exist"}, 409: {"description": "Duplicated name"}},
)
def update_exercise(exercise_id: int, data: ExerciseUpdate, _trainer: CurrentTrainer, db: DbSession):
    return exercise_service.update_exercise(db, exercise_id, data)


@router.delete(
    "/{exercise_id}",
    status_code=status.HTTP_204_NO_CONTENT,  # 204 = done, nothing to return
    summary="Delete an exercise that no routine uses",
    responses={404: {"description": "The exercise does not exist"}, 409: {"description": "A routine uses it"}},
)
def delete_exercise(exercise_id: int, _trainer: CurrentTrainer, db: DbSession) -> None:
    exercise_service.delete_exercise(db, exercise_id)