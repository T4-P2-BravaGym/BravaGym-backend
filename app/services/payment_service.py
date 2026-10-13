"""Simulated payments: member pay (HU-24) and admin list/export/refund (HU-26, RN-14 to RN-16).

Amounts are computed on the server. Business rules RN-xx: docs/business-rules.md.
"""
import csv
import io
import logging
from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import Order, Payment, User
from app.models.enums import OrderStatus, PaymentStatus
from app.models.types import utc_now
from app.schemas.payment import PaymentConcept
from app.services import discount_service

logger = logging.getLogger(__name__)

PAYMENT_NOT_FOUND = "No existe ese pago."
PAYMENT_NOT_PENDING = "Este pago ya no está pendiente."
PAYMENT_NOT_PAID = "Solo se puede reembolsar un pago que esté pagado."
ORDER_NOT_FOUND = "No existe el pedido de este pago."
INVALID_DATE_RANGE = (
    "El rango de fechas no es válido: 'from' debe ser anterior o igual a 'to'."
)

CSV_COLUMNS = (
    "id",
    "user_id",
    "concept",
    "subscription_id",
    "booking_id",
    "order_id",
    "discount_code",
    "base_amount_cents",
    "final_amount_cents",
    "status",
    "method",
    "created_at",
    "paid_at",
)


def apply_discount_cents(base_amount_cents: int, percent_off: int) -> int:
    """RN-15: final = base × (100 − percent_off) / 100, rounded to the nearest cent (half up)."""
    return (base_amount_cents * (100 - percent_off) + 50) // 100


def payment_concept(payment: Payment) -> PaymentConcept:
    """Derive concept from the single FK set on the payment (never stored)."""
    if payment.subscription_id is not None:
        return "subscription"
    if payment.booking_id is not None:
        return "booking"
    if payment.order_id is not None:
        return "order"
    raise ValueError("Payment must reference exactly one concept")


def _payment_query():
    """Load the discount code relationship so PaymentOut can expose the code text."""
    return select(Payment).options(joinedload(Payment.discount_code))


def _concept_filter(concept: PaymentConcept) -> ColumnElement[bool]:
    if concept == "subscription":
        return Payment.subscription_id.is_not(None)
    if concept == "booking":
        return Payment.booking_id.is_not(None)
    return Payment.order_id.is_not(None)


def _admin_filters(
    *,
    status: PaymentStatus | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    user_id: int | None = None,
    concept: PaymentConcept | None = None,
) -> list[ColumnElement[bool]]:
    """Shared filters for admin list and CSV export (created_at range is inclusive)."""
    if from_ is not None and to is not None and from_ > to:
        raise ValidationAppError(INVALID_DATE_RANGE)

    filters: list[ColumnElement[bool]] = []
    if status is not None:
        filters.append(Payment.status == status)
    if from_ is not None:
        filters.append(Payment.created_at >= from_)
    if to is not None:
        filters.append(Payment.created_at <= to)
    if user_id is not None:
        filters.append(Payment.user_id == user_id)
    if concept is not None:
        filters.append(_concept_filter(concept))
    return filters


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


def list_payments(
    db: Session,
    *,
    status: PaymentStatus | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    user_id: int | None = None,
    concept: PaymentConcept | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Payment], int]:
    """Admin: all payments with optional filters, newest first. Returns (page, total)."""
    filters = _admin_filters(
        status=status, from_=from_, to=to, user_id=user_id, concept=concept
    )
    count_stmt = select(func.count(Payment.id))
    query = _payment_query()
    if filters:
        count_stmt = count_stmt.where(*filters)
        query = query.where(*filters)

    total = db.scalar(count_stmt) or 0
    payments = db.scalars(
        query.order_by(Payment.created_at.desc(), Payment.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).unique().all()
    return list(payments), int(total)


def list_payments_for_export(
    db: Session,
    *,
    status: PaymentStatus | None = None,
    from_: datetime | None = None,
    to: datetime | None = None,
    user_id: int | None = None,
    concept: PaymentConcept | None = None,
) -> list[Payment]:
    """Admin: same filters as list_payments, but every matching row (no pagination)."""
    filters = _admin_filters(
        status=status, from_=from_, to=to, user_id=user_id, concept=concept
    )
    query = _payment_query()
    if filters:
        query = query.where(*filters)
    payments = db.scalars(
        query.order_by(Payment.created_at.desc(), Payment.id.desc())
    ).unique().all()
    return list(payments)


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def payment_to_csv_row(payment: Payment) -> list[str]:
    """One CSV data row aligned with CSV_COLUMNS."""
    code_text = payment.discount_code.code if payment.discount_code is not None else None
    return [
        _csv_cell(payment.id),
        _csv_cell(payment.user_id),
        payment_concept(payment),
        _csv_cell(payment.subscription_id),
        _csv_cell(payment.booking_id),
        _csv_cell(payment.order_id),
        _csv_cell(code_text),
        _csv_cell(payment.base_amount_cents),
        _csv_cell(payment.final_amount_cents),
        _csv_cell(payment.status),
        _csv_cell(payment.method),
        _csv_cell(payment.created_at),
        _csv_cell(payment.paid_at),
    ]


def iter_payments_csv(payments: list[Payment]) -> Iterator[str]:
    """Yield CSV text chunks: header row, then one row per payment (stdlib csv)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    yield buffer.getvalue()
    buffer.seek(0)
    buffer.truncate(0)
    for payment in payments:
        writer.writerow(payment_to_csv_row(payment))
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)


def _get_own_payment_or_404(db: Session, user_id: int, payment_id: int) -> Payment:
    """404 if missing or not owned by this member (no IDOR leak)."""
    payment = db.scalar(
        _payment_query().where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    if payment is None:
        raise NotFoundError(PAYMENT_NOT_FOUND)
    return payment


def _get_payment_or_404(db: Session, payment_id: int) -> Payment:
    payment = db.scalar(_payment_query().where(Payment.id == payment_id))
    if payment is None:
        raise NotFoundError(PAYMENT_NOT_FOUND)
    return payment


def pay_payment(
    db: Session,
    member: User,
    payment_id: int,
    discount_code_text: str | None = None,
) -> Payment:
    """RN-16: pending → paid. Optional discount via discount_service.get_valid_code (RN-14, RN-15).

    Cancelled (and any non-pending) payments → 409. Order-linked payments also mark the
    order as paid in the same transaction.
    """
    payment = _get_own_payment_or_404(db, member.id, payment_id)

    # Includes cancelled, paid, failed, refunded — same 409 as any non-pending.
    if payment.status != PaymentStatus.PENDING:
        raise ConflictError(PAYMENT_NOT_PENDING)

    if discount_code_text:
        code = discount_service.get_valid_code(db, discount_code_text)
        payment.discount_code_id = code.id
        payment.final_amount_cents = apply_discount_cents(
            payment.base_amount_cents, code.percent_off
        )
    else:
        payment.discount_code_id = None
        payment.final_amount_cents = payment.base_amount_cents

    payment.status = PaymentStatus.PAID
    payment.paid_at = utc_now()

    if payment.order_id is not None:
        order = db.get(Order, payment.order_id)
        if order is None:
            raise NotFoundError(ORDER_NOT_FOUND)
        order.status = OrderStatus.PAID

    db.commit()
    db.refresh(payment)

    # Re-load with relationship for the response schema.
    payment = _get_own_payment_or_404(db, member.id, payment.id)
    logger.info(
        "User %s paid payment %s (final_amount_cents=%s, discount_code_id=%s, order_id=%s)",
        member.id,
        payment.id,
        payment.final_amount_cents,
        payment.discount_code_id,
        payment.order_id,
    )
    return payment


def refund_payment(db: Session, admin: User, payment_id: int) -> Payment:
    """RN-16: admin marks a paid payment as refunded. Non-paid → 409; missing → 404."""
    payment = _get_payment_or_404(db, payment_id)

    if payment.status != PaymentStatus.PAID:
        raise ConflictError(PAYMENT_NOT_PAID)

    payment.status = PaymentStatus.REFUNDED
    db.commit()
    db.refresh(payment)

    payment = _get_payment_or_404(db, payment.id)
    logger.info(
        "Admin %s refunded payment %s (user_id=%s, final_amount_cents=%s)",
        admin.id,
        payment.id,
        payment.user_id,
        payment.final_amount_cents,
    )
    return payment
