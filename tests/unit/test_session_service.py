"""HU-10 free-spots / filters and HU-11 overlap (RN-09) + ownership (RN-10)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ConflictError, PermissionDeniedError, ValidationAppError
from app.models import Booking, ClassSession, ClassType, Payment
from app.models.enums import BookingStatus, PaymentStatus, RoleName, SessionStatus
from app.schemas.classes import ClassTypeCreate, SessionCreate, SessionUpdate
from app.services import session_service
from app.services.session_service import (
    INVALID_DATE_RANGE,
    SESSION_NOT_OWNED,
    SESSION_OVERLAP,
    free_spots_from_capacity,
    list_sessions,
    list_sessions_with_free_spots,
    sessions_overlap,
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


# --- HU-11.2 / HU-11.4: overlap (RN-09) and ownership (RN-10) -----------------


def _make_class_type(db, name: str = "Fuerza HU-11") -> ClassType:
    class_type = ClassType(name=name, description="Tipo de prueba.")
    db.add(class_type)
    db.flush()
    return class_type


def test_sessions_overlap_half_open_intervals():
    start = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
    assert sessions_overlap(
        starts_a=start,
        duration_a=60,
        starts_b=start + timedelta(minutes=30),
        duration_b=60,
    )
    assert not sessions_overlap(
        starts_a=start,
        duration_a=60,
        starts_b=start + timedelta(minutes=60),
        duration_b=60,
    )


def test_rn09_create_overlapping_session_raises_409(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = _make_class_type(db)
    db.commit()
    starts = datetime(2026, 10, 8, 17, 0, tzinfo=timezone.utc)

    session_service.create_session(
        db,
        trainer,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=starts,
            duration_minutes=60,
            capacity=12,
        ),
    )

    with pytest.raises(ConflictError) as exc:
        session_service.create_session(
            db,
            trainer,
            SessionCreate(
                class_type_id=class_type.id,
                starts_at=starts + timedelta(minutes=30),
                duration_minutes=60,
                capacity=8,
            ),
        )
    assert exc.value.detail == SESSION_OVERLAP
    assert exc.value.status_code == 409


def test_rn09_adjacent_sessions_do_not_overlap(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = _make_class_type(db, name="Adyacente")
    db.commit()
    starts = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)

    first = session_service.create_session(
        db,
        trainer,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=starts,
            duration_minutes=60,
            capacity=10,
        ),
    )
    second = session_service.create_session(
        db,
        trainer,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=starts + timedelta(minutes=60),
            duration_minutes=60,
            capacity=10,
        ),
    )
    assert first.session.id != second.session.id


def test_rn09_cancelled_session_does_not_block_overlap(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = _make_class_type(db, name="Tras cancelar")
    db.commit()
    starts = datetime(2026, 10, 8, 11, 0, tzinfo=timezone.utc)

    created = session_service.create_session(
        db,
        trainer,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=starts,
            duration_minutes=60,
            capacity=10,
        ),
    )
    session_service.cancel_session(db, trainer, created.session.id)

    replacement = session_service.create_session(
        db,
        trainer,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=starts,
            duration_minutes=60,
            capacity=10,
        ),
    )
    assert replacement.session.status == SessionStatus.SCHEDULED


def test_rn10_other_trainer_cannot_update_raises_403(db, make_user):
    owner = make_user(RoleName.TRAINER)
    other = make_user(RoleName.TRAINER)
    class_type = _make_class_type(db, name="Propiedad")
    db.commit()

    created = session_service.create_session(
        db,
        owner,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            capacity=8,
        ),
    )

    with pytest.raises(PermissionDeniedError) as exc:
        session_service.update_session(
            db,
            other,
            created.session.id,
            SessionUpdate(capacity=6),
        )
    assert exc.value.detail == SESSION_NOT_OWNED
    assert exc.value.status_code == 403


def test_rn10_superadmin_can_update_other_trainer_session(db, make_user):
    owner = make_user(RoleName.TRAINER)
    superadmin = make_user(RoleName.SUPERADMIN)
    class_type = _make_class_type(db, name="Superadmin edita")
    db.commit()

    created = session_service.create_session(
        db,
        owner,
        SessionCreate(
            class_type_id=class_type.id,
            starts_at=datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            capacity=8,
        ),
    )
    updated = session_service.update_session(
        db,
        superadmin,
        created.session.id,
        SessionUpdate(capacity=6),
    )
    assert updated.session.capacity == 6


def test_rn10_cancel_cancels_bookings_and_refunds_payments(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    member = make_user(RoleName.MEMBER)
    class_type = ClassType(
        name="Extra con pago",
        description="Clase con precio extra.",
        extra_price_cents=1500,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc),
        capacity=4,
    )
    db.add(session)
    db.flush()
    booking = Booking(
        user=member,
        class_session=session,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.flush()
    payment = Payment(
        user_id=member.id,
        booking_id=booking.id,
        base_amount_cents=1500,
        final_amount_cents=1500,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()

    result = session_service.cancel_session(db, trainer, session.id)

    db.refresh(session)
    db.refresh(booking)
    db.refresh(payment)
    assert result.session.status == SessionStatus.CANCELLED
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at is not None
    assert payment.status == PaymentStatus.REFUNDED


def test_create_class_type_and_deactivate(db):
    created = session_service.create_class_type(
        db,
        ClassTypeCreate(name="Nuevo tipo", description="Desc", extra_price_cents=0),
    )
    assert created.is_active is True
    deactivated = session_service.deactivate_class_type(db, created.id)
    assert deactivated.is_active is False
