"""Routines (HU-17, HU-18); a new routine deactivates the previous one."""
import logging
from itertools import groupby

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Exercise, Routine, RoutineExercise, User
from app.models.enums import RoleName
from app.schemas.routine import (
    RoutineCreate,
    RoutineDayOut,
    RoutineLineIn,
    RoutineLineOut,
    RoutineOut,
    RoutineUpdate,
    TrainerRoutineOut,
)

logger = logging.getLogger(__name__)

NO_ROUTINE = "Todavía no tienes una rutina asignada. Tu entrenadora te la preparará pronto."
ROUTINE_NOT_FOUND = "La rutina no existe."
LINE_NOT_FOUND = "La línea no existe en esta rutina."
MEMBER_NOT_FOUND = "La socia no existe."
EXERCISE_NOT_FOUND = "Alguno de los ejercicios no existe."
DUPLICATED_SLOT = "Ya hay un ejercicio en ese día y posición."


def _to_routine_out(routine: Routine) -> RoutineOut:
    # Sort here instead of trusting the load order: groupby needs the lines sorted by day
    items = sorted(routine.items, key=lambda item: (item.day_number, item.position))
    days = [
        RoutineDayOut(
            day_number=day_number,
            lines=[
                RoutineLineOut(
                    id=item.id,
                    position=item.position,
                    exercise_name=item.exercise.name,
                    sets=item.sets,
                    reps=item.reps,
                    rest_seconds=item.rest_seconds,
                )
                for item in day_items
            ],
        )
        for day_number, day_items in groupby(items, key=lambda item: item.day_number)
    ]
    return RoutineOut(
        id=routine.id,
        name=routine.name,
        trainer_name=f"{routine.trainer.first_name} {routine.trainer.last_name}",
        start_date=routine.start_date,
        notes=routine.notes,
        days=days,
    )


def my_routine(db: Session, member: User) -> RoutineOut:
    """The member's active routine. 404 when she has none."""
    routine = db.scalar(
        select(Routine).where(Routine.member_id == member.id, Routine.is_active.is_(True))
    )
    if routine is None:
        raise NotFoundError(NO_ROUTINE)
    return _to_routine_out(routine)


# ---------- Trainer side (HU-17.2) ----------

def create_routine(db: Session, trainer: User, data: RoutineCreate) -> TrainerRoutineOut:
    """Creates a routine for a member and deactivates her previous one, in one transaction."""
    # Validate everything first: if something is wrong, nothing is written
    _get_member_or_404(db, data.member_id)
    _check_unique_slots(data.lines)
    _check_exercises_exist(db, {line.exercise_id for line in data.lines})

    # Deactivate the old routine and add the new one before a single commit:
    # if anything fails, the member keeps her previous routine (criterion 3)
    db.execute(
        update(Routine)
        .where(Routine.member_id == data.member_id, Routine.is_active.is_(True))
        .values(is_active=False)
    )
    routine = Routine(
        member_id=data.member_id,
        trainer=trainer,  # from the token, never from the body
        name=data.name,
        start_date=data.start_date,
        notes=data.notes,
        # Each input line becomes a row of routine_exercises
        items=[RoutineExercise(**line.model_dump()) for line in data.lines],
    )
    db.add(routine)
    _commit_or_conflict(db)
    logger.info(
        "Routine created: routine_id=%s member_id=%s trainer_id=%s",
        routine.id, data.member_id, trainer.id,
    )
    return _to_trainer_out(routine)


def list_routines(db: Session, member_id: int | None = None) -> list[TrainerRoutineOut]:
    """All routines, newest first. With member_id, only that member's routines."""
    query = select(Routine).order_by(Routine.id.desc())
    if member_id is not None:
        query = query.where(Routine.member_id == member_id)
    return [_to_trainer_out(routine) for routine in db.scalars(query).all()]


def get_routine(db: Session, routine_id: int) -> TrainerRoutineOut:
    """One routine. 404 when it does not exist."""
    return _to_trainer_out(_get_routine_or_404(db, routine_id))


def update_routine(db: Session, routine_id: int, data: RoutineUpdate) -> TrainerRoutineOut:
    """Changes only the header fields the client sent."""
    routine = _get_routine_or_404(db, routine_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(routine, field, value)
    db.commit()
    logger.info("Routine updated: routine_id=%s", routine.id)
    return _to_trainer_out(routine)


def deactivate_routine(db: Session, routine_id: int) -> None:
    """DELETE = deactivate: the history stays in the database."""
    routine = _get_routine_or_404(db, routine_id)
    routine.is_active = False
    db.commit()
    logger.info("Routine deactivated: routine_id=%s", routine.id)


def add_line(db: Session, routine_id: int, line: RoutineLineIn) -> TrainerRoutineOut:
    """Adds one exercise to a routine. 409 if that day and position are taken."""
    routine = _get_routine_or_404(db, routine_id)
    _check_exercises_exist(db, {line.exercise_id})
    # Compare (day, position) pairs of the existing lines with the new one
    if any((item.day_number, item.position) == (line.day_number, line.position) for item in routine.items):
        raise ConflictError(DUPLICATED_SLOT)
    routine.items.append(RoutineExercise(**line.model_dump()))
    _commit_or_conflict(db)
    logger.info("Routine line added: routine_id=%s", routine.id)
    return _to_trainer_out(routine)


def delete_line(db: Session, routine_id: int, item_id: int) -> None:
    """Removes one exercise from a routine. 404 if the line is not in that routine."""
    routine = _get_routine_or_404(db, routine_id)
    # next(..., None): first matching line, or None if there is none
    item = next((item for item in routine.items if item.id == item_id), None)
    if item is None:
        raise NotFoundError(LINE_NOT_FOUND)
    # Removing it from the list deletes the row (cascade delete-orphan) and keeps the list in sync
    routine.items.remove(item)
    db.commit()
    logger.info("Routine line deleted: routine_id=%s item_id=%s", routine_id, item_id)

# ---------- Helpers ----------

def _get_routine_or_404(db: Session, routine_id: int) -> Routine:
    routine = db.get(Routine, routine_id)
    if routine is None:
        raise NotFoundError(ROUTINE_NOT_FOUND)
    return routine


def _get_member_or_404(db: Session, member_id: int) -> User:
    """Only active users with the member role can receive a routine."""
    member = db.get(User, member_id)
    if member is None or not member.is_active or member.role.name != RoleName.MEMBER:
        raise NotFoundError(MEMBER_NOT_FOUND)
    return member


def _check_unique_slots(lines: list[RoutineLineIn]) -> None:
    """Two lines cannot share day and position (criterion 2 of HU-17)."""
    slots = [(line.day_number, line.position) for line in lines]
    # A set removes duplicates: if it is shorter than the list, there was a repeated pair
    if len(slots) != len(set(slots)):
        raise ConflictError(DUPLICATED_SLOT)


def _check_exercises_exist(db: Session, exercise_ids: set[int]) -> None:
    """One query for all ids instead of one per line."""
    found = set(db.scalars(select(Exercise.id).where(Exercise.id.in_(exercise_ids))).all())
    if found != exercise_ids:
        raise NotFoundError(EXERCISE_NOT_FOUND)


def _commit_or_conflict(db: Session) -> None:
    """Last barrier: the UNIQUE(routine_id, day_number, position) of the table."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(DUPLICATED_SLOT) from None


def _to_trainer_out(routine: Routine) -> TrainerRoutineOut:
    """Reuses the member view (DRY) and adds what only the trainer needs."""
    base = _to_routine_out(routine)
    # ** unpacks the dict of base as keyword arguments
    return TrainerRoutineOut(**base.model_dump(), member_id=routine.member_id, is_active=routine.is_active)