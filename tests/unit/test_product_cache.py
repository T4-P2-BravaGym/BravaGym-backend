"""HU-28: products list cache hit, TTL expiry and CRUD invalidation."""

from freezegun import freeze_time

from app.core.cache import configure_response_cache, products_cache_key, response_cache
from app.schemas.shop import CategoryIn, ProductCreate, ProductUpdate
from app.services import shop_service
from app.services.shop_service import ProductSort


def _default_key(**overrides):
    params = dict(
        category_id=None,
        min_price=None,
        max_price=None,
        q=None,
        sort=ProductSort.NAME.value,
        page=1,
        size=20,
    )
    params.update(overrides)
    return products_cache_key(**params)


def test_second_public_products_call_is_a_cache_hit(db, make_category, make_product):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)

    first = shop_service.list_public_products(db)
    assert [item.name for item in first.items] == ["Proteína whey"]
    assert response_cache.get(_default_key()) is not None

    product.name = "Changed in DB"
    db.commit()

    second = shop_service.list_public_products(db)
    assert [item.name for item in second.items] == ["Proteína whey"]


def test_public_products_cache_key_includes_filters(db, make_category, make_product):
    supplements = make_category("Suplementos")
    clothing = make_category("Ropa")
    make_product(supplements, "Proteína whey", 3490)
    make_product(clothing, "Camiseta Brava", 2200)

    shop_service.list_public_products(db, category_id=supplements.id)
    shop_service.list_public_products(db, category_id=clothing.id)

    assert response_cache.get(_default_key(category_id=supplements.id)) is not None
    assert response_cache.get(_default_key(category_id=clothing.id)) is not None
    assert response_cache.get(_default_key()) is None


def test_create_product_invalidates_products_cache(db, make_category, make_product):
    category = make_category("Suplementos")
    make_product(category, "Proteína whey", 3490)
    shop_service.list_public_products(db)
    assert response_cache.get(_default_key()) is not None

    shop_service.create_product(
        db,
        ProductCreate(
            category_id=category.id,
            name="Creatina 300 g",
            price_cents=2290,
            stock=10,
        ),
    )
    assert response_cache.get(_default_key()) is None
    assert [item.name for item in shop_service.list_public_products(db).items] == [
        "Creatina 300 g",
        "Proteína whey",
    ]


def test_update_product_invalidates_products_cache(db, make_category, make_product):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)
    shop_service.list_public_products(db)

    shop_service.update_product(db, product.id, ProductUpdate(name="Whey isolate"))
    assert response_cache.get(_default_key()) is None
    assert shop_service.list_public_products(db).items[0].name == "Whey isolate"


def test_deactivate_product_invalidates_products_cache(db, make_category, make_product):
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)
    shop_service.list_public_products(db)

    shop_service.deactivate_product(db, product.id)
    assert response_cache.get(_default_key()) is None
    assert shop_service.list_public_products(db).items == []


def test_rename_category_invalidates_products_cache(db, make_category, make_product):
    category = make_category("Suplementos")
    make_product(category, "Proteína whey", 3490)
    shop_service.list_public_products(db)

    shop_service.update_category(db, category.id, CategoryIn(name="Nutrición"))
    assert response_cache.get(_default_key()) is None
    assert shop_service.list_public_products(db).items[0].category_name == "Nutrición"


def test_products_cache_expires_after_ttl(db, make_category, make_product):
    configure_response_cache(30)
    category = make_category("Suplementos")
    product = make_product(category, "Proteína whey", 3490)

    with freeze_time("2026-10-14 12:00:00") as frozen:
        shop_service.list_public_products(db)
        product.name = "After TTL"
        db.commit()

        frozen.tick(31)
        assert shop_service.list_public_products(db).items[0].name == "After TTL"
