"""Class types and sessions: free spots, CRUD, overlaps (RN-09), ownership (RN-10).

Free spots are never stored: free_spots = capacity - count(confirmed bookings).
See docs/er.md. Business rules RN-xx: docs/business-rules.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationAppError,
)
from app.models import Booking, ClassSession, ClassType, Payment, User
from app.models.enums import BookingStatus, PaymentStatus, RoleName, SessionStatus
from app.models.types import utc_now
from app.schemas.classes import ClassTypeCreate, ClassTypeUpdate, SessionCreate, SessionUpdate
from app.services.booking_service import waitlist_position_for

logger = logging.getLogger(__name__)

INVALID_DATE_RANGE = "El rango de fechas no es válido: 'from' debe ser anterior o igual a 'to'."
CLASS_TYPE_NOT_FOUND = "Este tipo de clase no existe."
CLASS_TYPE_INACTIVE = "Este tipo de clase no está activo."
CLASS_TYPE_NAME_TAKEN = "Ya existe un tipo de clase con ese nombre."
SESSION_NOT_FOUND = "Esta clase no existe."
SESSION_ALREADY_CANCELLED = "Esta clase ya está cancelada."
SESSION_OVERLAP = "Esta franja se solapa con otra de tus clases. Elige otra hora."
SESSION_NOT_OWNED = "No puedes modificar una clase de otra entrenadora."
SESSION_BOOKINGS_FORBIDDEN = "No tienes permiso para ver las reservas de esta clase."
TRAINER_ID_REQUIRED = "Indica la entrenadora de la clase (trainer_id)."
TRAINER_NOT_FOUND = "La entrenadora indicada no existe o no tiene rol de entrenadora."
CAPACITY_BELOW_CONFIRMED = (
    "El aforo no puede ser menor que el número de reservas confirmadas."
)


@dataclass(frozen=True, slots=True)
class SessionWithFreeSpots:
    """A class session plus seats derived from confirmed bookings."""

    session: ClassSession
    confirmed_count: int
    free_spots: int


def free_spots_from_capacity(capacity: int, confirmed_count: int) -> int:
    """Return remaining seats from capacity and confirmed bookings (never stored)."""
    return capacity - confirmed_count


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _session_end(starts_at: datetime, duration_minutes: int) -> datetime:
    return starts_at + timedelta(minutes=duration_minutes)


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


def _load_session_with_free_spots(db: Session, session_id: int) -> SessionWithFreeSpots:
    stmt = sessions_with_free_spots_stmt(scheduled_only=False).where(
        ClassSession.id == session_id
    )
    row = db.execute(stmt).unique().one_or_none()
    if row is None:
        raise NotFoundError(SESSION_NOT_FOUND)
    return _rows_to_sessions([row])[0]


def _get_active_class_type(db: Session, class_type_id: int) -> ClassType:
    class_type = db.get(ClassType, class_type_id)
    if class_type is None:
        raise NotFoundError(CLASS_TYPE_NOT_FOUND)
    if not class_type.is_active:
        raise ConflictError(CLASS_TYPE_INACTIVE)
    return class_type


def _assert_trainer_user(db: Session, trainer_id: int) -> User:
    trainer = db.scalar(
        select(User).options(joinedload(User.role)).where(User.id == trainer_id)
    )
    if (
        trainer is None
        or not trainer.is_active
        or trainer.role.name != RoleName.TRAINER
    ):
        raise ValidationAppError(TRAINER_NOT_FOUND)
    return trainer


def _resolve_trainer_id(db: Session, actor: User, trainer_id: int | None) -> int:
    if actor.role.name == RoleName.TRAINER:
        return actor.id
    if trainer_id is None:
        raise ValidationAppError(TRAINER_ID_REQUIRED)
    _assert_trainer_user(db, trainer_id)
    return trainer_id


def assert_can_manage_session(actor: User, session: ClassSession) -> None:
    """RN-10: only the session trainer or superadmin may edit / cancel."""
    if actor.role.name == RoleName.SUPERADMIN:
        return
    if actor.id == session.trainer_id:
        return
    raise PermissionDeniedError(SESSION_NOT_OWNED)


def assert_can_view_session_bookings(actor: User, session: ClassSession) -> None:
    """Trainer (own), admin or superadmin may list bookings for a session."""
    if actor.role.name in (RoleName.ADMIN, RoleName.SUPERADMIN):
        return
    if actor.role.name == RoleName.TRAINER and actor.id == session.trainer_id:
        return
    raise PermissionDeniedError(SESSION_BOOKINGS_FORBIDDEN)


def sessions_overlap(
    *,
    starts_a: datetime,
    duration_a: int,
    starts_b: datetime,
    duration_b: int,
) -> bool:
    """True when two half-open intervals [start, end) overlap."""
    start_a = _as_naive_utc(starts_a)
    start_b = _as_naive_utc(starts_b)
    end_a = _session_end(start_a, duration_a)
    end_b = _session_end(start_b, duration_b)
    return start_a < end_b and start_b < end_a


def _assert_no_overlap(
    db: Session,
    *,
    trainer_id: int,
    starts_at: datetime,
    duration_minutes: int,
    exclude_session_id: int | None = None,
) -> None:
    """RN-09: a trainer cannot have two scheduled overlapping sessions."""
    starts = _as_naive_utc(starts_at)
    ends = _session_end(starts, duration_minutes)

    stmt = select(ClassSession).where(
        ClassSession.trainer_id == trainer_id,
        ClassSession.status == SessionStatus.SCHEDULED,
    )
    if exclude_session_id is not None:
        stmt = stmt.where(ClassSession.id != exclude_session_id)

    for other in db.scalars(stmt).all():
        other_start = _as_naive_utc(other.starts_at)
        other_end = _session_end(other_start, other.duration_minutes)
        # Overlap if intervals intersect; also catch cases where SQL date compare
        # would be awkward with duration stored separately.
        if starts < other_end and other_start < ends:
            raise ConflictError(SESSION_OVERLAP)


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


# --- Class types (HU-11.1) -------------------------------------------------


def list_class_types(
    db: Session,
    *,
    active_only: bool = True,
    page: int = 1,
    size: int = 20,
) -> tuple[list[ClassType], int]:
    """List class types, optionally only active ones, with pagination."""
    stmt = select(ClassType)
    if active_only:
        stmt = stmt.where(ClassType.is_active.is_(True))
    stmt = stmt.order_by(ClassType.name, ClassType.id)

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = int(db.scalar(count_stmt) or 0)
    offset = (page - 1) * size
    items = list(db.scalars(stmt.offset(offset).limit(size)).all())
    return items, total


def get_class_type(db: Session, class_type_id: int) -> ClassType:
    class_type = db.get(ClassType, class_type_id)
    if class_type is None:
        raise NotFoundError(CLASS_TYPE_NOT_FOUND)
    return class_type


def create_class_type(db: Session, data: ClassTypeCreate) -> ClassType:
    class_type = ClassType(
        name=data.name.strip(),
        description=data.description,
        extra_price_cents=data.extra_price_cents,
        is_personal_training=data.is_personal_training,
        is_active=True,
    )
    db.add(class_type)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CLASS_TYPE_NAME_TAKEN) from None
    db.refresh(class_type)
    logger.info(
        "Created class type %s (personal_training=%s)",
        class_type.id,
        class_type.is_personal_training,
    )
    return class_type


def update_class_type(
    db: Session, class_type_id: int, data: ClassTypeUpdate
) -> ClassType:
    class_type = get_class_type(db, class_type_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()
    for field, value in changes.items():
        setattr(class_type, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CLASS_TYPE_NAME_TAKEN) from None
    db.refresh(class_type)
    logger.info("Updated class type %s", class_type.id)
    return class_type


def deactivate_class_type(db: Session, class_type_id: int) -> ClassType:
    """Soft-delete: set is_active=false (DELETE endpoint)."""
    class_type = get_class_type(db, class_type_id)
    if not class_type.is_active:
        return class_type
    class_type.is_active = False
    db.commit()
    db.refresh(class_type)
    logger.info("Deactivated class type %s", class_type.id)
    return class_type


# --- Sessions (HU-11.2 / HU-11.3) ------------------------------------------


def create_session(db: Session, actor: User, data: SessionCreate) -> SessionWithFreeSpots:
    """Create a scheduled session for a trainer (RN-09 overlap)."""
    class_type = _get_active_class_type(db, data.class_type_id)
    trainer_id = _resolve_trainer_id(db, actor, data.trainer_id)
    starts_at = _as_naive_utc(data.starts_at)

    _assert_no_overlap(
        db,
        trainer_id=trainer_id,
        starts_at=starts_at,
        duration_minutes=data.duration_minutes,
    )

    session = ClassSession(
        class_type_id=class_type.id,
        trainer_id=trainer_id,
        starts_at=starts_at,
        duration_minutes=data.duration_minutes,
        capacity=data.capacity,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()
    logger.info(
        "User %s created session %s for trainer %s (type %s)",
        actor.id,
        session.id,
        trainer_id,
        class_type.id,
    )
    return _load_session_with_free_spots(db, session.id)


def update_session(
    db: Session,
    actor: User,
    session_id: int,
    data: SessionUpdate,
) -> SessionWithFreeSpots:
    """Update a session (RN-09 overlap, RN-10 ownership)."""
    session = db.scalar(
        select(ClassSession)
        .options(joinedload(ClassSession.class_type))
        .where(ClassSession.id == session_id)
        .with_for_update()
    )
    if session is None:
        raise NotFoundError(SESSION_NOT_FOUND)

    assert_can_manage_session(actor, session)

    if session.status != SessionStatus.SCHEDULED:
        raise ConflictError(SESSION_ALREADY_CANCELLED)

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return _load_session_with_free_spots(db, session.id)

    if "class_type_id" in changes:
        class_type = _get_active_class_type(db, changes["class_type_id"])
        session.class_type_id = class_type.id

    if "starts_at" in changes and changes["starts_at"] is not None:
        session.starts_at = _as_naive_utc(changes["starts_at"])
    if "duration_minutes" in changes and changes["duration_minutes"] is not None:
        session.duration_minutes = changes["duration_minutes"]
    if "capacity" in changes and changes["capacity"] is not None:
        confirmed = _confirmed_count(db, session.id)
        if changes["capacity"] < confirmed:
            raise ConflictError(CAPACITY_BELOW_CONFIRMED)
        session.capacity = changes["capacity"]

    _assert_no_overlap(
        db,
        trainer_id=session.trainer_id,
        starts_at=session.starts_at,
        duration_minutes=session.duration_minutes,
        exclude_session_id=session.id,
    )

    db.commit()
    logger.info("User %s updated session %s", actor.id, session.id)
    return _load_session_with_free_spots(db, session.id)


def cancel_session(db: Session, actor: User, session_id: int) -> SessionWithFreeSpots:
    """Cancel a session, its bookings, and refund related extra-class payments (RN-10)."""
    session = db.scalar(
        select(ClassSession)
        .options(joinedload(ClassSession.class_type))
        .where(ClassSession.id == session_id)
        .with_for_update()
    )
    if session is None:
        raise NotFoundError(SESSION_NOT_FOUND)

    assert_can_manage_session(actor, session)

    if session.status == SessionStatus.CANCELLED:
        raise ConflictError(SESSION_ALREADY_CANCELLED)

    now = utc_now()
    session.status = SessionStatus.CANCELLED

    bookings = list(
        db.scalars(
            select(Booking)
            .where(
                Booking.class_session_id == session.id,
                Booking.status.in_(
                    (BookingStatus.CONFIRMED, BookingStatus.WAITLISTED)
                ),
            )
            .with_for_update()
        ).all()
    )
    booking_ids = [booking.id for booking in bookings]
    for booking in bookings:
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = now

    refunded = 0
    if booking_ids:
        payments = list(
            db.scalars(
                select(Payment)
                .where(
                    Payment.booking_id.in_(booking_ids),
                    Payment.status.in_(
                        (PaymentStatus.PENDING, PaymentStatus.PAID)
                    ),
                )
                .with_for_update()
            ).all()
        )
        for payment in payments:
            payment.status = PaymentStatus.REFUNDED
            refunded += 1

    db.commit()
    logger.info(
        "User %s cancelled session %s (%s bookings cancelled, %s payments refunded)",
        actor.id,
        session.id,
        len(booking_ids),
        refunded,
    )
    return _load_session_with_free_spots(db, session.id)


def list_session_bookings(
    db: Session,
    actor: User,
    session_id: int,
) -> list[tuple[Booking, int | None]]:
    """List confirmed and waitlisted bookings for a session (trainer/admin/superadmin)."""
    session = db.get(ClassSession, session_id)
    if session is None:
        raise NotFoundError(SESSION_NOT_FOUND)

    assert_can_view_session_bookings(actor, session)

    bookings = list(
        db.scalars(
            select(Booking)
            .options(joinedload(Booking.user))
            .where(
                Booking.class_session_id == session_id,
                Booking.status.in_(
                    (BookingStatus.CONFIRMED, BookingStatus.WAITLISTED)
                ),
            )
            .order_by(Booking.status, Booking.created_at, Booking.id)
        ).unique().all()
    )
    return [
        (booking, waitlist_position_for(db, booking)) for booking in bookings
    ]
