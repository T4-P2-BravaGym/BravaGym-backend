import pytest
from sqlalchemy import func, select

from app.models import Order, Payment
from app.models.enums import RoleName
from tests.conftest import auth_header_for

ORDERS_URL = "/api/v1/orders"


@pytest.fixture
def member(make_user):
    return make_user()


@pytest.fixture
def headers(member):
    return auth_header_for(member)


def place(client, headers, *lines):
    body = {"items": [{"product_id": p.id, "quantity": q} for p, q in lines]}
    return client.post(ORDERS_URL, json=body, headers=headers)


def cancel(client, headers, order_id):
    return client.post(f"{ORDERS_URL}/{order_id}/cancel", headers=headers)


def test_place_order_returns_201_with_lines_total_and_pending_payment(
        client, db, headers, make_product
):
    whey = make_product(name="Proteína whey 1 kg", price_cents=3490, stock=5)

    response = place(client, headers, (whey, 2))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["total_cents"] == 6980
    assert body["payment_status"] == "pending"
    assert body["items"] == [
        {
            "product_id": whey.id,
            "product_name": "Proteína whey 1 kg",
            "size": None,
            "quantity": 2,
            "unit_price_cents": 3490,
            "subtotal_cents": 6980,
        }
    ]
    db.refresh(whey)
    assert whey.stock == 3


def test_prices_sent_by_the_client_are_ignored(client, db, headers, make_product):
    product = make_product(price_cents=2500)
    body = {
        "items": [{"product_id": product.id, "quantity": 1, "unit_price_cents": 1}],
        "total_cents": 1,
    }

    response = client.post(ORDERS_URL, json=body, headers=headers)

    assert response.status_code == 201
    assert response.json()["total_cents"] == 2500
    payment = db.scalar(select(Payment).where(Payment.order_id == response.json()["id"]))
    assert payment.base_amount_cents == 2500


@pytest.mark.parametrize(
    "items",
    [
        [],
        [{"product_id": 1, "quantity": 0}],
        [{"product_id": 1, "quantity": 100}],
        [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}],
    ],
    ids=["empty-cart", "zero-units", "too-many-units", "same-product-twice"],
)
def test_invalid_cart_returns_422(client, headers, items):
    response = client.post(ORDERS_URL, json={"items": items}, headers=headers)

    assert response.status_code == 422


def test_not_enough_stock_returns_409_and_changes_nothing(client, db, headers, make_product):
    product = make_product(stock=1)

    response = place(client, headers, (product, 2))

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    db.refresh(product)
    assert product.stock == 1
    assert db.scalar(select(func.count(Order.id))) == 0


def test_place_order_without_token_returns_401(client, make_product):
    response = place(client, {}, (make_product(), 1))

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_place_orders(client, auth_headers, make_product, role):
    response = place(client, auth_headers(role), (make_product(), 1))

    assert response.status_code == 403


def test_my_orders_lists_only_mine_newest_first(client, headers, make_user, make_product):
    product = make_product(stock=10)
    first = place(client, headers, (product, 1)).json()
    second = place(client, headers, (product, 2)).json()
    place(client, auth_header_for(make_user()), (product, 1))

    response = client.get(f"{ORDERS_URL}/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [order["id"] for order in body["items"]] == [second["id"], first["id"]]
    assert body["items"][0]["items"][0]["quantity"] == 2


def test_my_orders_without_token_returns_401(client):
    assert client.get(f"{ORDERS_URL}/me").status_code == 401


def test_my_orders_as_admin_returns_403(client, auth_headers):
    response = client.get(f"{ORDERS_URL}/me", headers=auth_headers(RoleName.ADMIN))

    assert response.status_code == 403


def test_cancel_my_order_restores_stock_and_cancels_payment(client, db, headers, make_product):
    product = make_product(stock=5)
    order = place(client, headers, (product, 2)).json()

    response = cancel(client, headers, order["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["payment_status"] == "cancelled"
    db.refresh(product)
    assert product.stock == 5


def test_cancel_twice_returns_409(client, headers, make_product):
    order = place(client, headers, (make_product(), 1)).json()
    cancel(client, headers, order["id"])

    response = cancel(client, headers, order["id"])

    assert response.status_code == 409


def test_cancel_someone_elses_order_returns_404(client, db, headers, make_user, make_product):
    product = make_product(stock=5)
    order = place(client, auth_header_for(make_user()), (product, 1)).json()

    response = cancel(client, headers, order["id"])

    assert response.status_code == 404
    db.refresh(product)
    assert product.stock == 4


def test_cancel_unknown_order_returns_404(client, headers):
    assert cancel(client, headers, 999).status_code == 404


def test_cancel_without_token_returns_401(client):
    assert cancel(client, {}, 1).status_code == 401