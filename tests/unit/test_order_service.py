import pytest
from app.core.exceptions import ConflictError, NotFoundError
from app.models import Order, OrderItem, Payment, Product
from app.models.enums import OrderStatus, PaymentStatus
from app.models.types import utc_now
from app.schemas.order import OrderCreate
from app.services import order_service
from sqlalchemy import func, select, update


def count_rows(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def order_body(*lines: tuple[Product, int]) -> OrderCreate:
    return OrderCreate(items=[{"product_id": p.id, "quantity": q} for p, q in lines])


def stock_of(db, product: Product) -> int:
    db.refresh(product)
    return product.stock


@pytest.fixture
def placed(db, make_user, make_product):
    member = make_user()
    product = make_product(stock=5)
    result = order_service.place_order(
        db, user_id=member.id, data=order_body((product, 2))
    )
    return member, product, result


def test_rn17_order_takes_stock_and_creates_a_pending_payment(
    db, make_user, make_product
):
    member = make_user()
    whey = make_product(price_cents=3490, stock=5)
    straps = make_product(price_cents=1290, stock=2)

    result = order_service.place_order(
        db, user_id=member.id, data=order_body((whey, 2), (straps, 1))
    )

    assert result.order.status == OrderStatus.PENDING
    assert len(result.order.items) == 2
    assert stock_of(db, whey) == 3
    assert stock_of(db, straps) == 1
    assert result.payment.status == PaymentStatus.PENDING
    assert result.payment.user_id == member.id
    assert result.payment.base_amount_cents == 2 * 3490 + 1290
    assert result.payment.final_amount_cents == result.payment.base_amount_cents


def test_the_line_keeps_the_price_of_the_day(db, make_user, make_product):
    product = make_product(price_cents=1000)
    result = order_service.place_order(
        db, user_id=make_user().id, data=order_body((product, 1))
    )

    product.price_cents = 1500
    db.commit()

    item = db.scalar(select(OrderItem).where(OrderItem.order_id == result.order.id))
    assert item.unit_price_cents == 1000


def test_rn17_not_enough_stock_raises_conflict_and_changes_nothing(
    db, make_user, make_product
):
    plenty = make_product(stock=10)
    scarce = make_product(name="Cinturón de lastre", stock=1)

    with pytest.raises(ConflictError, match="Solo queda 1 unidad"):
        order_service.place_order(
            db, user_id=make_user().id, data=order_body((plenty, 3), (scarce, 2))
        )

    assert stock_of(db, plenty) == 10
    assert stock_of(db, scarce) == 1
    assert count_rows(db, Order) == 0
    assert count_rows(db, OrderItem) == 0
    assert count_rows(db, Payment) == 0


def test_rn17_stock_is_checked_in_the_database_not_in_the_loaded_object(
    db, make_user, make_product
):
    product = make_product(stock=5)
    db.execute(
        update(Product)
        .where(Product.id == product.id)
        .values(stock=1)
        .execution_options(synchronize_session=False)
    )
    db.commit()
    assert product.stock == 5

    with pytest.raises(ConflictError):
        order_service.place_order(
            db, user_id=make_user().id, data=order_body((product, 2))
        )

    assert stock_of(db, product) == 1


def test_rn17_the_last_unit_is_sold_only_once(db, make_user, make_product):
    product = make_product(stock=1)
    order_service.place_order(db, user_id=make_user().id, data=order_body((product, 1)))

    with pytest.raises(ConflictError, match="se ha agotado"):
        order_service.place_order(
            db, user_id=make_user().id, data=order_body((product, 1))
        )

    assert stock_of(db, product) == 0
    assert count_rows(db, Order) == 1


def test_inactive_product_raises_conflict(db, make_user, make_product):
    product = make_product(is_active=False)

    with pytest.raises(ConflictError):
        order_service.place_order(
            db, user_id=make_user().id, data=order_body((product, 1))
        )

    assert count_rows(db, Order) == 0


def test_unknown_product_raises_conflict(db, make_user):
    data = OrderCreate(items=[{"product_id": 999, "quantity": 1}])

    with pytest.raises(ConflictError):
        order_service.place_order(db, user_id=make_user().id, data=data)


def test_rn17_cancel_puts_the_stock_back_and_cancels_the_payment(db, placed):
    member, product, result = placed

    cancelled = order_service.cancel_order(
        db, user_id=member.id, order_id=result.order.id
    )

    assert cancelled.order.status == OrderStatus.CANCELLED
    assert cancelled.payment.status == PaymentStatus.CANCELLED
    assert stock_of(db, product) == 5


def test_cancel_twice_raises_conflict_and_restocks_once(db, placed):
    member, product, result = placed
    order_service.cancel_order(db, user_id=member.id, order_id=result.order.id)

    with pytest.raises(ConflictError):
        order_service.cancel_order(db, user_id=member.id, order_id=result.order.id)

    assert stock_of(db, product) == 5


def test_rn17_two_cancels_at_once_put_the_stock_back_only_once(db, placed):
    member, product, result = placed
    # Another request cancels the order after this session loaded it as pending.
    db.execute(
        update(Order)
        .where(Order.id == result.order.id)
        .values(status=OrderStatus.CANCELLED)
        .execution_options(synchronize_session=False)
    )
    db.commit()

    with pytest.raises(ConflictError):
        order_service.cancel_order(db, user_id=member.id, order_id=result.order.id)

    assert stock_of(db, product) == 3


def test_cannot_cancel_an_order_whose_payment_is_paid(db, placed):
    member, product, result = placed
    result.payment.status = PaymentStatus.PAID
    result.payment.paid_at = utc_now()
    db.commit()

    with pytest.raises(ConflictError):
        order_service.cancel_order(db, user_id=member.id, order_id=result.order.id)

    db.refresh(result.order)
    assert result.order.status == OrderStatus.PENDING
    assert stock_of(db, product) == 3


def test_cancel_someone_elses_order_raises_not_found(db, make_user, placed):
    _, product, result = placed

    with pytest.raises(NotFoundError):
        order_service.cancel_order(db, user_id=make_user().id, order_id=result.order.id)

    assert stock_of(db, product) == 3
