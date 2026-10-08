"""Discount codes: admin CRUD and their validation (HU-25, RN-14).

Business rules RN-xx: docs/business-rules.md.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import DiscountCode, Payment, User
from app.models.enums import PaymentStatus
from app.models.types import utc_now
from app.schemas.payment import DATES_IN_ORDER, DiscountCodeCreate, DiscountCodeOut, DiscountCodeUpdate

logger = logging.getLogger(__name__)

CODE_TAKEN = "Ya existe un código con ese nombre."
CODE_NOT_FOUND = "No existe ese código de descuento."


def count_uses(db: Session, code_id: int) -> int:
    """Uses = paid payments with this code (RN-14). Derived data: never stored."""
    return db.scalar(
        select(func.count(Payment.id)).where(
            Payment.discount_code_id == code_id, Payment.status == PaymentStatus.PAID
        )
    )


def _to_out(db: Session, code: DiscountCode) -> DiscountCodeOut:
    return DiscountCodeOut(
        id=code.id,
        code=code.code,
        percent_off=code.percent_off,
        valid_from=code.valid_from,
        valid_until=code.valid_until,
        max_uses=code.max_uses,
        is_active=code.is_active,
        uses=count_uses(db, code.id),
    )


def _get_or_404(db: Session, code_id: int) -> DiscountCode:
    code = db.get(DiscountCode, code_id)
    if code is None:
        raise NotFoundError(CODE_NOT_FOUND)
    return code


def list_codes(db: Session, *, page: int = 1, size: int = 20) -> tuple[list[DiscountCodeOut], int]:
    """All codes, newest end date first. Returns (codes of this page, total)."""
    total = db.scalar(select(func.count(DiscountCode.id))) or 0
    codes = db.scalars(
        select(DiscountCode)
        .order_by(DiscountCode.valid_until.desc(), DiscountCode.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return [_to_out(db, code) for code in codes], int(total)


def create_code(db: Session, admin: User, data: DiscountCodeCreate) -> DiscountCodeOut:
    """409 if a code with the same text already exists."""
    if db.scalar(select(DiscountCode).where(DiscountCode.code == data.code)) is not None:
        raise ConflictError(CODE_TAKEN)

    code = DiscountCode(**data.model_dump(), created_by=admin.id)
    db.add(code)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CODE_TAKEN) from None

    logger.info("User %s created discount code %s", admin.id, code.id)
    return _to_out(db, code)


def update_code(db: Session, admin: User, code_id: int, changes: DiscountCodeUpdate) -> DiscountCodeOut:
    """Change only the fields sent. The dates are checked again with the values that stay."""
    code = _get_or_404(db, code_id)
    data = changes.model_dump(exclude_unset=True)
    valid_from = data.get("valid_from", code.valid_from)
    valid_until = data.get("valid_until", code.valid_until)
    if valid_until < valid_from:
        raise ValidationAppError(DATES_IN_ORDER)

    for field, value in data.items():
        setattr(code, field, value)
    db.commit()
    logger.info("User %s updated discount code %s", admin.id, code.id)
    return _to_out(db, code)


def deactivate_code(db: Session, admin: User, code_id: int) -> None:
    """Codes are not deleted: paid payments still point to them."""
    code = _get_or_404(db, code_id)
    code.is_active = False
    db.commit()
    logger.info("User %s deactivated discount code %s", admin.id, code.id)


def get_valid_code(db: Session, code_text: str) -> DiscountCode:
    """RN-14: active, within its dates and under max_uses. 422 otherwise. Reused when paying (HU-24)."""
    code = db.scalar(select(DiscountCode).where(DiscountCode.code == code_text.strip().upper()))
    if code is None:
        raise ValidationAppError("Este código de descuento no existe.")
    if not code.is_active:
        raise ValidationAppError("Este código de descuento ya no está activo.")
    today = utc_now().date()
    if not code.valid_from <= today <= code.valid_until:
        raise ValidationAppError("Este código de descuento no está vigente hoy.")
    if code.max_uses is not None and count_uses(db, code.id) >= code.max_uses:
        raise ValidationAppError("Este código de descuento ya se ha usado el máximo de veces.")
    return code