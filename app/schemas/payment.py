"""TODO(HU-24, HU-25, HU-26): PaymentOut, PayRequest (optional discount_code), DiscountCodeOut/Create.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Page

DATES_IN_ORDER = "La fecha de fin no puede ser anterior a la de inicio."


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