"""Unit tests for booking_service (HU-12 / RN-01–04, RN-07)."""

from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Booking, ClassSession, ClassType, Payment
from app.models.enums import (
    BookingStatus,
    PaymentStatus,
    RoleName,
    SessionStatus,
    SubscriptionStatus,
)
from app.models.types import utc_now
from app.services import booking_service
from app.services.booking_service import (
    ALREADY_BOOKED,
    NO_ACTIVE_SUBSCRIPTION,
    SESSION_NOT_BOOKABLE,
    SESSION_NOT_FOUND,
)


def _make_session(
    db,
    make_user,
    *,
    capacity: int = 2,
    starts_at: datetime | None = None,
    status: SessionStatus = SessionStatus.SCHEDULED,
    extra_price_cents: int = 0,
    name: str = "Fuerza",
) -> ClassSession:
    trainer = make_user(RoleName.TRAINER)
    class_type = ClassType(
        name=name,
        description="Clase de prueba.",
        extra_price_cents=extra_price_cents,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts_at or (datetime.now(timezone.utc) + timedelta(days=1)),
        capacity=capacity,
        status=status,
    )
    db.add(session)
    db.commit()
    return session


def test_rn01_book_without_active_subscription_raises_403(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan(), status=SubscriptionStatus.CANCELLED)
    session = _make_session(db, make_user, name="Sin suscripción")

    with pytest.raises(PermissionDeniedError, match=NO_ACTIVE_SUBSCRIPTION):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )

    assert db.scalar(select(func.count()).select_from(Booking)) == 0


def test_rn01_book_with_no_subscription_at_all_raises_403(db, make_user):
    member = make_user()
    session = _make_session(db, make_user, name="Sin plan")

    with pytest.raises(PermissionDeniedError, match=NO_ACTIVE_SUBSCRIPTION):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )


def test_rn02_book_with_free_spots_is_confirmed(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(db, make_user, capacity=3, name="Con plazas")

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )

    assert result.booking.status == BookingStatus.CONFIRMED
    assert result.waitlist_position is None


def test_rn02_full_class_goes_to_waitlist_with_position(
    db, make_user, make_plan, make_subscription
):
    session = _make_session(db, make_user, capacity=1, name="Llena")
    plan = make_plan()

    first = make_user()
    make_subscription(first, plan)
    booking_service.book_session(db, user_id=first.id, class_session_id=session.id)

    second = make_user()
    make_subscription(second, plan)
    result = booking_service.book_session(
        db, user_id=second.id, class_session_id=session.id
    )

    assert result.booking.status == BookingStatus.WAITLISTED
    assert result.waitlist_position == 1

    third = make_user()
    make_subscription(third, plan)
    third_result = booking_service.book_session(
        db, user_id=third.id, class_session_id=session.id
    )
    assert third_result.booking.status == BookingStatus.WAITLISTED
    assert third_result.waitlist_position == 2


def test_rn03_duplicate_booking_raises_409(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(db, make_user, name="Duplicada")
    booking_service.book_session(db, user_id=member.id, class_session_id=session.id)

    with pytest.raises(ConflictError, match=ALREADY_BOOKED):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )

    assert db.scalar(select(func.count()).select_from(Booking)) == 1


def test_rn03_cancelled_booking_is_reactivated(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(db, make_user, capacity=2, name="Reactivar")
    first = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )
    booking = first.booking
    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = utc_now()
    db.commit()

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )

    assert result.booking.id == booking.id
    assert result.booking.status == BookingStatus.CONFIRMED
    assert result.booking.cancelled_at is None
    assert db.scalar(select(func.count()).select_from(Booking)) == 1


@freeze_time("2026-10-07 12:00:00")
def test_rn04_past_session_raises_409(db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(
        db,
        make_user,
        starts_at=datetime(2026, 10, 7, 11, 0, tzinfo=timezone.utc),
        name="Pasada",
    )

    with pytest.raises(ConflictError, match=SESSION_NOT_BOOKABLE):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )


def test_rn04_cancelled_session_raises_409(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(
        db, make_user, status=SessionStatus.CANCELLED, name="Cancelada"
    )

    with pytest.raises(ConflictError, match=SESSION_NOT_BOOKABLE):
        booking_service.book_session(
            db, user_id=member.id, class_session_id=session.id
        )


def test_book_missing_session_raises_404(db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())

    with pytest.raises(NotFoundError, match=SESSION_NOT_FOUND):
        booking_service.book_session(db, user_id=member.id, class_session_id=9999)


def test_rn07_confirmed_with_extra_price_creates_pending_payment(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(
        db, make_user, capacity=2, extra_price_cents=1200, name="Extra"
    )

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )

    payment = db.scalar(select(Payment).where(Payment.booking_id == result.booking.id))
    assert result.booking.status == BookingStatus.CONFIRMED
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING
    assert payment.base_amount_cents == 1200
    assert payment.final_amount_cents == 1200
    assert payment.user_id == member.id


def test_rn07_waitlisted_with_extra_price_does_not_create_payment(
    db, make_user, make_plan, make_subscription
):
    session = _make_session(
        db, make_user, capacity=1, extra_price_cents=1500, name="Extra waitlist"
    )
    plan = make_plan()

    first = make_user()
    make_subscription(first, plan)
    booking_service.book_session(db, user_id=first.id, class_session_id=session.id)

    second = make_user()
    make_subscription(second, plan)
    result = booking_service.book_session(
        db, user_id=second.id, class_session_id=session.id
    )

    assert result.booking.status == BookingStatus.WAITLISTED
    assert (
        db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.booking_id == result.booking.id)
        )
        == 0
    )


def test_rn07_zero_extra_price_creates_no_payment(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(db, make_user, extra_price_cents=0, name="Gratis")

    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )

    assert (
        db.scalar(
            select(func.count())
            .select_from(Payment)
            .where(Payment.booking_id == result.booking.id)
        )
        == 0
    )


def test_list_my_bookings_only_returns_own(
    db, make_user, make_plan, make_subscription
):
    plan = make_plan()
    session = _make_session(db, make_user, capacity=5, name="Listado")
    mine = make_user()
    other = make_user()
    make_subscription(mine, plan)
    make_subscription(other, plan)
    booking_service.book_session(db, user_id=mine.id, class_session_id=session.id)
    booking_service.book_session(db, user_id=other.id, class_session_id=session.id)

    items, total = booking_service.list_my_bookings(db, user_id=mine.id)

    assert total == 1
    assert items[0].booking.user_id == mine.id


# --- HU-13 / RN-05 / RN-06 -------------------------------------------------


def _book_confirmed(db, make_user, make_plan, make_subscription, **session_kwargs):
    member = make_user()
    make_subscription(member, make_plan())
    session = _make_session(db, make_user, **session_kwargs)
    result = booking_service.book_session(
        db, user_id=member.id, class_session_id=session.id
    )
    assert result.booking.status == BookingStatus.CONFIRMED
    return member, session, result.booking


@freeze_time("2026-10-07 12:00:00")
def test_rn05_cancel_confirmed_at_59_minutes_raises_409(
    db, make_user, make_plan, make_subscription
):
    member, session, booking = _book_confirmed(
        db,
        make_user,
        make_plan,
        make_subscription,
        starts_at=datetime(2026, 10, 7, 12, 59, tzinfo=timezone.utc),
        name="Cancel 59",
    )

    with pytest.raises(ConflictError, match=booking_service.CANCEL_TOO_LATE):
        booking_service.cancel_booking(db, user_id=member.id, booking_id=booking.id)

    db.refresh(booking)
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.cancelled_at is None


@freeze_time("2026-10-07 12:00:00")
def test_rn05_cancel_confirmed_at_60_minutes_succeeds(
    db, make_user, make_plan, make_subscription
):
    member, session, booking = _book_confirmed(
        db,
        make_user,
        make_plan,
        make_subscription,
        starts_at=datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc),
        name="Cancel 60",
    )

    result = booking_service.cancel_booking(
        db, user_id=member.id, booking_id=booking.id
    )

    assert result.booking.status == BookingStatus.CANCELLED
    assert result.booking.cancelled_at is not None
    assert result.waitlist_position is None


@freeze_time("2026-10-07 12:00:00")
def test_rn05_cancel_confirmed_at_61_minutes_succeeds(
    db, make_user, make_plan, make_subscription
):
    member, _session, booking = _book_confirmed(
        db,
        make_user,
        make_plan,
        make_subscription,
        starts_at=datetime(2026, 10, 7, 13, 1, tzinfo=timezone.utc),
        name="Cancel 61",
    )

    result = booking_service.cancel_booking(
        db, user_id=member.id, booking_id=booking.id
    )

    assert result.booking.status == BookingStatus.CANCELLED


@freeze_time("2026-10-07 12:30:00")
def test_rn05_leave_waitlist_always_allowed_under_one_hour(
    db, make_user, make_plan, make_subscription
):
    session = _make_session(
        db,
        make_user,
        capacity=1,
        starts_at=datetime(2026, 10, 7, 13, 0, tzinfo=timezone.utc),
        name="Salir espera",
    )
    plan = make_plan()

    first = make_user()
    make_subscription(first, plan)
    booking_service.book_session(db, user_id=first.id, class_session_id=session.id)

    waitlisted_member = make_user()
    make_subscription(waitlisted_member, plan)
    waitlisted = booking_service.book_session(
        db, user_id=waitlisted_member.id, class_session_id=session.id
    )
    assert waitlisted.booking.status == BookingStatus.WAITLISTED

    result = booking_service.cancel_booking(
        db, user_id=waitlisted_member.id, booking_id=waitlisted.booking.id
    )

    assert result.booking.status == BookingStatus.CANCELLED
    first_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == first.id, Booking.class_session_id == session.id
        )
    )
    assert first_booking.status == BookingStatus.CONFIRMED


@freeze_time("2026-10-07 12:00:00")
def test_rn06_cancel_confirmed_promotes_oldest_waitlisted(
    db, make_user, make_plan, make_subscription
):
    session = _make_session(
        db,
        make_user,
        capacity=1,
        starts_at=datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc),
        name="Promoción",
        extra_price_cents=900,
    )
    plan = make_plan()

    confirmed_member = make_user()
    make_subscription(confirmed_member, plan)
    confirmed = booking_service.book_session(
        db, user_id=confirmed_member.id, class_session_id=session.id
    )

    first_wait = make_user()
    make_subscription(first_wait, plan)
    first_wait_result = booking_service.book_session(
        db, user_id=first_wait.id, class_session_id=session.id
    )
    assert first_wait_result.booking.status == BookingStatus.WAITLISTED

    second_wait = make_user()
    make_subscription(second_wait, plan)
    second_wait_result = booking_service.book_session(
        db, user_id=second_wait.id, class_session_id=session.id
    )
    assert second_wait_result.waitlist_position == 2

    result = booking_service.cancel_booking(
        db, user_id=confirmed_member.id, booking_id=confirmed.booking.id
    )

    assert result.booking.status == BookingStatus.CANCELLED
    db.refresh(first_wait_result.booking)
    db.refresh(second_wait_result.booking)
    assert first_wait_result.booking.status == BookingStatus.CONFIRMED
    assert second_wait_result.booking.status == BookingStatus.WAITLISTED

    payment = db.scalar(
        select(Payment).where(Payment.booking_id == first_wait_result.booking.id)
    )
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING
    assert payment.base_amount_cents == 900


def test_cancel_other_members_booking_raises_404(
    db, make_user, make_plan, make_subscription
):
    owner, _session, booking = _book_confirmed(
        db, make_user, make_plan, make_subscription, name="Ajena"
    )
    other = make_user()
    make_subscription(other, make_plan(name="Otro plan"))

    with pytest.raises(NotFoundError, match=booking_service.BOOKING_NOT_FOUND):
        booking_service.cancel_booking(db, user_id=other.id, booking_id=booking.id)

    db.refresh(booking)
    assert booking.status == BookingStatus.CONFIRMED


def test_cancel_already_cancelled_raises_409(
    db, make_user, make_plan, make_subscription
):
    member, _session, booking = _book_confirmed(
        db,
        make_user,
        make_plan,
        make_subscription,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        name="Ya cancelada",
    )
    booking_service.cancel_booking(db, user_id=member.id, booking_id=booking.id)

    with pytest.raises(ConflictError, match=booking_service.BOOKING_ALREADY_CANCELLED):
        booking_service.cancel_booking(db, user_id=member.id, booking_id=booking.id)
