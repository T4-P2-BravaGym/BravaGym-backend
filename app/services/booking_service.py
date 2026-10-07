"""Book and list bookings (RN-01 to RN-04, RN-07).

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
SESSION_NOT_FOUND = "Esta clase no existe."
SESSION_NOT_BOOKABLE = "No se puede reservar esta clase: ya ha pasado o está cancelada."
ALREADY_BOOKED = "Ya tienes una reserva en esta clase."


@dataclass(frozen=True, slots=True)
class BookingWithPosition:
    """A booking plus its computed waitlist position (None unless waitlisted)."""

    booking: Booking
    waitlist_position: int | None


def _session_starts_at_naive(starts_at: datetime) -> datetime:
    if starts_at.tzinfo is None:
        return starts_at
    return starts_at.astimezone(UTC).replace(tzinfo=None)


def _is_past_session(starts_at: datetime, *, now: datetime | None = None) -> bool:
    current = now if now is not None else utc_now()
    return _session_starts_at_naive(starts_at) <= current


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


def book_session(db: Session, *, user_id: int, class_session_id: int) -> BookingWithPosition:
    """Create or reactivate a booking for a member (RN-01–04, RN-07)."""
    if subscription_service.get_active_subscription(db, user_id) is None:
        raise PermissionDeniedError(NO_ACTIVE_SUBSCRIPTION)

    session = db.scalar(
        select(ClassSession)
        .options(joinedload(ClassSession.class_type))
        .where(ClassSession.id == class_session_id)
        .with_for_update()
    )
    if session is None:
        raise NotFoundError(SESSION_NOT_FOUND)

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
