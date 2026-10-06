from datetime import date

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    muscle_group: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)


class Routine(Base):
    __tablename__ = "routines"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trainer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date]
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    member: Mapped["User"] = relationship(foreign_keys=[member_id])
    trainer: Mapped["User"] = relationship(foreign_keys=[trainer_id])
    items: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by=lambda: [RoutineExercise.day_number, RoutineExercise.position],
    )

class RoutineExercise(Base):
    __tablename__ = "routine_exercises"
    __table_args__ = (
        UniqueConstraint("routine_id", "day_number", "position", name="uq_routine_exercises_slot"),
        CheckConstraint("day_number BETWEEN 1 AND 7", name="ck_routine_exercises_day"),
        CheckConstraint("position >= 1", name="ck_routine_exercises_position"),
        CheckConstraint("sets > 0 AND reps > 0", name="ck_routine_exercises_sets_reps"),
        CheckConstraint("rest_seconds >= 0", name="ck_routine_exercises_rest"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("routines.id", ondelete="CASCADE"))
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"))
    day_number: Mapped[int]
    position: Mapped[int]
    sets: Mapped[int]
    reps: Mapped[int]
    rest_seconds: Mapped[int] = mapped_column(default=60)

    routine: Mapped["Routine"] = relationship(back_populates="items")
    exercise: Mapped["Exercise"] = relationship()