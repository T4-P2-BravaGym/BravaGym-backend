"""Unit tests for personal training (HU-14 / RN-08, RN-09)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationAppError
from app.models import Booking, ClassSession, ClassType
from app.models.enums import BookingStatus, RoleName, SessionStatus
from app.services import booking_service, session_service
from app.services.booking_service import NO_PERSONAL_TRAINING_PLAN
from app.services.session_service import (
    CLASS_TYPE_NOT_PERSONAL_TRAINING,
    PERSONAL_TRAINING_CAPACITY,
    PERSONAL_TRAINING_DURATION_MINUTES,
    PT_CLASS_TYPE_NOT_FOUND,
    TRAINER_OVERLAP,
)


def _make_pt_class_type(db, *, name: str = "Entrenamiento personal") -> ClassType:
    class_type = ClassType(
        name=name,
        description="Sesión individual.",
        is_personal_training=True,
    )
    db.add(class_type)
    db.commit()
    return class_type


def _make_regular_class_type(db, *, name: str = "Fuerza") -> ClassType:
    class_type = ClassType(name=name, description="Grupo.")
    db.add(class_type)
    db.commit()
    return class_type


def test_rn08_book_pt_without_plan_flag_raises_403(
    db, make_user, make_plan, make_subscription
):
    trainer = make_user(RoleName.TRAINER)
    pt_type = _make_pt_class_type(db)
    session = ClassSession(
        class_type=pt_type,
        trainer=trainer,
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=60,
        capacity=1,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()

    member = make_user()
    make_subscription(member, make_plan(includes_personal_training=False))

    with pytest.raises(PermissionDeniedError, match=NO_PERSONAL_TRAINING_PLAN):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )

    assert db.scalar(select(func.count()).select_from(Booking)) == 0


def test_rn08_book_pt_with_plan_flag_is_confirmed(
    db, make_user, make_plan, make_subscription
):
    trainer = make_user(RoleName.TRAINER)
    pt_type = _make_pt_class_type(db, name="PT confirmado")
    session = ClassSession(
        class_type=pt_type,
        trainer=trainer,
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
        duration_minutes=60,
        capacity=1,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()

    member = make_user()
    make_subscription(member, make_plan(includes_personal_training=True))

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )

    assert result.booking.status == BookingStatus.CONFIRMED
    assert result.waitlist_position is None


def test_rn08_regular_class_ignores_pt_plan_flag(
    db, make_user, make_plan, make_subscription
):
    trainer = make_user(RoleName.TRAINER)
    class_type = _make_regular_class_type(db)
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=datetime.now(timezone.utc) + timedelta(days=1),
        capacity=8,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()

    member = make_user()
    make_subscription(member, make_plan(includes_personal_training=False))

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )
    assert result.booking.status == BookingStatus.CONFIRMED


def test_create_pt_slot_forces_60_min_and_capacity_1(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _make_pt_class_type(db)
    starts = datetime(2026, 10, 10, 10, 0, tzinfo=timezone.utc)

    row = session_service.create_personal_training_slot(
        db, trainer_id=trainer.id, starts_at=starts
    )

    assert row.session.duration_minutes == PERSONAL_TRAINING_DURATION_MINUTES
    assert row.session.capacity == PERSONAL_TRAINING_CAPACITY
    assert row.free_spots == 1
    assert row.session.class_type.is_personal_training is True
    assert row.session.trainer_id == trainer.id


def test_create_pt_slot_rejects_non_pt_class_type(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    regular = _make_regular_class_type(db, name="No PT")

    with pytest.raises(ValidationAppError, match=CLASS_TYPE_NOT_PERSONAL_TRAINING):
        session_service.create_personal_training_slot(
            db,
            trainer_id=trainer.id,
            starts_at=datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc),
            class_type_id=regular.id,
        )


def test_create_pt_slot_without_pt_type_raises_404(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _make_regular_class_type(db, name="Solo grupo")

    with pytest.raises(NotFoundError, match=PT_CLASS_TYPE_NOT_FOUND):
        session_service.create_personal_training_slot(
            db,
            trainer_id=trainer.id,
            starts_at=datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc),
        )


def test_rn09_overlapping_pt_slot_raises_409(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _make_pt_class_type(db, name="PT solape")
    starts = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)

    session_service.create_personal_training_slot(
        db, trainer_id=trainer.id, starts_at=starts
    )

    with pytest.raises(ConflictError, match=TRAINER_OVERLAP):
        session_service.create_personal_training_slot(
            db,
            trainer_id=trainer.id,
            starts_at=starts + timedelta(minutes=30),
        )

    assert (
        db.scalar(select(func.count()).select_from(ClassSession)) == 1
    )
