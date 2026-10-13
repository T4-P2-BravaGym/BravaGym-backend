from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Order, OrderItem, Payment, Product
from app.models.enums import OrderStatus, PaymentStatus
from app.schemas.order import OrderCreate

logger = logging.getLogger(__name__)

PRODUCT_NOT_AVAILABLE = (
    "Algún producto de tu carrito ya no está disponible. Quítalo y vuelve a intentarlo."
)
ORDER_NOT_FOUND = "Este pedido no existe."
ORDER_NOT_CANCELLABLE = "Solo puedes cancelar un pedido que aún no has pagado."


@dataclass(frozen=True, slots=True)
class OrderWithPayment:

    order: Order
    payment: Payment | None


def not_enough_stock_message(product_name: str, available: int) -> str:
    if available <= 0:
        return f"«{product_name}» se ha agotado. Quítalo del carrito para continuar."
    if available == 1:
        return f"Solo queda 1 unidad de «{product_name}»."
    return f"Solo quedan {available} unidades de «{product_name}»."


def _change_stock(db: Session, product_id: int, delta: int) -> bool:
    stmt = update(Product).where(Product.id == product_id).values(stock=Product.stock + delta)
    if delta < 0:
        stmt = stmt.where(Product.stock >= -delta)
    result = db.execute(stmt.execution_options(synchronize_session=False))
    return result.rowcount == 1


def _set_status(db: Session, model: type[Order] | type[Payment], row_id: int, current, new) -> bool:
    result = db.execute(
        update(model)
        .where(model.id == row_id, model.status == current)
        .values(status=new)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1


def _orders_stmt() -> Select:
    return select(Order).options(selectinload(Order.items).joinedload(OrderItem.product))


def _with_payments(db: Session, orders: list[Order]) -> list[OrderWithPayment]:
    if not orders:
        return []
    payments = {
        payment.order_id: payment
        for payment in db.scalars(
            select(Payment).where(Payment.order_id.in_([order.id for order in orders]))
        )
    }
    return [OrderWithPayment(order=order, payment=payments.get(order.id)) for order in orders]


def _get_my_order(db: Session, user_id: int, order_id: int) -> OrderWithPayment:
    order = db.scalar(_orders_stmt().where(Order.id == order_id, Order.user_id == user_id))
    if order is None:
        raise NotFoundError(ORDER_NOT_FOUND)
    return _with_payments(db, [order])[0]


def place_order(db: Session, *, user_id: int, data: OrderCreate) -> OrderWithPayment:
    quantities = {line.product_id: line.quantity for line in data.items}
    product_ids = sorted(quantities)
    products = {
        product.id: product
        for product in db.scalars(select(Product).where(Product.id.in_(product_ids)))
    }
    if len(products) != len(product_ids) or not all(p.is_active for p in products.values()):
        raise ConflictError(PRODUCT_NOT_AVAILABLE)

    order = Order(user_id=user_id, status=OrderStatus.PENDING)
    for product_id in product_ids:
        product = products[product_id]
        quantity = quantities[product_id]
        if not _change_stock(db, product_id, -quantity):
            available = db.scalar(select(Product.stock).where(Product.id == product_id)) or 0
            product_name = product.name
            db.rollback()
            logger.info(
                "Blocked order for user %s: product %s has %s left, %s requested",
                user_id,
                product_id,
                available,
                quantity,
            )
            raise ConflictError(not_enough_stock_message(product_name, available))
        order.items.append(
            OrderItem(
                product_id=product_id,
                quantity=quantity,
                unit_price_cents=product.price_cents,
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
        len(product_ids),
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

    claimed = _set_status(db, Order, order.id, OrderStatus.PENDING, OrderStatus.CANCELLED)
    if claimed and payment is not None:
        claimed = _set_status(
            db, Payment, payment.id, PaymentStatus.PENDING, PaymentStatus.CANCELLED
        )
    if not claimed:
        db.rollback()
        logger.info("Blocked cancel of order %s for user %s: no longer pending", order_id, user_id)
        raise ConflictError(ORDER_NOT_CANCELLABLE)

    restored = [(item.product_id, item.quantity) for item in order.items]
    for product_id, quantity in restored:
        _change_stock(db, product_id, quantity)
    db.commit()

    db.expire_all()
    logger.info(
        "User %s cancelled order %s (stock restored: %s; payment %s cancelled)",
        user_id,
        order_id,
        ", ".join(f"product {pid} +{qty}" for pid, qty in restored),
        payment.id if payment is not None else "none",
    )
    return _get_my_order(db, user_id, order_id)