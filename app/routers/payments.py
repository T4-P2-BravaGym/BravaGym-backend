"""Controller for member payments (HU-24) and admin list/export/refund (HU-26).

Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember, require_roles
from app.core.openapi import error
from app.models import User
from app.models.enums import PaymentStatus, RoleName
from app.schemas.payment import PaymentConcept, PaymentOut, PaymentPage, PayRequest
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[
    User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))
]

MEMBER_AUTH_RESPONSES = {
    401: error("Missing, invalid or expired token"),
    403: error("Only members can use this endpoint"),
}

ADMIN_AUTH_RESPONSES = {
    401: error("Missing, invalid or expired token"),
    403: error("Only admin or superadmin can use this endpoint"),
}


@router.get(
    "/me",
    response_model=PaymentPage,
    summary="List my payments",
    description=(
        "Returns the authenticated member's payments, newest first. "
        "Filter by status. Amounts are always in cents."
    ),
    responses=MEMBER_AUTH_RESPONSES,
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


@router.get(
    "",
    response_model=PaymentPage,
    summary="List all payments (admin)",
    description=(
        "Paginated admin list of payments, newest first. "
        "Filter by status, created_at range (from/to inclusive), user_id and concept."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        422: {"description": "Invalid date range (from after to) or query parameters"},
    },
)
def list_payments(
    admin: CurrentAdmin,
    db: DbSession,
    status: Annotated[
        PaymentStatus | None,
        Query(description="Filter by payment status"),
    ] = None,
    from_: Annotated[
        datetime | None,
        Query(alias="from", description="Inclusive start of created_at range (UTC)"),
    ] = None,
    to: Annotated[
        datetime | None,
        Query(description="Inclusive end of created_at range (UTC)"),
    ] = None,
    user_id: Annotated[
        int | None, Query(ge=1, description="Filter by member user id")
    ] = None,
    concept: Annotated[
        PaymentConcept | None,
        Query(description="Filter by derived concept: subscription, booking or order"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaymentPage:
    del admin  # role gate only
    payments, total = payment_service.list_payments(
        db,
        status=status,
        from_=from_,
        to=to,
        user_id=user_id,
        concept=concept,
        page=page,
        size=size,
    )
    return PaymentPage(
        items=[PaymentOut.from_payment(payment) for payment in payments],
        total=total,
        page=page,
        size=size,
    )


@router.get(
    "/export",
    summary="Export payments as CSV (admin)",
    description=(
        "Downloads a CSV with the same filters as GET /payments (no pagination). "
        "Header row plus one row per payment. Amounts are in cents."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        200: {
            "content": {"text/csv": {}},
            "description": "CSV file with payment rows",
        },
        422: {"description": "Invalid date range (from after to) or query parameters"},
    },
)
def export_payments(
    admin: CurrentAdmin,
    db: DbSession,
    status: Annotated[
        PaymentStatus | None,
        Query(description="Filter by payment status"),
    ] = None,
    from_: Annotated[
        datetime | None,
        Query(alias="from", description="Inclusive start of created_at range (UTC)"),
    ] = None,
    to: Annotated[
        datetime | None,
        Query(description="Inclusive end of created_at range (UTC)"),
    ] = None,
    user_id: Annotated[
        int | None, Query(ge=1, description="Filter by member user id")
    ] = None,
    concept: Annotated[
        PaymentConcept | None,
        Query(description="Filter by derived concept: subscription, booking or order"),
    ] = None,
) -> StreamingResponse:
    del admin  # role gate only
    payments = payment_service.list_payments_for_export(
        db,
        status=status,
        from_=from_,
        to=to,
        user_id=user_id,
        concept=concept,
    )
    return StreamingResponse(
        payment_service.iter_payments_csv(payments),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="payments.csv"'},
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
        **MEMBER_AUTH_RESPONSES,
        404: error("Payment does not exist or is not yours"),
        409: error("Payment is not pending (already paid or refunded)"),
        422: {
            "description": "Discount code unknown, inactive, out of dates or used up"
        },
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


@router.post(
    "/{payment_id}/refund",
    response_model=PaymentOut,
    summary="Refund a paid payment (admin)",
    description=(
        "Marks a paid payment as refunded (RN-16). Only admin or superadmin. "
        "The change is logged. Pending, failed or already refunded payments return 409."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        404: error("Payment not found"),
        409: error("Payment is not in paid status"),
    },
)
def refund_payment(
    payment_id: int,
    admin: CurrentAdmin,
    db: DbSession,
) -> PaymentOut:
    payment = payment_service.refund_payment(db, admin, payment_id)
    return PaymentOut.from_payment(payment)
