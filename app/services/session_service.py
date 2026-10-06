"""Class types and sessions: free spots computed, no overlaps (RN-09), ownership (RN-10).

Free spots are never stored: free_spots = capacity - count(confirmed bookings).
See docs/er.md. Business rules RN-xx: docs/business-rules.md.

TODO(HU-11): create/update sessions, overlap checks (RN-09), ownership (RN-10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ValidationAppError
from app.models import Booking, ClassSession
from app.models.enums import BookingStatus, SessionStatus

INVALID_DATE_RANGE = "El rango de fechas no es válido: 'from' debe ser anterior o igual a 'to'."


@dataclass(frozen=True, slots=True)
class SessionWithFreeSpots:
    """A class session plus seats derived from confirmed bookings."""

    session: ClassSession
    confirmed_count: int
    free_spots: int


def free_spots_from_capacity(capacity: int, confirmed_count: int) -> int:
    """Return remaining seats from capacity and confirmed bookings (never stored)."""
    return capacity - confirmed_count


def _confirmed_bookings_subquery():
    """Per-session count of bookings with status=confirmed."""
    return (
        select(
            Booking.class_session_id.label("class_session_id"),
            func.count(Booking.id).label("confirmed_count"),
        )
        .where(Booking.status == BookingStatus.CONFIRMED)
        .group_by(Booking.class_session_id)
        .subquery()
    )


def sessions_with_free_spots_stmt(
    *,
    from_: datetime | None = None,
    to: datetime | None = None,
    class_type_id: int | None = None,
    trainer_id: int | None = None,
    only_available: bool = False,
    scheduled_only: bool = True,
) -> Select:
    """SELECT sessions with confirmed_count and free_spots (outerjoin + count).

    Sessions with no confirmed bookings get confirmed_count=0 and free_spots=capacity.
    Waitlisted and cancelled bookings are excluded from the count.
    """
    if from_ is not None and to is not None and from_ > to:
        raise ValidationAppError(INVALID_DATE_RANGE)

    confirmed = _confirmed_bookings_subquery()
    confirmed_count = func.coalesce(confirmed.c.confirmed_count, 0)
    free_spots = ClassSession.capacity - confirmed_count

    stmt = (
        select(
            ClassSession,
            confirmed_count.label("confirmed_count"),
            free_spots.label("free_spots"),
        )
        .options(joinedload(ClassSession.class_type))
        .outerjoin(confirmed, confirmed.c.class_session_id == ClassSession.id)
    )

    if scheduled_only:
        stmt = stmt.where(ClassSession.status == SessionStatus.SCHEDULED)
    if from_ is not None:
        stmt = stmt.where(ClassSession.starts_at >= from_)
    if to is not None:
        stmt = stmt.where(ClassSession.starts_at <= to)
    if class_type_id is not None:
        stmt = stmt.where(ClassSession.class_type_id == class_type_id)
    if trainer_id is not None:
        stmt = stmt.where(ClassSession.trainer_id == trainer_id)
    if only_available:
        stmt = stmt.where(free_spots > 0)

    return stmt.order_by(ClassSession.starts_at, ClassSession.id)


def _rows_to_sessions(rows) -> list[SessionWithFreeSpots]:
    return [
        SessionWithFreeSpots(
            session=session,
            confirmed_count=int(confirmed_count),
            free_spots=int(spots),
        )
        for session, confirmed_count, spots in rows
    ]


def list_sessions_with_free_spots(db: Session) -> list[SessionWithFreeSpots]:
    """Load all sessions with confirmed-booking counts and computed free spots."""
    rows = db.execute(sessions_with_free_spots_stmt(scheduled_only=False)).unique().all()
    return _rows_to_sessions(rows)


def list_sessions(
    db: Session,
    *,
    from_: datetime | None = None,
    to: datetime | None = None,
    class_type_id: int | None = None,
    trainer_id: int | None = None,
    only_available: bool = False,
    page: int = 1,
    size: int = 20,
) -> tuple[list[SessionWithFreeSpots], int]:
    """List scheduled sessions with filters, free spots and pagination."""
    stmt = sessions_with_free_spots_stmt(
        from_=from_,
        to=to,
        class_type_id=class_type_id,
        trainer_id=trainer_id,
        only_available=only_available,
        scheduled_only=True,
    )
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)

    offset = (page - 1) * size
    rows = db.execute(stmt.offset(offset).limit(size)).unique().all()
    return _rows_to_sessions(rows), total
