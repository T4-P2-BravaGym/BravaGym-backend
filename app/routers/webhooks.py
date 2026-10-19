"""Stripe webhook endpoint (HU-29). No JWT — authenticity is the Stripe signature."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.openapi import error
from app.services import stripe_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/stripe",
    summary="Stripe webhook (Checkout)",
    description=(
        "Receives Stripe events. Verifies the Stripe-Signature header. "
        "On checkout.session.completed (payment_status=paid) marks the Brava "
        "payment as paid and stores provider_ref (HU-29)."
    ),
    responses={
        200: {
            "description": "Event acknowledged",
            "content": {
                "application/json": {"example": {"received": True}},
            },
        },
        400: error("Invalid payload or signature"),
        409: error("Checkout is not ready or session details do not match the payment"),
        503: error("STRIPE_WEBHOOK_SECRET not configured"),
    },
)
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    event = stripe_service.construct_webhook_event(payload, stripe_signature)
    stripe_service.handle_webhook_event(db, event)
    return {"received": True}
