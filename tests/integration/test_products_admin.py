import pytest

from app.models import Order, OrderItem, Product, ProductCategory
from app.models.enums import RoleName
from app.services.shop_service import (
    CATEGORY_HAS_PRODUCTS,
    CATEGORY_NAME_TAKEN,
    UNKNOWN_CATEGORY,
)

PRODUCTS_URL = "/api/v1/products"
ADMIN_PRODUCTS_URL = f"{PRODUCTS_URL}/admin"
CATEGORIES_URL = "/api/v1/product-categories"


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers(RoleName.ADMIN)


@pytest.fixture
def category(make_category):
    return make_category("Suplementos")


@pytest.fixture
def product(make_product, category):
    return make_product(category, "Proteína whey 1 kg", 3490, stock=20)


@pytest.fixture
def make_order_for(db, make_user):

    def _make_order_for(product: Product) -> Order:
        order = Order(user_id=make_user().id)
        order.items.append(
            OrderItem(product_id=product.id, quantity=1, unit_price_cents=product.price_cents)
        )
        db.add(order)
        db.commit()
        return order

    return _make_order_for


def _product_body(category_id: int, **overrides) -> dict:
    body = {
        "category_id": category_id,
        "name": "Straps de agarre",
        "description": "Algodón.",
        "price_cents": 1290,
        "stock": 5,
    }
    return {**body, **overrides}


def _public_names(client) -> list[str]:
    return [item["name"] for item in client.get(PRODUCTS_URL).json()["items"]]


ADMIN_CALLS = [
    ("get", ADMIN_PRODUCTS_URL),
    ("post", PRODUCTS_URL),
    ("patch", f"{PRODUCTS_URL}/1"),
    ("delete", f"{PRODUCTS_URL}/1"),
    ("post", CATEGORIES_URL),
    ("patch", f"{CATEGORIES_URL}/1"),
    ("delete", f"{CATEGORIES_URL}/1"),
]


def _call(client, method: str, url: str, headers: dict | None = None):
    kwargs = {"headers": headers or {}}
    if method in ("post", "patch"):
        kwargs["json"] = {"name": "X", "category_id": 1, "price_cents": 100}
    return getattr(client, method)(url, **kwargs)


@pytest.mark.parametrize(("method", "url"), ADMIN_CALLS)
def test_admin_endpoints_without_token_return_401(client, product, method, url):
    response = _call(client, method, url)

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
@pytest.mark.parametrize(("method", "url"), ADMIN_CALLS)
def test_admin_endpoints_reject_member_and_trainer(client, auth_headers, product, role, method, url):
    response = _call(client, method, url, auth_headers(role))

    assert response.status_code == 403


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_forbidden_create_does_not_save_anything(client, db, auth_headers, category, role):
    client.post(PRODUCTS_URL, headers=auth_headers(role), json=_product_body(category.id))

    assert db.query(Product).count() == 0


@pytest.mark.parametrize("role", [RoleName.ADMIN, RoleName.SUPERADMIN])
def test_admin_and_superadmin_create_a_product(client, auth_headers, category, role):
    response = client.post(PRODUCTS_URL, headers=auth_headers(role), json=_product_body(category.id))

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "category_id": category.id,
        "category_name": "Suplementos",
        "name": "Straps de agarre",
        "description": "Algodón.",
        "price_cents": 1290,
        "stock": 5,
        "in_stock": True,
        "is_active": True,
    }
    assert _public_names(client) == ["Straps de agarre"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_cents": -1},
        {"stock": -1},
        {"price_cents": 1_000_001},
        {"name": "   "},
        {"name": "x" * 121},
        {"price_cents": "gratis"},
    ],
)
def test_create_product_with_invalid_values_returns_422(client, db, admin_headers, category, overrides):
    response = client.post(
        PRODUCTS_URL, headers=admin_headers, json=_product_body(category.id, **overrides)
    )

    assert response.status_code == 422
    assert db.query(Product).count() == 0


def test_create_product_in_unknown_category_returns_422(client, admin_headers):
    response = client.post(PRODUCTS_URL, headers=admin_headers, json=_product_body(9999))

    assert response.status_code == 422
    assert response.json() == {"detail": UNKNOWN_CATEGORY, "code": "validation_error"}


def test_create_product_ignores_fields_that_are_not_in_the_schema(client, admin_headers, category):
    response = client.post(
        PRODUCTS_URL,
        headers=admin_headers,
        json=_product_body(category.id, id=999, is_active=False),
    )

    assert response.status_code == 201
    assert response.json()["id"] != 999
    assert response.json()["is_active"] is True


def test_update_product_changes_only_the_fields_sent(client, admin_headers, product, make_category):
    clothing = make_category("Ropa")

    response = client.patch(
        f"{PRODUCTS_URL}/{product.id}",
        headers=admin_headers,
        json={"price_cents": 2990, "category_id": clothing.id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["price_cents"] == 2990
    assert body["category_id"] == clothing.id
    assert body["category_name"] == "Ropa"
    assert body["name"] == "Proteína whey 1 kg"
    assert body["stock"] == 20


@pytest.mark.parametrize(
    "body",
    [{"price_cents": -5}, {"stock": -1}, {"name": None}, {"price_cents": None}, {"is_active": None}],
)
def test_update_product_with_invalid_values_returns_422(client, admin_headers, product, body):
    response = client.patch(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers, json=body)

    assert response.status_code == 422


def test_update_product_allows_clearing_the_description(client, admin_headers, product):
    response = client.patch(
        f"{PRODUCTS_URL}/{product.id}", headers=admin_headers, json={"description": None}
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_product_to_unknown_category_returns_422(client, admin_headers, product):
    response = client.patch(
        f"{PRODUCTS_URL}/{product.id}", headers=admin_headers, json={"category_id": 9999}
    )

    assert response.status_code == 422
    assert response.json()["detail"] == UNKNOWN_CATEGORY


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_product_returns_404(client, admin_headers, method):
    kwargs = {"json": {"stock": 1}} if method == "patch" else {}

    response = getattr(client, method)(f"{PRODUCTS_URL}/9999", headers=admin_headers, **kwargs)

    assert response.status_code == 404


def test_delete_product_with_orders_deactivates_it(client, db, admin_headers, product, make_order_for):
    order = make_order_for(product)

    response = client.delete(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    db.refresh(product)
    assert product.is_active is False
    assert db.get(Order, order.id).items[0].product_id == product.id
    assert _public_names(client) == []


def test_delete_product_without_orders_also_deactivates_it(client, db, admin_headers, product):
    response = client.delete(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers)

    assert response.status_code == 200
    assert db.get(Product, product.id) is not None
    assert response.json()["is_active"] is False


def test_delete_product_twice_is_idempotent(client, admin_headers, product):
    client.delete(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers)

    response = client.delete(f"{PRODUCTS_URL}/{product.id}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_patch_is_active_true_reactivates_a_product(client, admin_headers, make_product, category):
    old = make_product(category, "Sudadera antigua", is_active=False)

    response = client.patch(
        f"{PRODUCTS_URL}/{old.id}", headers=admin_headers, json={"is_active": True}
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert _public_names(client) == ["Sudadera antigua"]


def test_admin_list_includes_inactive_products(client, admin_headers, make_product, category):
    make_product(category, "Camiseta Brava")
    make_product(category, "Sudadera antigua", is_active=False)

    response = client.get(ADMIN_PRODUCTS_URL, headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [(item["name"], item["is_active"]) for item in body["items"]] == [
        ("Camiseta Brava", True),
        ("Sudadera antigua", False),
    ]


def test_admin_list_keeps_filters_and_pagination(client, admin_headers, make_product, make_category):
    clothing = make_category("Ropa")
    make_product(clothing, "Camiseta Brava")
    make_product(clothing, "Leggings Brava", is_active=False)
    make_product(make_category("Suplementos"), "Creatina")

    response = client.get(
        ADMIN_PRODUCTS_URL,
        headers=admin_headers,
        params={"category_id": clothing.id, "page": 2, "size": 1},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["name"] for item in response.json()["items"]] == ["Leggings Brava"]


def test_admin_creates_a_category(client, admin_headers):
    response = client.post(CATEGORIES_URL, headers=admin_headers, json={"name": "  Accesorios "})

    assert response.status_code == 201
    assert response.json() == {"id": response.json()["id"], "name": "Accesorios"}
    assert client.get(CATEGORIES_URL).json() == [response.json()]


@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
def test_create_category_with_invalid_name_returns_422(client, admin_headers, name):
    response = client.post(CATEGORIES_URL, headers=admin_headers, json={"name": name})

    assert response.status_code == 422


def test_create_category_with_repeated_name_returns_409(client, admin_headers, category):
    response = client.post(CATEGORIES_URL, headers=admin_headers, json={"name": "Suplementos"})

    assert response.status_code == 409
    assert response.json() == {"detail": CATEGORY_NAME_TAKEN, "code": "conflict"}


def test_rename_category(client, admin_headers, category):
    response = client.patch(
        f"{CATEGORIES_URL}/{category.id}", headers=admin_headers, json={"name": "Nutrición"}
    )

    assert response.status_code == 200
    assert response.json() == {"id": category.id, "name": "Nutrición"}


def test_rename_category_to_an_existing_name_returns_409(client, admin_headers, category, make_category):
    clothing = make_category("Ropa")

    response = client.patch(
        f"{CATEGORIES_URL}/{clothing.id}", headers=admin_headers, json={"name": "Suplementos"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == CATEGORY_NAME_TAKEN


def test_delete_empty_category_returns_204(client, db, admin_headers, category):
    response = client.delete(f"{CATEGORIES_URL}/{category.id}", headers=admin_headers)

    assert response.status_code == 204
    assert db.get(ProductCategory, category.id) is None


@pytest.mark.parametrize("is_active", [True, False])
def test_delete_category_with_products_returns_409(
        client, db, admin_headers, make_product, category, is_active
):
    make_product(category, is_active=is_active)

    response = client.delete(f"{CATEGORIES_URL}/{category.id}", headers=admin_headers)

    assert response.status_code == 409
    assert response.json() == {"detail": CATEGORY_HAS_PRODUCTS, "code": "conflict"}
    assert db.get(ProductCategory, category.id) is not None


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_category_returns_404(client, admin_headers, method):
    kwargs = {"json": {"name": "Nada"}} if method == "patch" else {}

    response = getattr(client, method)(f"{CATEGORIES_URL}/9999", headers=admin_headers, **kwargs)

    assert response.status_code == 404