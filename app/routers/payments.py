"""Controller for member payments (HU-24). Admin list/export/refund stay for HU-26.

Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember
from app.models.enums import PaymentStatus
from app.schemas.payment import PaymentOut, PaymentPage, PayRequest
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}


@router.get(
    "/me",
    response_model=PaymentPage,
    summary="List my payments",
    description=(
        "Returns the authenticated member's payments, newest first. "
        "Filter by status. Amounts are always in cents."
    ),
    responses=AUTH_RESPONSES,
)
def list_my_payments(
    member: CurrentMember,
    db: DbSession,
    status: Annotated[
        PaymentStatus | None,
        Query(description="Filter by payment status"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaymentPage:
    payments, total = payment_service.list_my_payments(
        db,
        user_id=member.id,
        status=status,
        page=page,
        size=size,
    )
    return PaymentPage(
        items=[PaymentOut.from_payment(payment) for payment in payments],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/{payment_id}/pay",
    response_model=PaymentOut,
    summary="Pay a pending payment (simulated)",
    description=(
        "Marks the member's own pending payment as paid (RN-16). "
        "Optional discount_code applies RN-14 and RN-15. "
        "The final amount is computed on the server; the client never sends prices."
    ),
    responses={
        **AUTH_RESPONSES,
        404: {"description": "Payment does not exist or is not yours"},
        409: {"description": "Payment is not pending (already paid or refunded)"},
        422: {"description": "Discount code unknown, inactive, out of dates or used up"},
    },
)
def pay_payment(
    payment_id: int,
    member: CurrentMember,
    db: DbSession,
    data: PayRequest | None = None,
) -> PaymentOut:
    payload = data or PayRequest()
    payment = payment_service.pay_payment(
        db,
        member,
        payment_id,
        discount_code_text=payload.discount_code,
    )
    return PaymentOut.from_payment(payment)
