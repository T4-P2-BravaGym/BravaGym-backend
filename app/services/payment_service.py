"""Simulated payment for members (HU-24, RN-14 to RN-16). Amounts are computed on the server.

Admin list/export/refund belong to HU-26 and stay out of this module for now.
Business rules RN-xx: docs/business-rules.md.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Payment, User
from app.models.enums import PaymentStatus
from app.models.types import utc_now
from app.services import discount_service

logger = logging.getLogger(__name__)

PAYMENT_NOT_FOUND = "No existe ese pago."
PAYMENT_NOT_PENDING = "Este pago ya no está pendiente."


def apply_discount_cents(base_amount_cents: int, percent_off: int) -> int:
    """RN-15: final = base × (100 − percent_off) / 100, rounded to the nearest cent (half up)."""
    return (base_amount_cents * (100 - percent_off) + 50) // 100


def _payment_query():
    """Load the discount code relationship so PaymentOut can expose the code text."""
    return select(Payment).options(joinedload(Payment.discount_code))


def list_my_payments(
    db: Session,
    *,
    user_id: int,
    status: PaymentStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Payment], int]:
    """Member's own payments, newest first. Optional status filter. Returns (page, total)."""
    filters = [Payment.user_id == user_id]
    if status is not None:
        filters.append(Payment.status == status)

    total = db.scalar(select(func.count(Payment.id)).where(*filters)) or 0
    payments = db.scalars(
        _payment_query()
        .where(*filters)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).unique().all()
    return list(payments), int(total)


def _get_own_payment_or_404(db: Session, user_id: int, payment_id: int) -> Payment:
    """404 if missing or not owned by this member (no IDOR leak)."""
    payment = db.scalar(_payment_query().where(Payment.id == payment_id, Payment.user_id == user_id))
    if payment is None:
        raise NotFoundError(PAYMENT_NOT_FOUND)
    return payment


def pay_payment(
    db: Session,
    member: User,
    payment_id: int,
    discount_code_text: str | None = None,
) -> Payment:
    """RN-16: pending → paid. Optional discount via discount_service.get_valid_code (RN-14, RN-15)."""
    payment = _get_own_payment_or_404(db, member.id, payment_id)

    if payment.status != PaymentStatus.PENDING:
        raise ConflictError(PAYMENT_NOT_PENDING)

    if discount_code_text:
        code = discount_service.get_valid_code(db, discount_code_text)
        payment.discount_code_id = code.id
        payment.final_amount_cents = apply_discount_cents(payment.base_amount_cents, code.percent_off)
    else:
        payment.discount_code_id = None
        payment.final_amount_cents = payment.base_amount_cents

    payment.status = PaymentStatus.PAID
    payment.paid_at = utc_now()
    db.commit()
    db.refresh(payment)

    # Re-load with relationship for the response schema.
    payment = _get_own_payment_or_404(db, member.id, payment.id)
    logger.info(
        "User %s paid payment %s (final_amount_cents=%s, discount_code_id=%s)",
        member.id,
        payment.id,
        payment.final_amount_cents,
        payment.discount_code_id,
    )
    return payment
