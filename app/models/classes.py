from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import BookingStatus, SessionStatus
from app.models.types import db_enum, utc_now

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class ClassType(Base):
    __tablename__ = "class_types"
    __table_args__ = (
        CheckConstraint("extra_price_cents >= 0", name="ck_class_types_extra_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    extra_price_cents: Mapped[int] = mapped_column(default=0)
    is_personal_training: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)


class ClassSession(Base):
    __tablename__ = "class_sessions"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_class_sessions_capacity"),
        CheckConstraint("duration_minutes > 0", name="ck_class_sessions_duration"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    class_type_id: Mapped[int] = mapped_column(ForeignKey("class_types.id"))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(index=True)  # UTC
    duration_minutes: Mapped[int] = mapped_column(default=60)
    capacity: Mapped[int]
    status: Mapped[SessionStatus] = mapped_column(
        db_enum(SessionStatus), default=SessionStatus.SCHEDULED
    )

    class_type: Mapped["ClassType"] = relationship()
    trainer: Mapped["User"] = relationship()
    bookings: Mapped[list["Booking"]] = relationship(back_populates="class_session")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("user_id", "class_session_id", name="uq_bookings_user_session"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    class_session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(
        db_enum(BookingStatus), default=BookingStatus.CONFIRMED
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    cancelled_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship()
    class_session: Mapped["ClassSession"] = relationship(back_populates="bookings")