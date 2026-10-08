"""Unit tests for admin cancellation review (HU-20 / RN-13)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import Booking, CancellationRequest, ClassSession, ClassType
from app.models.enums import (
    BookingStatus,
    CancellationStatus,
    RoleName,
    SessionStatus,
    SubscriptionStatus,
)
from app.core.exceptions import UnauthorizedError
from app.services import booking_service, cancellation_service
from app.services.auth_service import login
from tests.conftest import TEST_PASSWORD


def _make_class_session(
    db,
    make_user,
    *,
    capacity: int = 2,
    starts_at: datetime | None = None,
    name: str = "Fuerza RN-13",
) -> ClassSession:
    trainer = make_user(RoleName.TRAINER)
    class_type = ClassType(
        name=name,
        description="Clase de prueba RN-13.",
        extra_price_cents=0,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts_at or (datetime.now(timezone.utc) + timedelta(days=2)),
        capacity=capacity,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()
    return session


def _pending_request(db, member, subscription, reason: str = "Me voy") -> CancellationRequest:
    request = CancellationRequest(
        subscription_id=subscription.id,
        reason=reason,
        status=CancellationStatus.PENDING,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def test_rn13_approve_cancels_subscription_deactivates_user_and_future_bookings(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    other = make_user()
    plan = make_plan()
    subscription = make_subscription(member, plan)
    make_subscription(other, plan)
    admin = make_user(RoleName.ADMIN)
    request = _pending_request(db, member, subscription)

    future = _make_class_session(db, make_user, capacity=1, name="Futura")
    past = _make_class_session(
        db,
        make_user,
        starts_at=datetime.now(timezone.utc) - timedelta(days=3),
        name="Pasada",
    )
    soon = _make_class_session(
        db,
        make_user,
        capacity=1,
        starts_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        name="Pronto",
    )

    booking_service.book_session(db, user_id=member.id, class_session_id=future.id)
    booking_service.book_session(db, user_id=member.id, class_session_id=soon.id)
    # Past sessions cannot be booked via the service (RN-04); seed the row directly.
    past_seed = Booking(
        user_id=member.id,
        class_session_id=past.id,
        status=BookingStatus.CONFIRMED,
    )
    db.add(past_seed)
    db.commit()
    waitlisted = booking_service.book_session(
        db, user_id=other.id, class_session_id=future.id
    )
    assert waitlisted.booking.status == BookingStatus.WAITLISTED

    approved = cancellation_service.approve_cancellation_request(
        db, request_id=request.id, admin=admin
    )

    db.refresh(member)
    db.refresh(subscription)
    db.refresh(waitlisted.booking)
    future_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == member.id, Booking.class_session_id == future.id
        )
    )
    past_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == member.id, Booking.class_session_id == past.id
        )
    )
    soon_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == member.id, Booking.class_session_id == soon.id
        )
    )

    assert approved.status == CancellationStatus.APPROVED
    assert approved.reviewed_by == admin.id
    assert approved.reviewed_at is not None
    assert subscription.status == SubscriptionStatus.CANCELLED
    assert member.is_active is False
    assert member.deactivated_at is not None
    assert future_booking.status == BookingStatus.CANCELLED
    assert soon_booking.status == BookingStatus.CANCELLED
    assert past_booking.status == BookingStatus.CONFIRMED
    assert waitlisted.booking.status == BookingStatus.CONFIRMED


def test_rn13_reject_without_admin_notes_raises_422(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    request = _pending_request(db, member, subscription)

    with pytest.raises(ValidationAppError, match="notas"):
        cancellation_service.reject_cancellation_request(
            db, request_id=request.id, admin=admin, admin_notes="   "
        )

    db.refresh(member)
    db.refresh(subscription)
    db.refresh(request)
    assert request.status == CancellationStatus.PENDING
    assert member.is_active is True
    assert subscription.status == SubscriptionStatus.ACTIVE


def test_rn13_reject_keeps_member_and_subscription_active(
    db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    request = _pending_request(db, member, subscription)

    rejected = cancellation_service.reject_cancellation_request(
        db,
        request_id=request.id,
        admin=admin,
        admin_notes="Te esperamos el mes que viene",
    )

    db.refresh(member)
    db.refresh(subscription)
    assert rejected.status == CancellationStatus.REJECTED
    assert rejected.admin_notes == "Te esperamos el mes que viene"
    assert rejected.reviewed_by == admin.id
    assert member.is_active is True
    assert member.deactivated_at is None
    assert subscription.status == SubscriptionStatus.ACTIVE


def test_rn13_approved_member_cannot_log_in(db, make_user, make_plan, make_subscription):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    request = _pending_request(db, member, subscription)

    cancellation_service.approve_cancellation_request(
        db, request_id=request.id, admin=admin
    )

    with pytest.raises(UnauthorizedError):
        login(db, member.email, TEST_PASSWORD)


def test_approve_unknown_request_raises_404(db, make_user):
    admin = make_user(RoleName.ADMIN)

    with pytest.raises(NotFoundError, match="no existe"):
        cancellation_service.approve_cancellation_request(
            db, request_id=9999, admin=admin
        )


def test_approve_non_pending_raises_409(db, make_user, make_plan, make_subscription):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    request = CancellationRequest(
        subscription_id=subscription.id,
        reason="Ya vista",
        status=CancellationStatus.REJECTED,
        admin_notes="No",
    )
    db.add(request)
    db.commit()

    with pytest.raises(ConflictError, match="pendientes"):
        cancellation_service.approve_cancellation_request(
            db, request_id=request.id, admin=admin
        )


def test_list_filters_by_status(db, make_user, make_plan, make_subscription):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    pending = _pending_request(db, member, subscription, reason="Pendiente")
    rejected = CancellationRequest(
        subscription_id=subscription.id,
        reason="Rechazada",
        status=CancellationStatus.REJECTED,
        admin_notes="No",
    )
    db.add(rejected)
    db.commit()

    items, total = cancellation_service.list_cancellation_requests(
        db, status=CancellationStatus.PENDING
    )

    assert total == 1
    assert [item.id for item in items] == [pending.id]
    assert db.scalar(select(func.count()).select_from(CancellationRequest)) == 2
