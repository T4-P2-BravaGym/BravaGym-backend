"""In-memory TTL cache for public read responses (HU-28).

Stores JSON-serialisable payloads only — never SQLAlchemy instances — so a cache
hit does not depend on a live database session.
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TtlCache:
    """Thread-safe dict cache with per-entry expiry."""

    def __init__(self, default_ttl_seconds: float = 60.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._entries: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= time.monotonic():
                del self._entries[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        with self._lock:
            self._entries[key] = (time.monotonic() + ttl, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def delete_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in [k for k in self._entries if k.startswith(prefix)]:
                del self._entries[key]

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            now = time.monotonic()
            expired = [key for key, (expires_at, _) in self._entries.items() if expires_at <= now]
            for key in expired:
                del self._entries[key]
            return len(self._entries)


PLANS_CACHE_KEY = "plans:active"
PRODUCTS_CACHE_PREFIX = "products:"

# Module singleton used by plan/product services. TTL is refreshed from settings
# on first use via configure_response_cache().
response_cache = TtlCache()


def configure_response_cache(ttl_seconds: float) -> TtlCache:
    """Point the shared cache at the configured TTL (idempotent for tests)."""
    response_cache.default_ttl_seconds = ttl_seconds
    return response_cache


def invalidate_plans_cache() -> None:
    response_cache.delete(PLANS_CACHE_KEY)


def invalidate_products_cache() -> None:
    response_cache.delete_prefix(PRODUCTS_CACHE_PREFIX)


def products_cache_key(
    *,
    category_id: int | None,
    min_price: int | None,
    max_price: int | None,
    q: str | None,
    sort: str,
    page: int,
    size: int,
) -> str:
    search = (q or "").strip().casefold()
    return (
        f"{PRODUCTS_CACHE_PREFIX}"
        f"category={category_id}|min={min_price}|max={max_price}|"
        f"q={search}|sort={sort}|page={page}|size={size}"
    )
