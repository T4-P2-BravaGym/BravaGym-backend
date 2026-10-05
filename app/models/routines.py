"""Exercises and routines (HU-17, HU-18).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    Exercise: id, name (unique), muscle_group, description
    Routine: id, member_id -> users.id, trainer_id -> users.id, name, start_date, notes, is_active
    RoutineExercise: id, routine_id -> routines.id, exercise_id -> exercises.id, day_number,
                     position, sets, reps, rest_seconds
                     UNIQUE(routine_id, day_number, position)
"""
from app.core.database import Base  # noqa: F401
