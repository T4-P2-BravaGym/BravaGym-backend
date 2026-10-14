from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.enums import OrderStatus, PaymentStatus, ProductSize
from app.schemas.common import Page

if TYPE_CHECKING:
    from app.models import Order, OrderItem, Payment

MAX_ORDER_LINES = 50
MAX_LINE_QUANTITY = 99

ORDER_CREATE_EXAMPLE = {
    "items": [
        {"product_id": 1, "quantity": 2},
        {"product_id": 3, "size": "M", "quantity": 1},
    ]
}

ORDER_EXAMPLE = {
    "id": 7,
    "status": "pending",
    "created_at": "2026-10-13T10:30:00",
    "items": [
        {
            "product_id": 1,
            "product_name": "Proteína whey 1 kg",
            "size": None,
            "quantity": 2,
            "unit_price_cents": 3490,
            "subtotal_cents": 6980,
        },
        {
            "product_id": 3,
            "product_name": "Camiseta Brava",
            "size": "M",
            "quantity": 1,
            "unit_price_cents": 2200,
            "subtotal_cents": 2200,
        },
    ],
    "payment_id": 15,
    "payment_status": "pending",
    "total_cents": 9180,
}

ORDER_PAGE_EXAMPLE = {"items": [ORDER_EXAMPLE], "total": 1, "page": 1, "size": 20}


class OrderLineIn(BaseModel):
    product_id: int = Field(ge=1)
    size: ProductSize | None = Field(
        default=None,
        description="Required for clothing with sizes; leave it out for the rest",
    )
    quantity: int = Field(ge=1, le=MAX_LINE_QUANTITY)


class OrderCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": ORDER_CREATE_EXAMPLE})

    items: list[OrderLineIn] = Field(min_length=1, max_length=MAX_ORDER_LINES)

    @field_validator("items")
    @classmethod
    def reject_repeated_lines(cls, items: list[OrderLineIn]) -> list[OrderLineIn]:
        keys = [(line.product_id, line.size) for line in items]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "each product and size can only appear once; add up its quantity instead"
            )
        return items


class OrderItemOut(BaseModel):
    product_id: int
    product_name: str = Field(max_length=120)
    size: ProductSize | None
    quantity: int = Field(ge=1)
    unit_price_cents: int = Field(ge=0)

    @computed_field
    @property
    def subtotal_cents(self) -> int:
        return self.unit_price_cents * self.quantity

    @classmethod
    def from_item(cls, item: "OrderItem") -> "OrderItemOut":
        return cls(
            product_id=item.product_id,
            product_name=item.product.name,
            size=item.size,
            quantity=item.quantity,
            unit_price_cents=item.unit_price_cents,
        )


class OrderOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": ORDER_EXAMPLE})

    id: int
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemOut]
    payment_id: int | None
    payment_status: PaymentStatus | None

    @computed_field
    @property
    def total_cents(self) -> int:
        return sum(item.subtotal_cents for item in self.items)

    @classmethod
    def from_order(cls, order: "Order", payment: "Payment | None") -> "OrderOut":
        return cls(
            id=order.id,
            status=order.status,
            created_at=order.created_at,
            items=[OrderItemOut.from_item(item) for item in order.items],
            payment_id=payment.id if payment else None,
            payment_status=payment.status if payment else None,
        )


class OrderPage(Page[OrderOut]):
    model_config = ConfigDict(json_schema_extra={"example": ORDER_PAGE_EXAMPLE})
