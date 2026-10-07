"""Exercises and routines; a new routine deactivates the previous one.

TODO(HU-17, HU-18). Business rules RN-xx: docs/business-rules.md.
"""
from itertools import groupby

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models import Routine, User
from app.schemas.routine import RoutineDayOut, RoutineLineOut, RoutineOut

NO_ROUTINE = "Todavía no tienes una rutina asignada. Tu entrenadora te la preparará pronto."


def _to_routine_out(routine: Routine) -> RoutineOut:
    # Sort here instead of trusting the load order: groupby needs the lines sorted by day
    items = sorted(routine.items, key=lambda item: (item.day_number, item.position))
    days = [
        RoutineDayOut(
            day_number=day_number,
            lines=[
                RoutineLineOut(
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
