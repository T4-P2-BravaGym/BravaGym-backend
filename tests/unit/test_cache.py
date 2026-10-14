"""Unit tests for the in-memory TTL cache (HU-28)."""

from freezegun import freeze_time

from app.core.cache import TtlCache, products_cache_key


def test_get_returns_none_for_missing_key():
    cache = TtlCache(default_ttl_seconds=60)
    assert cache.get("missing") is None


def test_set_then_get_returns_value():
    cache = TtlCache(default_ttl_seconds=60)
    cache.set("plans:active", [{"id": 1}])
    assert cache.get("plans:active") == [{"id": 1}]


def test_expired_entry_is_a_miss():
    cache = TtlCache(default_ttl_seconds=30)
    with freeze_time("2026-10-14 12:00:00") as frozen:
        cache.set("plans:active", ["stale"])
        frozen.tick(31)
        assert cache.get("plans:active") is None


def test_delete_removes_key():
    cache = TtlCache(default_ttl_seconds=60)
    cache.set("plans:active", [1])
    cache.delete("plans:active")
    assert cache.get("plans:active") is None


def test_delete_prefix_clears_matching_keys_only():
    cache = TtlCache(default_ttl_seconds=60)
    cache.set("products:a", 1)
    cache.set("products:b", 2)
    cache.set("plans:active", 3)
    cache.delete_prefix("products:")
    assert cache.get("products:a") is None
    assert cache.get("products:b") is None
    assert cache.get("plans:active") == 3


def test_products_cache_key_is_stable_for_same_filters():
    assert products_cache_key(
        category_id=2,
        min_price=100,
        max_price=5000,
        q="  Whey ",
        sort="name",
        page=1,
        size=20,
    ) == products_cache_key(
        category_id=2,
        min_price=100,
        max_price=5000,
        q="whey",
        sort="name",
        page=1,
        size=20,
    )


def test_products_cache_key_changes_with_page():
    base = dict(
        category_id=None,
        min_price=None,
        max_price=None,
        q=None,
        sort="name",
        size=20,
    )
    assert products_cache_key(page=1, **base) != products_cache_key(page=2, **base)
