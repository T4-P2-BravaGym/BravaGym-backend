"""Exercises and routines (HU-17, HU-18).

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ExerciseCreate(BaseModel):
    """Input to add an exercise to the catalog."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Sentadilla trasera",
                "muscle_group": "Piernas",
                "description": "Barra sobre los trapecios, baja hasta romper el paralelo.",
            }
        }
    )

    name: str = Field(min_length=2, max_length=100)
    muscle_group: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class ExerciseUpdate(BaseModel):
    """Fields a trainer can change. Fields left out are not changed."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    muscle_group: str | None = Field(default=None, min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class ExerciseOut(BaseModel):
    """An exercise of the catalog."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Sentadilla trasera",
                "muscle_group": "Piernas",
                "description": "Barra sobre los trapecios, baja hasta romper el paralelo.",
            }
        },
    )

    id: int
    name: str
    muscle_group: str
    description: str | None


class RoutineLineIn(BaseModel):
    """One line of a routine as the trainer sends it."""

    exercise_id: int = Field(ge=1)
    day_number: int = Field(ge=1, le=7)
    position: int = Field(ge=1, le=50)
    sets: int = Field(ge=1, le=20)
    reps: int = Field(ge=1, le=100)
    rest_seconds: int = Field(default=60, ge=0, le=600)


class RoutineCreate(BaseModel):
    """A new routine for a member. The trainer comes from the token, never from the body."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "member_id": 5,
                "name": "Fuerza base · 4 semanas",
                "start_date": "2026-10-13",
                "notes": "Subir peso cuando completes todas las series con buena técnica.",
                "lines": [
                    {"exercise_id": 1, "day_number": 1, "position": 1, "sets": 4, "reps": 6, "rest_seconds": 150},
                    {"exercise_id": 2, "day_number": 1, "position": 2, "sets": 3, "reps": 10, "rest_seconds": 90},
                ],
            }
        }
    )

    member_id: int = Field(ge=1)
    name: str = Field(min_length=2, max_length=100)
    start_date: date
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[RoutineLineIn] = Field(min_length=1, max_length=100)


class RoutineUpdate(BaseModel):
    """Header fields a trainer can change. Lines have their own endpoints."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    start_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class RoutineLineOut(BaseModel):
    """One exercise of a routine day: what to do and how much to rest."""

    id: int
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
                            {
                                "position": 1,
                                "exercise_name": "Sentadilla trasera",
                                "sets": 4,
                                "reps": 6,
                                "rest_seconds": 150,
                            }
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


class TrainerRoutineOut(RoutineOut):
    """What the trainer sees: the member's routine plus who it belongs to and if it is active."""

    member_id: int
    is_active: bool