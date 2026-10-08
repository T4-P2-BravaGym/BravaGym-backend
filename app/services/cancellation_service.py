"""Cancellation requests (RN-12). Approval (RN-13) is HU-20."""

import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import CancellationRequest, Subscription, User
from app.models.enums import CancellationStatus, SubscriptionStatus
from app.services.subscription_service import get_active_subscription

logger = logging.getLogger(__name__)

NO_ACTIVE_SUBSCRIPTION = "No tienes una suscripción activa."
ALREADY_PENDING = "Ya tienes una solicitud de baja pendiente."
NO_CANCELLATION_REQUEST = "No tienes ninguna solicitud de baja."


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
