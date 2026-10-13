"""Payment and discount-code schemas (HU-24, HU-25, HU-26).

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.common import Page

DATES_IN_ORDER = "La fecha de fin no puede ser anterior a la de inicio."

PaymentConcept = Literal["subscription", "booking", "order"]

PAYMENT_EXAMPLE = {
    "id": 12,
    "user_id": 3,
    "concept": "subscription",
    "subscription_id": 7,
    "booking_id": None,
    "order_id": None,
    "discount_code": "VERANO20",
    "base_amount_cents": 5900,
    "final_amount_cents": 4720,
    "status": "paid",
    "method": "simulated",
    "created_at": "2026-10-06T10:00:00",
    "paid_at": "2026-10-06T10:05:00",
}


class DiscountCodeCreate(BaseModel):
    """Body for POST /discount-codes. The code is saved in capitals, without spaces around."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "VERANO20",
                "percent_off": 20,
                "valid_from": "2026-06-01",
                "valid_until": "2026-08-31",
                "max_uses": 50,
            }
        }
    )

    code: str = Field(min_length=3, max_length=30)
    percent_off: int = Field(ge=1, le=100)
    valid_from: date
    valid_until: date
    max_uses: int | None = Field(default=None, ge=1)

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def check_dates(self) -> "DiscountCodeCreate":
        if self.valid_until < self.valid_from:
            raise ValueError(DATES_IN_ORDER)
        return self


class DiscountCodeUpdate(BaseModel):
    """What an admin can change in a code. The code text itself never changes."""

    model_config = ConfigDict(json_schema_extra={"example": {"percent_off": 15, "max_uses": 100}})

    percent_off: int = Field(default=None, ge=1, le=100)
    valid_from: date = None
    valid_until: date = None
    max_uses: int | None = Field(default=None, ge=1)
    is_active: bool = None


class DiscountCodeOut(BaseModel):
    """A discount code for the admin panel, with how many paid payments used it."""

    id: int
    code: str
    percent_off: int
    valid_from: date
    valid_until: date
    max_uses: int | None
    is_active: bool
    uses: int


class DiscountCodePage(Page[DiscountCodeOut]):
    """Paginated list of discount codes."""


class DiscountValidationOut(BaseModel):
    """What a member gets when her code is valid (RN-14)."""

    model_config = ConfigDict(json_schema_extra={"example": {"code": "VERANO20", "percent_off": 20}})

    code: str
    percent_off: int


class PayRequest(BaseModel):
    """Optional body for POST /payments/{id}/pay. Amounts are never accepted from the client."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"discount_code": "VERANO20"}},
    )

    discount_code: str | None = Field(default=None, max_length=30)

    @field_validator("discount_code")
    @classmethod
    def normalize_discount_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None


class PaymentOut(BaseModel):
    """A payment as seen by the member (or later by admin). Concept is derived, never stored."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": PAYMENT_EXAMPLE},
    )

    id: int
    user_id: int
    concept: PaymentConcept
    subscription_id: int | None
    booking_id: int | None
    order_id: int | None
    discount_code: str | None = None
    base_amount_cents: int
    final_amount_cents: int
    status: PaymentStatus
    method: PaymentMethod
    created_at: datetime
    paid_at: datetime | None

    @classmethod
    def from_payment(cls, payment) -> "PaymentOut":
        if payment.subscription_id is not None:
            concept: PaymentConcept = "subscription"
        elif payment.booking_id is not None:
            concept = "booking"
        elif payment.order_id is not None:
            concept = "order"
        else:
            raise ValueError("Payment must reference exactly one concept")

        code_text = payment.discount_code.code if payment.discount_code is not None else None
        return cls(
            id=payment.id,
            user_id=payment.user_id,
            concept=concept,
            subscription_id=payment.subscription_id,
            booking_id=payment.booking_id,
            order_id=payment.order_id,
            discount_code=code_text,
            base_amount_cents=payment.base_amount_cents,
            final_amount_cents=payment.final_amount_cents,
            status=payment.status,
            method=payment.method,
            created_at=payment.created_at,
            paid_at=payment.paid_at,
        )


class PaymentPage(Page[PaymentOut]):
    """Paginated list of payments."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"items": [PAYMENT_EXAMPLE], "total": 1, "page": 1, "size": 20}
        }
    )
