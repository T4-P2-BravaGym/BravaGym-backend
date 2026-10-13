import pytest
from sqlalchemy import select

from app.models import ProductVariant
from app.models.enums import RoleName
from tests.conftest import auth_header_for

PRODUCTS_URL = "/api/v1/products"
ADMIN_PRODUCTS_URL = f"{PRODUCTS_URL}/admin"
ORDERS_URL = "/api/v1/orders"


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers(RoleName.ADMIN)


@pytest.fixture
def tshirt(make_product):
    return make_product(name="Camiseta Brava", price_cents=2200, sizes={"L": 8, "S": 10, "M": 0})


def sizes_of(body: dict) -> list[tuple[str, int]]:
    return [(item["size"], item["stock"]) for item in body["sizes"]]


def stock_by_size(db, product) -> dict[str, int]:
    db.expire_all()
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id))
    return {variant.size: variant.stock for variant in variants if variant.is_active}


def order(client, headers, *lines: dict):
    return client.post(ORDERS_URL, json={"items": list(lines)}, headers=headers)


def test_shop_lists_sizes_from_xs_to_xl_and_their_total(client, tshirt):
    item = client.get(PRODUCTS_URL).json()["items"][0]

    assert sizes_of(item) == [("S", 10), ("M", 0), ("L", 8)]
    assert item["stock"] == 18
    assert item["in_stock"] is True


def test_clothing_with_every_size_sold_out_is_out_of_stock(client, admin_headers, make_product):
    make_product(name="Leggings Brava", sizes={"S": 0, "M": 0})
    make_product(name="Magnesio", stock=5)

    public = {item["name"]: item for item in client.get(PRODUCTS_URL).json()["items"]}
    assert public["Leggings Brava"]["in_stock"] is False

    response = client.get(ADMIN_PRODUCTS_URL, params={"status": "out_of_stock"}, headers=admin_headers)
    assert [item["name"] for item in response.json()["items"]] == ["Leggings Brava"]


def test_admin_creates_a_product_with_sizes(client, admin_headers, make_category):
    body = {
        "category_id": make_category("Ropa").id,
        "name": "Sudadera Brava",
        "price_cents": 3500,
        "sizes": [{"size": "M", "stock": 4}, {"size": "S", "stock": 2}],
    }

    response = client.post(PRODUCTS_URL, json=body, headers=admin_headers)

    assert response.status_code == 201
    assert sizes_of(response.json()) == [("S", 2), ("M", 4)]
    assert response.json()["stock"] == 6


@pytest.mark.parametrize(
    "extra",
    [
        {"sizes": [{"size": "M", "stock": 1}, {"size": "M", "stock": 2}]},
        {"sizes": [{"size": "M", "stock": -1}]},
        {"sizes": [{"size": "XXL", "stock": 1}]},
        {"sizes": [{"size": "M", "stock": 1}], "stock": 5},
    ],
    ids=["repeated-size", "negative-stock", "unknown-size", "stock-and-sizes"],
)
def test_invalid_sizes_return_422(client, admin_headers, make_category, extra):
    body = {"category_id": make_category().id, "name": "Sudadera", "price_cents": 3500, **extra}

    response = client.post(PRODUCTS_URL, json=body, headers=admin_headers)

    assert response.status_code == 422


def test_a_removed_size_is_hidden_but_not_deleted(client, db, admin_headers, tshirt):
    sizes = [{"size": "S", "stock": 5}, {"size": "M", "stock": 3}]

    response = client.patch(f"{PRODUCTS_URL}/{tshirt.id}", json={"sizes": sizes}, headers=admin_headers)

    assert response.status_code == 200
    assert sizes_of(response.json()) == [("S", 5), ("M", 3)]
    db.expire_all()
    rows = {v.size: v for v in db.scalars(select(ProductVariant).where(ProductVariant.product_id == tshirt.id))}
    assert rows["L"].is_active is False
    assert rows["L"].stock == 0


def test_stock_of_a_product_with_sizes_cannot_be_patched(client, admin_headers, tshirt):
    response = client.patch(f"{PRODUCTS_URL}/{tshirt.id}", json={"stock": 50}, headers=admin_headers)

    assert response.status_code == 422


def test_removing_every_size_makes_it_a_normal_product(client, admin_headers, tshirt):
    response = client.patch(
        f"{PRODUCTS_URL}/{tshirt.id}", json={"sizes": [], "stock": 7}, headers=admin_headers
    )

    assert response.status_code == 200
    assert response.json()["sizes"] == []
    assert response.json()["stock"] == 7


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_only_admin_changes_sizes(client, auth_headers, tshirt, role):
    response = client.patch(f"{PRODUCTS_URL}/{tshirt.id}", json={"sizes": []}, headers=auth_headers(role))

    assert response.status_code == 403


def test_changing_sizes_without_token_returns_401(client, tshirt):
    assert client.patch(f"{PRODUCTS_URL}/{tshirt.id}", json={"sizes": []}).status_code == 401


def test_an_order_takes_stock_only_from_its_size(client, db, auth_headers, tshirt):
    response = order(client, auth_headers(), {"product_id": tshirt.id, "size": "S", "quantity": 2})

    assert response.status_code == 201
    assert response.json()["items"][0]["size"] == "S"
    assert stock_by_size(db, tshirt) == {"S": 8, "M": 0, "L": 8}


def test_the_same_shirt_in_two_sizes_is_two_lines(client, auth_headers, tshirt):
    response = order(
        client,
        auth_headers(),
        {"product_id": tshirt.id, "size": "S", "quantity": 1},
        {"product_id": tshirt.id, "size": "L", "quantity": 1},
    )

    assert response.status_code == 201
    assert sorted(item["size"] for item in response.json()["items"]) == ["L", "S"]
    assert response.json()["total_cents"] == 4400


def test_the_same_product_and_size_twice_returns_422(client, auth_headers, tshirt):
    line = {"product_id": tshirt.id, "size": "S", "quantity": 1}

    assert order(client, auth_headers(), line, line).status_code == 422


@pytest.mark.parametrize(
    "line", [{"quantity": 1}, {"size": "XL", "quantity": 1}], ids=["no-size", "size-not-on-sale"]
)
def test_clothing_without_a_valid_size_returns_422(client, db, auth_headers, tshirt, line):
    response = order(client, auth_headers(), {"product_id": tshirt.id, **line})

    assert response.status_code == 422
    assert stock_by_size(db, tshirt) == {"S": 10, "M": 0, "L": 8}


def test_a_size_for_a_product_without_sizes_returns_422(client, auth_headers, make_product):
    whey = make_product(name="Proteína whey 1 kg")

    response = order(client, auth_headers(), {"product_id": whey.id, "size": "M", "quantity": 1})

    assert response.status_code == 422


def test_not_enough_of_a_size_returns_409_naming_the_size(client, db, auth_headers, tshirt):
    response = order(client, auth_headers(), {"product_id": tshirt.id, "size": "S", "quantity": 11})

    assert response.status_code == 409
    assert "talla S" in response.json()["detail"]
    assert stock_by_size(db, tshirt) == {"S": 10, "M": 0, "L": 8}


def test_a_sold_out_size_returns_409(client, auth_headers, tshirt):
    response = order(client, auth_headers(), {"product_id": tshirt.id, "size": "M", "quantity": 1})

    assert response.status_code == 409
    assert "se ha agotado" in response.json()["detail"]


def test_cancelling_puts_the_units_back_in_their_size(client, db, make_user, tshirt):
    headers = auth_header_for(make_user())
    placed = order(client, headers, {"product_id": tshirt.id, "size": "S", "quantity": 3}).json()

    response = client.post(f"{ORDERS_URL}/{placed['id']}/cancel", headers=headers)

    assert response.status_code == 200
    assert stock_by_size(db, tshirt) == {"S": 10, "M": 0, "L": 8}


def test_cancelling_after_the_size_was_removed_does_not_bring_it_back(
        client, db, make_user, admin_headers, tshirt
):
    headers = auth_header_for(make_user())
    placed = order(client, headers, {"product_id": tshirt.id, "size": "S", "quantity": 2}).json()
    client.patch(
        f"{PRODUCTS_URL}/{tshirt.id}",
        json={"sizes": [{"size": "M", "stock": 1}, {"size": "L", "stock": 8}]},
        headers=admin_headers,
    )

    response = client.post(f"{ORDERS_URL}/{placed['id']}/cancel", headers=headers)

    assert response.status_code == 200
    assert stock_by_size(db, tshirt) == {"M": 1, "L": 8}