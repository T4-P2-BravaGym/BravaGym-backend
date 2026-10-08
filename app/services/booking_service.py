"""Book, cancel and list bookings (RN-01 to RN-07).

Capacity check and write happen in one transaction. Waitlist position is
computed from created_at order and never stored.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, contains_eager, joinedload

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Booking, ClassSession, ClassType, Payment
from app.models.enums import BookingStatus, PaymentStatus, SessionStatus
from app.models.types import utc_now
from app.services import subscription_service

logger = logging.getLogger(__name__)

NO_ACTIVE_SUBSCRIPTION = "Necesitas una suscripción activa para reservar."
NO_PERSONAL_TRAINING_PLAN = "Tu plan no incluye entrenamiento personal."
SESSION_NOT_FOUND = "Esta clase no existe."
SESSION_NOT_BOOKABLE = "No se puede reservar esta clase: ya ha pasado o está cancelada."
ALREADY_BOOKED = "Ya tienes una reserva en esta clase."
BOOKING_NOT_FOUND = "Esta reserva no existe."
BOOKING_ALREADY_CANCELLED = "Esta reserva ya está cancelada."
CANCEL_TOO_LATE = (
    "Solo puedes cancelar una reserva confirmada hasta 60 minutos antes del inicio."
)

CANCEL_DEADLINE_MINUTES = 60


@dataclass(frozen=True, slots=True)
class BookingWithPosition:
    """A booking plus its computed waitlist position (None unless waitlisted)."""

    booking: Booking
    waitlist_position: int | None


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _session_starts_at_naive(starts_at: datetime) -> datetime:
    return _as_naive_utc(starts_at)


def _is_past_session(starts_at: datetime, *, now: datetime | None = None) -> bool:
    current = _as_naive_utc(now if now is not None else utc_now())
    return _session_starts_at_naive(starts_at) <= current


def _minutes_until_start(starts_at: datetime, *, now: datetime | None = None) -> float:
    current = _as_naive_utc(now if now is not None else utc_now())
    delta = _session_starts_at_naive(starts_at) - current
    return delta.total_seconds() / 60


def _confirmed_count(db: Session, class_session_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.class_session_id == class_session_id,
                Booking.status == BookingStatus.CONFIRMED,
            )
        )
        or 0
    )


def waitlist_position_for(db: Session, booking: Booking) -> int | None:
    """1-based position among waitlisted bookings for the same session (by created_at, id)."""
    if booking.status != BookingStatus.WAITLISTED:
        return None
    position = db.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.class_session_id == booking.class_session_id,
            Booking.status == BookingStatus.WAITLISTED,
            or_(
                Booking.created_at < booking.created_at,
                and_(
                    Booking.created_at == booking.created_at,
                    Booking.id <= booking.id,
                ),
            ),
        )
    )
    return int(position or 0)



def _ensure_extra_class_payment(
    db: Session, booking: Booking, class_type: ClassType
) -> Payment | None:
    """RN-07: pending payment when a confirmed booking has an extra price."""
    if class_type.extra_price_cents <= 0:
        return None

    existing = db.scalar(
        select(Payment).where(
            Payment.booking_id == booking.id,
            Payment.status.in_((PaymentStatus.PENDING, PaymentStatus.PAID)),
        )
    )
    if existing is not None:
        return existing

    payment = Payment(
        user_id=booking.user_id,
        booking_id=booking.id,
        base_amount_cents=class_type.extra_price_cents,
        final_amount_cents=class_type.extra_price_cents,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    return payment


def _load_booking_with_session(db: Session, booking_id: int) -> Booking:
    booking = db.scalar(
        select(Booking)
        .options(
            joinedload(Booking.class_session).joinedload(ClassSession.class_type)
        )
        .where(Booking.id == booking_id)
    )
    assert booking is not None
    return booking


def _emit_session_updated(class_session_id: int) -> None:
    """RN-06: notify listeners when free spots / waitlist change.

    Websocket delivery (WS /ws/sessions/{id}) will hook here when that channel exists.
    """
    logger.info("Session %s updated after booking change", class_session_id)


def _promote_oldest_waitlisted(
    db: Session, *, class_session_id: int, class_type: ClassType
) -> Booking | None:
    """RN-06: oldest waitlisted booking (created_at, id) becomes confirmed."""
    promoted = db.scalar(
        select(Booking)
        .where(
            Booking.class_session_id == class_session_id,
            Booking.status == BookingStatus.WAITLISTED,
        )
        .order_by(Booking.created_at, Booking.id)
        .with_for_update()
        .limit(1)
    )
    if promoted is None:
        return None

    promoted.status = BookingStatus.CONFIRMED
    payment = _ensure_extra_class_payment(db, promoted, class_type)
    logger.info(
        "Promoted waitlisted booking %s on session %s to confirmed%s",
        promoted.id,
        class_session_id,
        f" (pending payment {payment.id})" if payment is not None else "",
    )
    return promoted


def book_session(db: Session, *, user_id: int, class_session_id: int) -> BookingWithPosition:
    """Create or reactivate a booking for a member (RN-01–04, RN-07, RN-08)."""
    subscription = subscription_service.get_active_subscription(db, user_id)
    if subscription is None:
        raise PermissionDeniedError(NO_ACTIVE_SUBSCRIPTION)

    session = db.scalar(
        select(ClassSession)
        .options(joinedload(ClassSession.class_type))
        .where(ClassSession.id == class_session_id)
        .with_for_update()
    )
    if session is None:
        raise NotFoundError(SESSION_NOT_FOUND)

    # RN-08: personal training only for plans that include it.
    if session.class_type.is_personal_training and not (
        subscription.plan.includes_personal_training
    ):
        raise PermissionDeniedError(NO_PERSONAL_TRAINING_PLAN)

    if session.status != SessionStatus.SCHEDULED or _is_past_session(session.starts_at):
        raise ConflictError(SESSION_NOT_BOOKABLE)

    existing = db.scalar(
        select(Booking)
        .where(
            Booking.user_id == user_id,
            Booking.class_session_id == class_session_id,
        )
        .with_for_update()
    )
    if existing is not None and existing.status != BookingStatus.CANCELLED:
        raise ConflictError(ALREADY_BOOKED)

    confirmed = _confirmed_count(db, class_session_id)
    new_status = (
        BookingStatus.CONFIRMED
        if confirmed < session.capacity
        else BookingStatus.WAITLISTED
    )

    if existing is not None:
        booking = existing
        booking.status = new_status
        booking.cancelled_at = None
        booking.created_at = utc_now()
    else:
        booking = Booking(
            user_id=user_id,
            class_session_id=class_session_id,
            status=new_status,
        )
        db.add(booking)

    db.flush()

    payment_id: int | None = None
    if new_status == BookingStatus.CONFIRMED:
        payment = _ensure_extra_class_payment(db, booking, session.class_type)
        if payment is not None:
            db.flush()
            payment_id = payment.id

    booking_id = booking.id
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.info(
            "Blocked duplicate booking for user %s on session %s",
            user_id,
            class_session_id,
        )
        raise ConflictError(ALREADY_BOOKED) from None

    booking = _load_booking_with_session(db, booking_id)
    position = waitlist_position_for(db, booking)
    logger.info(
        "User %s booked session %s as %s (booking %s%s)",
        user_id,
        class_session_id,
        new_status.value,
        booking.id,
        f", pending payment {payment_id}" if payment_id is not None else "",
    )
    return BookingWithPosition(booking=booking, waitlist_position=position)


def cancel_booking(
    db: Session,
    *,
    user_id: int,
    booking_id: int,
    now: datetime | None = None,
) -> BookingWithPosition:
    """Cancel the member's booking (RN-05, RN-06, RN-07 on waitlist promotion).

    Confirmed bookings require at least CANCEL_DEADLINE_MINUTES before starts_at.
    Leaving the waitlist is always allowed. Own-resource only (missing → 404).
    """
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.user_id == user_id)
        .with_for_update()
    )
    if booking is None:
        raise NotFoundError(BOOKING_NOT_FOUND)

    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError(BOOKING_ALREADY_CANCELLED)

    session = db.scalar(
        select(ClassSession)
        .options(joinedload(ClassSession.class_type))
        .where(ClassSession.id == booking.class_session_id)
        .with_for_update()
    )
    assert session is not None

    previous_status = booking.status
    if previous_status == BookingStatus.CONFIRMED:
        minutes_left = _minutes_until_start(session.starts_at, now=now)
        if minutes_left < CANCEL_DEADLINE_MINUTES:
            raise ConflictError(CANCEL_TOO_LATE)

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = _as_naive_utc(now if now is not None else utc_now())
    db.flush()

    promoted: Booking | None = None
    if previous_status == BookingStatus.CONFIRMED:
        promoted = _promote_oldest_waitlisted(
            db, class_session_id=session.id, class_type=session.class_type
        )
        if promoted is not None:
            db.flush()

    cancelled_id = booking.id
    session_id = session.id
    promoted_id = promoted.id if promoted is not None else None
    db.commit()

    booking = _load_booking_with_session(db, cancelled_id)
    _emit_session_updated(session_id)
    logger.info(
        "User %s cancelled booking %s (was %s)%s",
        user_id,
        cancelled_id,
        previous_status.value,
        f"; promoted booking {promoted_id}" if promoted_id is not None else "",
    )
    return BookingWithPosition(booking=booking, waitlist_position=None)


def _my_bookings_stmt(
    user_id: int,
    *,
    status: BookingStatus | None = None,
    upcoming: bool | None = None,
) -> Select:
    stmt = (
        select(Booking)
        .join(ClassSession, Booking.class_session_id == ClassSession.id)
        .options(
            contains_eager(Booking.class_session).joinedload(ClassSession.class_type)
        )
        .where(Booking.user_id == user_id)
    )
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if upcoming is True:
        stmt = stmt.where(ClassSession.starts_at >= utc_now())
    elif upcoming is False:
        stmt = stmt.where(ClassSession.starts_at < utc_now())
    return stmt.order_by(ClassSession.starts_at, Booking.id)


def list_my_bookings(
    db: Session,
    *,
    user_id: int,
    status: BookingStatus | None = None,
    upcoming: bool | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[BookingWithPosition], int]:
    """List the member's bookings with optional status / upcoming filters."""
    stmt = _my_bookings_stmt(user_id, status=status, upcoming=upcoming)
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)

    offset = (page - 1) * size
    bookings = db.scalars(stmt.offset(offset).limit(size)).unique().all()
    items = [
        BookingWithPosition(
            booking=booking,
            waitlist_position=waitlist_position_for(db, booking),
        )
        for booking in bookings
    ]
    return items, total
