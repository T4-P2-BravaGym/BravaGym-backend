import pytest

from app.services.shop_service import INVALID_PRICE_RANGE

PRODUCTS_URL = "/api/v1/products"
CATEGORIES_URL = "/api/v1/product-categories"


@pytest.fixture
def shop(make_category, make_product):
    supplements = make_category("Suplementos")
    clothing = make_category("Ropa")
    return {
        "supplements": supplements,
        "clothing": clothing,
        "whey": make_product(supplements, "Proteína whey 1 kg", 3490, stock=20),
        "creatine": make_product(supplements, "Creatina 300 g", 2290, stock=0),
        "tshirt": make_product(clothing, "Camiseta Brava", 2200),
        "leggings": make_product(clothing, "Leggings Brava", 3900),
        "old": make_product(clothing, "Sudadera antigua", 2500, is_active=False),
    }


def _names(response) -> list[str]:
    return [item["name"] for item in response.json()["items"]]


def test_get_products_is_public_and_lists_only_active_by_name(client, shop):
    response = client.get(PRODUCTS_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["total"] == 4
    assert body["page"] == 1
    assert body["size"] == 20
    assert _names(response) == [
        "Camiseta Brava",
        "Creatina 300 g",
        "Leggings Brava",
        "Proteína whey 1 kg",
    ]


def test_get_products_returns_only_safe_fields(client, shop):
    response = client.get(PRODUCTS_URL, params={"q": "whey"})

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "id": shop["whey"].id,
            "category_id": shop["supplements"].id,
            "category_name": "Suplementos",
            "name": "Proteína whey 1 kg",
            "description": None,
            "price_cents": 3490,
            "stock": 20,
            "in_stock": True,
        }
    ]


def test_sold_out_product_is_listed_as_not_in_stock(client, shop):
    response = client.get(PRODUCTS_URL, params={"category_id": shop["supplements"].id})

    assert response.status_code == 200
    by_name = {item["name"]: item for item in response.json()["items"]}
    assert by_name["Creatina 300 g"]["in_stock"] is False
    assert by_name["Creatina 300 g"]["stock"] == 0
    assert by_name["Proteína whey 1 kg"]["in_stock"] is True


def test_filter_by_category(client, shop):
    response = client.get(PRODUCTS_URL, params={"category_id": shop["clothing"].id})

    assert response.status_code == 200
    assert _names(response) == ["Camiseta Brava", "Leggings Brava"]
    assert response.json()["total"] == 2


def test_filter_by_price_range_includes_both_limits(client, shop):
    response = client.get(PRODUCTS_URL, params={"min_price": 2200, "max_price": 3490})

    assert response.status_code == 200
    assert _names(response) == ["Camiseta Brava", "Creatina 300 g", "Proteína whey 1 kg"]


def test_filter_by_category_and_price_together(client, shop):
    response = client.get(
        PRODUCTS_URL,
        params={"category_id": shop["clothing"].id, "max_price": 3000},
    )

    assert response.status_code == 200
    assert _names(response) == ["Camiseta Brava"]


def test_search_by_name_is_case_insensitive(client, shop):
    response = client.get(PRODUCTS_URL, params={"q": "BRAVA"})

    assert response.status_code == 200
    assert _names(response) == ["Camiseta Brava", "Leggings Brava"]


def test_search_treats_wildcards_as_text(client, shop):
    response = client.get(PRODUCTS_URL, params={"q": "%"})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_sort_by_price_ascending(client, shop):
    response = client.get(PRODUCTS_URL, params={"sort": "price_asc"})

    assert response.status_code == 200
    assert [item["price_cents"] for item in response.json()["items"]] == [2200, 2290, 3490, 3900]


def test_sort_by_price_descending(client, shop):
    response = client.get(PRODUCTS_URL, params={"sort": "price_desc"})

    assert response.status_code == 200
    assert [item["price_cents"] for item in response.json()["items"]] == [3900, 3490, 2290, 2200]


def test_sort_works_together_with_filters_and_pagination(client, shop):
    response = client.get(
        PRODUCTS_URL,
        params={"sort": "price_desc", "max_price": 3500, "page": 2, "size": 2},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert _names(response) == ["Camiseta Brava"]


def test_unknown_category_returns_empty_page(client, shop):
    response = client.get(PRODUCTS_URL, params={"category_id": 9999})

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_pagination_returns_the_requested_page(client, shop):
    response = client.get(PRODUCTS_URL, params={"page": 2, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 4
    assert body["page"] == 2
    assert body["size"] == 2
    assert _names(response) == ["Leggings Brava", "Proteína whey 1 kg"]


def test_min_price_greater_than_max_price_returns_422(client, shop):
    response = client.get(PRODUCTS_URL, params={"min_price": 3000, "max_price": 1000})

    assert response.status_code == 422
    assert response.json() == {"detail": INVALID_PRICE_RANGE, "code": "validation_error"}


@pytest.mark.parametrize(
    "params",
    [
        {"size": 101},
        {"page": 0},
        {"min_price": -1},
        {"max_price": 1_000_001},
        {"category_id": 0},
        {"min_price": "abc"},
        {"q": "x" * 61},
        {"sort": "price"},
    ],
)
def test_invalid_query_parameters_return_422(client, params):
    response = client.get(PRODUCTS_URL, params=params)

    assert response.status_code == 422


def test_get_product_categories_is_public_and_sorted_by_name(client, shop):
    response = client.get(CATEGORIES_URL)

    assert response.status_code == 200
    assert response.json() == [
        {"id": shop["clothing"].id, "name": "Ropa"},
        {"id": shop["supplements"].id, "name": "Suplementos"},
    ]