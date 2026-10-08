"""Cancellation requests: member create (RN-12) and admin review (RN-13)."""

from __future__ import annotations

import logging

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import CancellationRequest, Subscription, User
from app.models.enums import CancellationStatus, SubscriptionStatus
from app.models.types import utc_now
from app.services import booking_service
from app.services.subscription_service import get_active_subscription

logger = logging.getLogger(__name__)

NO_ACTIVE_SUBSCRIPTION = "No tienes una suscripción activa."
ALREADY_PENDING = "Ya tienes una solicitud de baja pendiente."
NO_CANCELLATION_REQUEST = "No tienes ninguna solicitud de baja."
REQUEST_NOT_FOUND = "Esta solicitud de baja no existe."
REQUEST_NOT_PENDING = "Solo se pueden revisar solicitudes pendientes."
ADMIN_NOTES_REQUIRED = "Las notas de administración son obligatorias al rechazar."


def get_pending_for_subscription(db: Session, subscription_id: int) -> CancellationRequest | None:
    return db.scalar(
        select(CancellationRequest).where(
            CancellationRequest.subscription_id == subscription_id,
            CancellationRequest.status == CancellationStatus.PENDING,
        )
    )


def get_my_cancellation_request(db: Session, user_id: int) -> CancellationRequest:
    """Return the member's most recent cancellation request, or 404 if none."""
    request = db.scalar(
        select(CancellationRequest)
        .join(Subscription, CancellationRequest.subscription_id == Subscription.id)
        .where(Subscription.user_id == user_id)
        .order_by(CancellationRequest.requested_at.desc(), CancellationRequest.id.desc())
    )
    if request is None:
        raise NotFoundError(NO_CANCELLATION_REQUEST)
    return request


def create_cancellation_request(db: Session, user: User, reason: str) -> CancellationRequest:
    """Create a pending cancellation request. The member stays active (RN-12)."""
    subscription = get_active_subscription(db, user.id)
    if subscription is None:
        raise NotFoundError(NO_ACTIVE_SUBSCRIPTION)

    if get_pending_for_subscription(db, subscription.id) is not None:
        raise ConflictError(ALREADY_PENDING)

    request = CancellationRequest(
        subscription_id=subscription.id,
        reason=reason,
        status=CancellationStatus.PENDING,
    )
    db.add(request)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if get_pending_for_subscription(db, subscription.id) is None:
            raise
        logger.info(
            "Blocked a second pending cancellation for user %s (subscription %s)",
            user.id,
            subscription.id,
        )
        raise ConflictError(ALREADY_PENDING) from None

    db.refresh(request)
    db.refresh(user)

    assert user.is_active is True
    assert subscription.status == SubscriptionStatus.ACTIVE

    logger.info(
        "User %s created cancellation request %s for subscription %s",
        user.id,
        request.id,
        subscription.id,
    )
    return request


def _list_stmt(*, status: CancellationStatus | None = None) -> Select:
    stmt = select(CancellationRequest)
    if status is not None:
        stmt = stmt.where(CancellationRequest.status == status)
    return stmt.order_by(
        CancellationRequest.requested_at.desc(), CancellationRequest.id.desc()
    )


def list_cancellation_requests(
    db: Session,
    *,
    status: CancellationStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[CancellationRequest], int]:
    """Paginated admin list, newest first. Optional status filter."""
    stmt = _list_stmt(status=status)
    total = int(
        db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    )
    offset = (page - 1) * size
    items = list(db.scalars(stmt.offset(offset).limit(size)).all())
    return items, total


def _get_pending_request_for_review(db: Session, request_id: int) -> CancellationRequest:
    request = db.scalar(
        select(CancellationRequest)
        .where(CancellationRequest.id == request_id)
        .with_for_update()
    )
    if request is None:
        raise NotFoundError(REQUEST_NOT_FOUND)
    if request.status != CancellationStatus.PENDING:
        raise ConflictError(REQUEST_NOT_PENDING)
    return request


def _load_subscription_and_member(
    db: Session, subscription_id: int
) -> tuple[Subscription, User]:
    subscription = db.scalar(
        select(Subscription)
        .where(Subscription.id == subscription_id)
        .with_for_update()
    )
    assert subscription is not None
    member = db.scalar(
        select(User).where(User.id == subscription.user_id).with_for_update()
    )
    assert member is not None
    return subscription, member


def approve_cancellation_request(
    db: Session,
    *,
    request_id: int,
    admin: User,
    admin_notes: str | None = None,
) -> CancellationRequest:
    """Approve a pending request in one transaction (RN-13).

    Sets the subscription to cancelled, deactivates the member, cancels future
    bookings (reusing HU-13 / RN-06 waitlist promotion), then marks the request
    approved.
    """
    request = _get_pending_request_for_review(db, request_id)
    subscription, member = _load_subscription_and_member(db, request.subscription_id)
    now = utc_now()

    subscription.status = SubscriptionStatus.CANCELLED
    member.is_active = False
    member.deactivated_at = now

    affected_sessions = booking_service.cancel_future_bookings_for_user(
        db, user_id=member.id, now=now
    )

    request.status = CancellationStatus.APPROVED
    request.reviewed_by = admin.id
    request.reviewed_at = now
    if admin_notes is not None:
        request.admin_notes = admin_notes

    db.commit()
    db.refresh(request)

    booking_service.notify_sessions_updated(affected_sessions)

    logger.info(
        "Admin %s approved cancellation request %s "
        "(user %s, subscription %s, %s sessions updated)",
        admin.id,
        request.id,
        member.id,
        subscription.id,
        len(affected_sessions),
    )
    return request


def reject_cancellation_request(
    db: Session,
    *,
    request_id: int,
    admin: User,
    admin_notes: str,
) -> CancellationRequest:
    """Reject a pending request. admin_notes is required (RN-13)."""
    notes = (admin_notes or "").strip()
    if not notes:
        raise ValidationAppError(ADMIN_NOTES_REQUIRED)

    request = _get_pending_request_for_review(db, request_id)
    subscription, member = _load_subscription_and_member(db, request.subscription_id)
    now = utc_now()

    request.status = CancellationStatus.REJECTED
    request.admin_notes = notes
    request.reviewed_by = admin.id
    request.reviewed_at = now

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationAppError(ADMIN_NOTES_REQUIRED) from None

    db.refresh(request)
    db.refresh(member)
    db.refresh(subscription)

    assert member.is_active is True
    assert subscription.status == SubscriptionStatus.ACTIVE

    logger.info(
        "Admin %s rejected cancellation request %s (user %s)",
        admin.id,
        request.id,
        member.id,
    )
    return request
