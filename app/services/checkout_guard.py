"""Serialize payment changes and safely retire an active hosted checkout."""
import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ServiceUnavailableError
from app.models import Payment, PaymentCheckout
from app.models.enums import PaymentStatus

logger = logging.getLogger(__name__)
CHECKOUT_BUSY = "Hay un pago con tarjeta en curso. Espera su confirmación antes de continuar."


def lock_payment(db: Session, payment: Payment) -> None:
    # A real write acquires SQLite's writer lock (and a row lock on PostgreSQL).
    db.execute(update(Payment).where(Payment.id == payment.id).values(id=Payment.id))
    db.refresh(payment)


def retire_checkout(db: Session, payment: Payment) -> None:
    """Caller owns the payment lock. Never release stock on an uncertain outcome."""
    from app.services import stripe_service

    attempt = db.get(PaymentCheckout, payment.id)
    if attempt is None:
        return
    if payment.status != PaymentStatus.PENDING or not attempt.session_id:
        raise ConflictError(CHECKOUT_BUSY)
    try:
        sessions = stripe_service._stripe_client().v1.checkout.sessions
        session = sessions.retrieve(attempt.session_id)
        if session.status == "open":
            session = sessions.expire(attempt.session_id)
        if session.status != "expired":
            raise ConflictError(CHECKOUT_BUSY)
    except stripe_service.stripe.StripeError as exc:
        logger.warning("Could not expire checkout for payment %s", payment.id)
        raise ServiceUnavailableError(CHECKOUT_BUSY) from exc
    db.delete(attempt)
    db.flush()
