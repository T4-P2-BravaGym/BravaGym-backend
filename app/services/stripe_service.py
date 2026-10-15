"""Stripe Checkout + webhook fulfillment (HU-29).

When STRIPE_SECRET_KEY is missing, callers must not create sessions — the API
falls back to simulated pay (HU-24). Business rules: docs/business-rules.md.
"""

from __future__ import annotations

import logging
from typing import Any

import stripe
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ServiceUnavailableError,
    ValidationAppError,
)
from app.models import Payment, User
from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.payment import CheckoutSessionOut, PaymentConcept
from app.services import payment_service

logger = logging.getLogger(__name__)

STRIPE_NOT_CONFIGURED = (
    "Stripe no está configurado. Usa el pago simulado o contacta con administración."
)
STRIPE_WEBHOOK_NOT_CONFIGURED = "El webhook de Stripe no está configurado."
INVALID_WEBHOOK_SIGNATURE = "Firma de Stripe no válida."
INVALID_WEBHOOK_PAYLOAD = "El cuerpo del webhook de Stripe no es válido."
MISSING_PAYMENT_METADATA = "La sesión de Stripe no incluye el pago de Brava."
CHECKOUT_NO_URL = "Stripe no devolvió una URL de Checkout."

CONCEPT_LABELS: dict[PaymentConcept, str] = {
    "subscription": "Cuota de plan",
    "booking": "Clase / reserva",
    "order": "Pedido tienda",
}


def stripe_is_enabled() -> bool:
    return get_settings().stripe_enabled


def _require_stripe_secret() -> str:
    settings = get_settings()
    if not settings.stripe_enabled or not settings.stripe_secret_key:
        raise ServiceUnavailableError(STRIPE_NOT_CONFIGURED)
    return settings.stripe_secret_key.strip()


def _stripe_client() -> stripe.StripeClient:
    return stripe.StripeClient(_require_stripe_secret())


def create_checkout_session(
    db: Session,
    member: User,
    payment_id: int,
    discount_code_text: str | None = None,
) -> CheckoutSessionOut:
    """Create a Stripe Checkout Session for a pending payment owned by the member."""
    settings = get_settings()
    _require_stripe_secret()

    payment = payment_service.get_own_payment_or_404(db, member.id, payment_id)
    if payment.status != PaymentStatus.PENDING:
        raise ConflictError(payment_service.PAYMENT_NOT_PENDING)

    payment_service.apply_optional_discount(db, payment, discount_code_text)
    db.commit()
    db.refresh(payment)

    concept = payment_service.payment_concept(payment)
    product_name = f"Brava · {CONCEPT_LABELS[concept]}"
    amount = payment.final_amount_cents

    client = _stripe_client()
    session = client.v1.checkout.sessions.create(
        params={
            "mode": "payment",
            "success_url": settings.stripe_success_url,
            "cancel_url": settings.stripe_cancel_url,
            "client_reference_id": str(payment.id),
            "line_items": [
                {
                    "quantity": 1,
                    "price_data": {
                        "currency": "eur",
                        "unit_amount": amount,
                        "product_data": {"name": product_name},
                    },
                }
            ],
            "metadata": {
                "payment_id": str(payment.id),
                "user_id": str(member.id),
            },
        }
    )

    checkout_url = getattr(session, "url", None)
    session_id = getattr(session, "id", None)
    if not checkout_url or not session_id:
        raise ValidationAppError(CHECKOUT_NO_URL)

    logger.info(
        "User %s started Stripe Checkout for payment %s (session_id=%s, amount_cents=%s)",
        member.id,
        payment.id,
        session_id,
        amount,
    )
    return CheckoutSessionOut(checkout_url=checkout_url, session_id=session_id)


def construct_webhook_event(payload: bytes, signature_header: str | None) -> stripe.Event:
    """Verify Stripe-Signature and return the Event. Invalid → 400."""
    settings = get_settings()
    secret = (settings.stripe_webhook_secret or "").strip()
    if not secret:
        raise ServiceUnavailableError(STRIPE_WEBHOOK_NOT_CONFIGURED)
    if not signature_header:
        raise BadRequestError(INVALID_WEBHOOK_SIGNATURE)

    try:
        return stripe.Webhook.construct_event(payload, signature_header, secret)
    except ValueError as exc:
        raise BadRequestError(INVALID_WEBHOOK_PAYLOAD) from exc
    except stripe.SignatureVerificationError as exc:
        raise BadRequestError(INVALID_WEBHOOK_SIGNATURE) from exc


def _session_payment_id(session: Any) -> int:
    metadata = getattr(session, "metadata", None) or {}
    if isinstance(metadata, dict):
        raw = metadata.get("payment_id")
    else:
        # Stripe SDK objects expose keys via mapping-style access.
        try:
            raw = metadata["payment_id"]
        except (KeyError, TypeError):
            raw = getattr(metadata, "payment_id", None)
    if raw is None:
        raw = getattr(session, "client_reference_id", None)
    if raw is None or str(raw).strip() == "":
        raise ValidationAppError(MISSING_PAYMENT_METADATA)
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationAppError(MISSING_PAYMENT_METADATA) from exc


def fulfill_checkout_session(db: Session, session: Any) -> Payment | None:
    """Mark the Brava payment paid from a Checkout Session object. Idempotent.

    Returns the payment when fulfillment ran or was skipped as already paid;
    returns None when the session is not yet paid (async methods).
    """
    payment_status = getattr(session, "payment_status", None)
    if payment_status != "paid":
        logger.info(
            "Skipping Stripe fulfill: session %s payment_status=%s",
            getattr(session, "id", None),
            payment_status,
        )
        return None

    payment_id = _session_payment_id(session)
    payment = payment_service.get_payment_or_404(db, payment_id)

    if payment.status == PaymentStatus.PAID:
        logger.info(
            "Stripe webhook idempotent: payment %s already paid (session=%s)",
            payment.id,
            getattr(session, "id", None),
        )
        return payment

    if payment.status != PaymentStatus.PENDING:
        raise ConflictError(payment_service.PAYMENT_NOT_PENDING)

    session_id = getattr(session, "id", None)
    payment = payment_service.mark_payment_paid(
        db,
        payment,
        method=PaymentMethod.STRIPE,
        provider_ref=str(session_id) if session_id else None,
    )
    logger.info(
        "Stripe webhook marked payment %s paid (provider_ref=%s, order_id=%s)",
        payment.id,
        payment.provider_ref,
        payment.order_id,
    )
    return payment


def handle_webhook_event(db: Session, event: stripe.Event) -> None:
    """Dispatch supported Checkout events. Unknown types are ignored (ACK 200)."""
    event_type = event["type"] if isinstance(event, dict) else event.type
    data_object = (
        event["data"]["object"]
        if isinstance(event, dict)
        else event.data.object
    )

    if event_type in (
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    ):
        fulfill_checkout_session(db, data_object)
        return

    logger.debug("Ignoring Stripe event type %s", event_type)
