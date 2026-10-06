"""HU-10.1 free-spots formula and HU-10.3 filter / pagination checks."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ValidationAppError
from app.models import Booking, ClassSession, ClassType
from app.models.enums import BookingStatus, RoleName, SessionStatus
from app.services.session_service import (
    INVALID_DATE_RANGE,
    free_spots_from_capacity,
    list_sessions,
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


def _seed_schedule(db, make_user):
    trainer_a = make_user(RoleName.TRAINER)
    trainer_b = make_user(RoleName.TRAINER)
    strength = ClassType(name="Fuerza", description="Fuerza básica.")
    olympic = ClassType(
        name="Halterofilia",
        description="Taller con precio extra.",
        extra_price_cents=1200,
    )
    db.add_all([strength, olympic])
    db.flush()

    base = datetime(2026, 10, 6, 8, 0, tzinfo=timezone.utc)
    open_strength = ClassSession(
        class_type=strength,
        trainer=trainer_a,
        starts_at=base,
        capacity=4,
    )
    full_strength = ClassSession(
        class_type=strength,
        trainer=trainer_a,
        starts_at=base + timedelta(hours=2),
        capacity=2,
    )
    olympic_session = ClassSession(
        class_type=olympic,
        trainer=trainer_b,
        starts_at=base + timedelta(days=1),
        capacity=8,
    )
    cancelled = ClassSession(
        class_type=strength,
        trainer=trainer_a,
        starts_at=base + timedelta(days=2),
        capacity=10,
        status=SessionStatus.CANCELLED,
    )
    outside_range = ClassSession(
        class_type=strength,
        trainer=trainer_b,
        starts_at=base + timedelta(days=10),
        capacity=12,
    )
    db.add_all([open_strength, full_strength, olympic_session, cancelled, outside_range])
    db.flush()

    members = [make_user(RoleName.MEMBER) for _ in range(2)]
    db.add_all(
        [
            Booking(user=members[0], class_session=full_strength, status=BookingStatus.CONFIRMED),
            Booking(user=members[1], class_session=full_strength, status=BookingStatus.CONFIRMED),
        ]
    )
    db.commit()

    return {
        "trainer_a": trainer_a,
        "trainer_b": trainer_b,
        "strength": strength,
        "olympic": olympic,
        "open_strength": open_strength,
        "full_strength": full_strength,
        "olympic_session": olympic_session,
        "cancelled": cancelled,
        "outside_range": outside_range,
        "base": base,
    }


def test_list_sessions_filters_by_from_to_and_excludes_cancelled(db, make_user):
    data = _seed_schedule(db, make_user)
    base = data["base"]

    rows, total = list_sessions(
        db,
        from_=base,
        to=base + timedelta(days=2),
        page=1,
        size=20,
    )

    ids = {row.session.id for row in rows}
    assert total == 3
    assert data["open_strength"].id in ids
    assert data["full_strength"].id in ids
    assert data["olympic_session"].id in ids
    assert data["cancelled"].id not in ids
    assert data["outside_range"].id not in ids


def test_list_sessions_only_available_hides_full_sessions(db, make_user):
    data = _seed_schedule(db, make_user)
    base = data["base"]

    rows, total = list_sessions(
        db,
        from_=base,
        to=base + timedelta(days=2),
        only_available=True,
        page=1,
        size=20,
    )

    ids = {row.session.id for row in rows}
    by_id = {row.session.id: row for row in rows}

    assert total == 2
    assert data["full_strength"].id not in ids
    assert by_id[data["open_strength"].id].free_spots == 4
    assert by_id[data["olympic_session"].id].free_spots == 8


def test_list_sessions_filters_by_class_type_and_trainer(db, make_user):
    data = _seed_schedule(db, make_user)

    by_type, total_type = list_sessions(db, class_type_id=data["olympic"].id)
    assert total_type == 1
    assert by_type[0].session.id == data["olympic_session"].id
    assert by_type[0].session.class_type.extra_price_cents == 1200

    by_trainer, total_trainer = list_sessions(db, trainer_id=data["trainer_b"].id)
    assert total_trainer == 2
    assert {row.session.id for row in by_trainer} == {
        data["olympic_session"].id,
        data["outside_range"].id,
    }


def test_list_sessions_paginates(db, make_user):
    data = _seed_schedule(db, make_user)
    base = data["base"]

    page1, total = list_sessions(db, from_=base, to=base + timedelta(days=2), page=1, size=2)
    page2, total2 = list_sessions(db, from_=base, to=base + timedelta(days=2), page=2, size=2)

    assert total == total2 == 3
    assert len(page1) == 2
    assert len(page2) == 1
    assert {row.session.id for row in page1}.isdisjoint({row.session.id for row in page2})


def test_list_sessions_rejects_inverted_date_range(db, make_user):
    _seed_schedule(db, make_user)
    with pytest.raises(ValidationAppError) as exc:
        list_sessions(
            db,
            from_=datetime(2026, 10, 10, tzinfo=timezone.utc),
            to=datetime(2026, 10, 1, tzinfo=timezone.utc),
        )
    assert exc.value.detail == INVALID_DATE_RANGE
    assert exc.value.status_code == 422
