from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.types import db_enum, utc_now

if TYPE_CHECKING:
    from app.models.classes import Booking
    from app.models.membership import Subscription
    from app.models.shop import Order
    from app.models.user import User


class DiscountCode(Base):
    __tablename__ = "discount_codes"
    __table_args__ = (
        CheckConstraint(
            "percent_off BETWEEN 1 AND 100", name="ck_discount_codes_percent"
        ),
        CheckConstraint("valid_until >= valid_from", name="ck_discount_codes_dates"),
        CheckConstraint(
            "max_uses IS NULL OR max_uses > 0", name="ck_discount_codes_max_uses"
        ),
        CheckConstraint(
            "applies_to IS NULL OR applies_to IN ('subscription', 'booking', 'order')",
            name="ck_discount_codes_applies_to",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    percent_off: Mapped[int]
    valid_from: Mapped[date]
    valid_until: Mapped[date]
    max_uses: Mapped[int | None]
    # T-240: only for one payment concept (subscription, booking or order); empty = all
    applies_to: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))

    creator: Mapped["User"] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "(subscription_id IS NOT NULL) + (booking_id IS NOT NULL)"
            " + (order_id IS NOT NULL) = 1",
            name="ck_payments_one_concept",
        ),
        CheckConstraint(
            "base_amount_cents >= 0 AND final_amount_cents >= 0"
            " AND final_amount_cents <= base_amount_cents",
            name="ck_payments_amounts",
        ),
        CheckConstraint(
            "status != 'paid' OR paid_at IS NOT NULL", name="ck_payments_paid_at"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id"))
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    discount_code_id: Mapped[int | None] = mapped_column(
        ForeignKey("discount_codes.id")
    )
    base_amount_cents: Mapped[int]
    final_amount_cents: Mapped[int]
    status: Mapped[PaymentStatus] = mapped_column(
        db_enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    method: Mapped[PaymentMethod] = mapped_column(
        db_enum(PaymentMethod), default=PaymentMethod.SIMULATED
    )
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    paid_at: Mapped[datetime | None]

    user: Mapped["User"] = relationship()
    subscription: Mapped[Optional["Subscription"]] = relationship()
    booking: Mapped[Optional["Booking"]] = relationship()
    order: Mapped[Optional["Order"]] = relationship()
    discount_code: Mapped[Optional["DiscountCode"]] = relationship()


class PaymentCheckout(Base):
    """One durable Stripe attempt per payment; its request remains immutable."""

    __tablename__ = "payment_checkouts"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), primary_key=True)
    attempt_key: Mapped[str] = mapped_column(String(64), unique=True)
    request: Mapped[dict] = mapped_column(JSON)
    session_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
