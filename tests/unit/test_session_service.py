"""Focused checks for HU-10.1 free-spots query (full filter suite is HU-10.3)."""

from datetime import datetime, timedelta, timezone

from app.models import Booking, ClassSession, ClassType
from app.models.enums import BookingStatus, RoleName
from app.services.session_service import (
    free_spots_from_capacity,
    list_sessions_with_free_spots,
)


def test_free_spots_from_capacity_is_capacity_minus_confirmed():
    assert free_spots_from_capacity(12, 0) == 12
    assert free_spots_from_capacity(12, 3) == 9
    assert free_spots_from_capacity(1, 1) == 0


def test_list_sessions_counts_only_confirmed_bookings(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = ClassType(name="Fuerza total", description="Sentadilla y peso muerto.")
    db.add(class_type)
    db.flush()

    starts = datetime.now(timezone.utc) + timedelta(days=1)
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts,
        duration_minutes=60,
        capacity=4,
    )
    empty_session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts + timedelta(days=1),
        duration_minutes=60,
        capacity=8,
    )
    db.add_all([session, empty_session])
    db.flush()

    members = [make_user(RoleName.MEMBER) for _ in range(4)]
    db.add_all(
        [
            Booking(user=members[0], class_session=session, status=BookingStatus.CONFIRMED),
            Booking(user=members[1], class_session=session, status=BookingStatus.CONFIRMED),
            Booking(user=members[2], class_session=session, status=BookingStatus.WAITLISTED),
            Booking(user=members[3], class_session=session, status=BookingStatus.CANCELLED),
        ]
    )
    db.commit()

    results = {row.session.id: row for row in list_sessions_with_free_spots(db)}

    booked = results[session.id]
    assert booked.confirmed_count == 2
    assert booked.free_spots == 2
    assert "free_spots" not in session.__table__.c

    empty = results[empty_session.id]
    assert empty.confirmed_count == 0
    assert empty.free_spots == 8
