"""Class types and sessions: free spots computed, no overlaps (RN-09), ownership (RN-10).

Free spots are never stored: free_spots = capacity - count(confirmed bookings).
See docs/er.md. Business rules RN-xx: docs/business-rules.md.

TODO(HU-11): create/update sessions, overlap checks (RN-09), ownership (RN-10).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Booking, ClassSession
from app.models.enums import BookingStatus


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


def sessions_with_free_spots_stmt() -> Select:
    """SELECT sessions with confirmed_count and free_spots (outerjoin + count).

    Sessions with no confirmed bookings get confirmed_count=0 and free_spots=capacity.
    Waitlisted and cancelled bookings are excluded from the count.
    """
    confirmed = _confirmed_bookings_subquery()
    confirmed_count = func.coalesce(confirmed.c.confirmed_count, 0)
    free_spots = ClassSession.capacity - confirmed_count

    return (
        select(
            ClassSession,
            confirmed_count.label("confirmed_count"),
            free_spots.label("free_spots"),
        )
        .outerjoin(confirmed, confirmed.c.class_session_id == ClassSession.id)
        .order_by(ClassSession.starts_at)
    )


def list_sessions_with_free_spots(db: Session) -> list[SessionWithFreeSpots]:
    """Load all sessions with confirmed-booking counts and computed free spots."""
    rows = db.execute(sessions_with_free_spots_stmt()).all()
    return [
        SessionWithFreeSpots(
            session=session,
            confirmed_count=int(confirmed_count),
            free_spots=int(spots),
        )
        for session, confirmed_count, spots in rows
    ]
