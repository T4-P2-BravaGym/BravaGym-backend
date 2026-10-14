from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import OrderStatus, ProductSize
from app.models.types import db_enum, utc_now

if TYPE_CHECKING:
    from app.models.user import User

_SIZE_ORDER = list(ProductSize)


class ProductCategory(Base):
    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_products_price"),
        CheckConstraint("stock >= 0", name="ck_products_stock"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("product_categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    price_cents: Mapped[int]
    stock: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    category: Mapped["ProductCategory"] = relationship()
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def active_variants(self) -> list["ProductVariant"]:
        return sorted(
            (variant for variant in self.variants if variant.is_active),
            key=lambda variant: _SIZE_ORDER.index(variant.size),
        )

    @property
    def has_sizes(self) -> bool:
        return any(variant.is_active for variant in self.variants)

    @property
    def available_stock(self) -> int:
        if self.has_sizes:
            return sum(variant.stock for variant in self.active_variants)
        return self.stock


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "size", name="uq_product_variants_product_size"),
        CheckConstraint("stock >= 0", name="ck_product_variants_stock"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    size: Mapped[ProductSize] = mapped_column(db_enum(ProductSize))
    stock: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    product: Mapped["Product"] = relationship(back_populates="variants")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(db_enum(OrderStatus), default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    user: Mapped["User"] = relationship()
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint(
            "order_id", "product_id", "variant_id", name="uq_order_items_order_product_variant"
        ),
        CheckConstraint("quantity > 0", name="ck_order_items_quantity"),
        CheckConstraint("unit_price_cents >= 0", name="ck_order_items_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    size: Mapped[ProductSize | None] = mapped_column(db_enum(ProductSize))
    quantity: Mapped[int]
    unit_price_cents: Mapped[int]

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
    variant: Mapped[Optional["ProductVariant"]] = relationship()