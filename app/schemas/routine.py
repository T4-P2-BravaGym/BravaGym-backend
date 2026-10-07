"""TODO(HU-17, HU-18): ExerciseOut/Create, RoutineOut with its lines grouped by day, RoutineCreate.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict


class RoutineLineOut(BaseModel):
    """One exercise of a routine day: what to do and how much to rest."""

    position: int
    exercise_name: str
    sets: int
    reps: int
    rest_seconds: int


class RoutineDayOut(BaseModel):
    """A training day of the routine with its exercises in order."""

    day_number: int
    lines: list[RoutineLineOut]


class RoutineOut(BaseModel):
    """A routine with its exercises grouped by day."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Fuerza base · 4 semanas",
                "trainer_name": "Ana Torres",
                "start_date": "2026-10-05",
                "notes": "Subir peso cuando completes todas las series con buena técnica.",
                "days": [
                    {
                        "day_number": 1,
                        "lines": [
                            {"position": 1, "exercise_name": "Sentadilla trasera", "sets": 4, "reps": 6, "rest_seconds": 150}
                        ],
                    }
                ],
            }
        }
    )

    id: int
    name: str
    trainer_name: str
    start_date: date
    notes: str | None
    days: list[RoutineDayOut]
    