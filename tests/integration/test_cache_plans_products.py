"""Integration ACs for HU-28: public /plans and /products cache + invalidation."""

from app.models.enums import RoleName
from app.models.membership import MembershipPlan


def test_second_get_plans_is_served_from_cache(client, db, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=2990)

    first = client.get("/api/v1/plans")
    assert first.status_code == 200
    assert first.json()[0]["name"] == "Basic"

    stored = db.get(MembershipPlan, plan.id)
    stored.name = "Changed in DB"
    db.commit()

    second = client.get("/api/v1/plans")
    assert second.status_code == 200
    assert second.json()[0]["name"] == "Basic"


def test_admin_plan_update_invalidates_plans_cache(client, db, auth_headers, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=2990)
    assert client.get("/api/v1/plans").json()[0]["name"] == "Basic"

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"name": "Strength"},
    )
    assert response.status_code == 200

    listed = client.get("/api/v1/plans")
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Strength"


def test_admin_plan_create_appears_on_next_public_list(client, auth_headers, make_plan):
    make_plan(name="Basic", monthly_price_cents=2990)
    client.get("/api/v1/plans")

    created = client.post(
        "/api/v1/plans",
        headers=auth_headers(RoleName.ADMIN),
        json={"name": "Premium", "monthly_price_cents": 5990},
    )
    assert created.status_code == 201

    names = [item["name"] for item in client.get("/api/v1/plans").json()]
    assert names == ["Basic", "Premium"]


def test_admin_plan_delete_invalidates_plans_cache(client, auth_headers, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=2990)
    client.get("/api/v1/plans")

    deleted = client.delete(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
    )
    assert deleted.status_code == 200
    assert client.get("/api/v1/plans").json() == []


def test_second_get_products_is_served_from_cache(client, db, make_category, make_product):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)

    first = client.get("/api/v1/products")
    assert first.status_code == 200
    assert first.json()["items"][0]["name"] == "Proteína whey"

    product.name = "Changed in DB"
    db.commit()

    second = client.get("/api/v1/products")
    assert second.status_code == 200
    assert second.json()["items"][0]["name"] == "Proteína whey"


def test_admin_product_update_invalidates_products_cache(
    client, auth_headers, make_category, make_product
):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)
    assert client.get("/api/v1/products").json()["items"][0]["name"] == "Proteína whey"

    response = client.patch(
        f"/api/v1/products/{product.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"name": "Whey isolate"},
    )
    assert response.status_code == 200

    listed = client.get("/api/v1/products")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["name"] == "Whey isolate"


def test_admin_product_create_appears_on_next_public_list(
    client, auth_headers, make_category, make_product
):
    category = make_category("Suplementos")
    make_product(category, "Proteína whey", 3490)
    client.get("/api/v1/products")

    created = client.post(
        "/api/v1/products",
        headers=auth_headers(RoleName.ADMIN),
        json={
            "category_id": category.id,
            "name": "Creatina 300 g",
            "price_cents": 2290,
            "stock": 5,
        },
    )
    assert created.status_code == 201

    names = [item["name"] for item in client.get("/api/v1/products").json()["items"]]
    assert names == ["Creatina 300 g", "Proteína whey"]


def test_admin_product_delete_invalidates_products_cache(
    client, auth_headers, make_category, make_product
):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)
    client.get("/api/v1/products")

    deleted = client.delete(
        f"/api/v1/products/{product.id}",
        headers=auth_headers(RoleName.ADMIN),
    )
    assert deleted.status_code == 200
    assert client.get("/api/v1/products").json()["items"] == []
