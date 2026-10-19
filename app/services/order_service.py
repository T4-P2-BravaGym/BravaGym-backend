from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import Order, OrderItem, Payment, Product, ProductVariant
from app.models.enums import OrderStatus, PaymentStatus, ProductSize
from app.schemas.order import OrderCreate, OrderLineIn

logger = logging.getLogger(__name__)

PRODUCT_NOT_AVAILABLE = (
    "Algún producto de tu carrito ya no está disponible. Quítalo y vuelve a intentarlo."
)
ORDER_NOT_FOUND = "Este pedido no existe."
ORDER_NOT_CANCELLABLE = "Solo puedes cancelar un pedido que aún no has pagado."

_SIZE_ORDER = list(ProductSize)


@dataclass(frozen=True, slots=True)
class OrderWithPayment:
    order: Order
    payment: Payment | None


@dataclass(frozen=True, slots=True)
class _Line:
    product: Product
    variant: ProductVariant | None
    quantity: int

    @property
    def label(self) -> str:
        if self.variant is None:
            return f"«{self.product.name}»"
        return f"«{self.product.name}» en talla {self.variant.size}"

    @property
    def sort_key(self) -> tuple[int, int]:
        return self.product.id, _SIZE_ORDER.index(
            self.variant.size
        ) if self.variant else -1


def not_enough_stock_message(label: str, available: int) -> str:
    if available <= 0:
        return f"{label} se ha agotado. Quítalo del carrito para continuar."
    if available == 1:
        return f"Solo queda 1 unidad de {label}."
    return f"Solo quedan {available} unidades de {label}."


def _update_stock(
    db: Session,
    model: type[Product | ProductVariant],
    row_id: int,
    delta: int,
    *conditions,
) -> bool:
    stmt = (
        update(model)
        .where(model.id == row_id, *conditions)
        .values(stock=model.stock + delta)
    )
    if delta < 0:
        stmt = stmt.where(model.stock >= -delta)
    result = db.execute(stmt.execution_options(synchronize_session=False))
    return result.rowcount == 1


def _set_status(
    db: Session, model: type[Order | Payment], row_id: int, current, new
) -> bool:
    result = db.execute(
        update(model)
        .where(model.id == row_id, model.status == current)
        .values(status=new)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _variant_for(product: Product, size: ProductSize | None) -> ProductVariant | None:
    if not product.has_sizes:
        if size is not None:
            raise ValidationAppError(f"«{product.name}» no tiene tallas.")
        return None
    if size is None:
        raise ValidationAppError(f"Elige una talla de «{product.name}».")
    variant = next((v for v in product.active_variants if v.size == size), None)
    if variant is None:
        raise ValidationAppError(f"«{product.name}» no tiene la talla {size}.")
    return variant


def _check_lines(db: Session, lines: list[OrderLineIn]) -> list[_Line]:
    product_ids = {line.product_id for line in lines}
    products = {
        product.id: product
        for product in db.scalars(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id.in_(product_ids))
        )
    }
    if len(products) != len(product_ids) or not all(
        p.is_active for p in products.values()
    ):
        raise ConflictError(PRODUCT_NOT_AVAILABLE)

    checked = [
        _Line(
            product=products[line.product_id],
            variant=_variant_for(products[line.product_id], line.size),
            quantity=line.quantity,
        )
        for line in lines
    ]
    return sorted(checked, key=lambda line: line.sort_key)


def _take_stock(db: Session, line: _Line) -> bool:
    if line.variant is None:
        return _update_stock(db, Product, line.product.id, -line.quantity)
    return _update_stock(
        db,
        ProductVariant,
        line.variant.id,
        -line.quantity,
        ProductVariant.is_active.is_(True),
    )


def _stock_left(db: Session, line: _Line) -> int:
    if line.variant is None:
        return (
            db.scalar(select(Product.stock).where(Product.id == line.product.id)) or 0
        )
    return (
        db.scalar(
            select(ProductVariant.stock).where(ProductVariant.id == line.variant.id)
        )
        or 0
    )


def _restore_stock(db: Session, item: OrderItem) -> None:
    if item.variant_id is None:
        _update_stock(db, Product, item.product_id, item.quantity)
    else:
        _update_stock(
            db,
            ProductVariant,
            item.variant_id,
            item.quantity,
            ProductVariant.is_active.is_(True),
        )


def _orders_stmt() -> Select:
    return select(Order).options(
        selectinload(Order.items).joinedload(OrderItem.product)
    )


def _with_payments(db: Session, orders: list[Order]) -> list[OrderWithPayment]:
    if not orders:
        return []
    payments = {
        payment.order_id: payment
        for payment in db.scalars(
            select(Payment).where(Payment.order_id.in_([order.id for order in orders]))
        )
    }
    return [
        OrderWithPayment(order=order, payment=payments.get(order.id))
        for order in orders
    ]


def _get_my_order(db: Session, user_id: int, order_id: int) -> OrderWithPayment:
    order = db.scalar(
        _orders_stmt().where(Order.id == order_id, Order.user_id == user_id)
    )
    if order is None:
        raise NotFoundError(ORDER_NOT_FOUND)
    return _with_payments(db, [order])[0]


def place_order(db: Session, *, user_id: int, data: OrderCreate) -> OrderWithPayment:
    lines = _check_lines(db, data.items)

    order = Order(user_id=user_id, status=OrderStatus.PENDING)
    for line in lines:
        label = line.label
        if not _take_stock(db, line):
            available = _stock_left(db, line)
            db.rollback()
            logger.info(
                "Blocked order for user %s: %s has %s left, %s requested",
                user_id,
                label,
                available,
                line.quantity,
            )
            raise ConflictError(not_enough_stock_message(label, available))
        order.items.append(
            OrderItem(
                product_id=line.product.id,
                variant_id=line.variant.id if line.variant else None,
                size=line.variant.size if line.variant else None,
                quantity=line.quantity,
                unit_price_cents=line.product.price_cents,
            )
        )

    total_cents = sum(item.unit_price_cents * item.quantity for item in order.items)
    payment = Payment(
        user_id=user_id,
        order=order,
        base_amount_cents=total_cents,
        final_amount_cents=total_cents,
        status=PaymentStatus.PENDING,
    )
    db.add_all([order, payment])
    db.commit()

    order_id, payment_id = order.id, payment.id
    db.expire_all()
    logger.info(
        "User %s placed order %s (%s lines, %s cents, pending payment %s)",
        user_id,
        order_id,
        len(lines),
        total_cents,
        payment_id,
    )
    return _get_my_order(db, user_id, order_id)


def list_my_orders(
    db: Session, *, user_id: int, page: int = 1, size: int = 20
) -> tuple[list[OrderWithPayment], int]:
    total = db.scalar(select(func.count(Order.id)).where(Order.user_id == user_id)) or 0
    orders = list(
        db.scalars(
            _orders_stmt()
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
    )
    return _with_payments(db, orders), int(total)


def cancel_order(db: Session, *, user_id: int, order_id: int) -> OrderWithPayment:
    current = _get_my_order(db, user_id, order_id)
    order, payment = current.order, current.payment
    if order.status != OrderStatus.PENDING or (
        payment is not None and payment.status != PaymentStatus.PENDING
    ):
        raise ConflictError(ORDER_NOT_CANCELLABLE)

    claimed = _set_status(
        db, Order, order.id, OrderStatus.PENDING, OrderStatus.CANCELLED
    )
    if claimed and payment is not None:
        claimed = _set_status(
            db, Payment, payment.id, PaymentStatus.PENDING, PaymentStatus.CANCELLED
        )
    if not claimed:
        db.rollback()
        logger.info(
            "Blocked cancel of order %s for user %s: no longer pending",
            order_id,
            user_id,
        )
        raise ConflictError(ORDER_NOT_CANCELLABLE)

    restored = [
        f"product {item.product_id}{f' {item.size}' if item.size else ''} +{item.quantity}"
        for item in order.items
    ]
    for item in order.items:
        _restore_stock(db, item)
    db.commit()

    db.expire_all()
    logger.info(
        "User %s cancelled order %s (stock restored: %s; payment %s cancelled)",
        user_id,
        order_id,
        ", ".join(restored),
        payment.id if payment is not None else "none",
    )
    return _get_my_order(db, user_id, order_id)
