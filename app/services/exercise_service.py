"""Exercise catalog (HU-17.1): create, list, update and delete exercises."""
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Exercise, RoutineExercise
from app.schemas.routine import ExerciseCreate, ExerciseUpdate

logger = logging.getLogger(__name__)

EXERCISE_NOT_FOUND = "El ejercicio no existe."
DUPLICATED_NAME = "Ya existe un ejercicio con ese nombre."
EXERCISE_IN_USE = "No puedes borrar un ejercicio que forma parte de una rutina."


def list_exercises(db: Session) -> list[Exercise]:
    """The whole catalog ordered by muscle group and name."""
    query = select(Exercise).order_by(Exercise.muscle_group, Exercise.name)
    return list(db.scalars(query).all())


def get_exercise(db: Session, exercise_id: int) -> Exercise:
    """One exercise. 404 when it does not exist."""
    exercise = db.get(Exercise, exercise_id)
    if exercise is None:
        raise NotFoundError(EXERCISE_NOT_FOUND)
    return exercise


def create_exercise(db: Session, data: ExerciseCreate) -> Exercise:
    """Adds an exercise. 409 when the name is already taken (UNIQUE in the table)."""
    exercise = Exercise(**data.model_dump())
    db.add(exercise)
    _commit_or_conflict(db)
    logger.info("Exercise created: exercise_id=%s", exercise.id)
    return exercise


def update_exercise(db: Session, exercise_id: int, data: ExerciseUpdate) -> Exercise:
    """Changes only the fields the client sent."""
    exercise = get_exercise(db, exercise_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)
    _commit_or_conflict(db)
    logger.info("Exercise updated: exercise_id=%s", exercise.id)
    return exercise


def delete_exercise(db: Session, exercise_id: int) -> None:
    """Deletes an exercise. 409 if a routine still uses it, so no routine loses a line"""
    exercise = get_exercise(db, exercise_id)
    in_use = db.scalar(
        select(RoutineExercise.id).where(RoutineExercise.exercise_id == exercise_id).limit(1)
    )
    if in_use is not None:
        raise ConflictError(EXERCISE_IN_USE)
    db.delete(exercise)
    db.commit()
    logger.info("Exercise deleted: exercise_id=%s", exercise_id)


def _commit_or_conflict(db: Session) -> None:
    """Commits; the only UNIQUE in exercises is the name, so a clash means a duplicate name."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(DUPLICATED_NAME) from None