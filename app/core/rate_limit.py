"""In-memory attempt-window rate limiter for auth endpoints (HU-34).

Stores timestamps per key. Safe for a **single process** only — several Uvicorn
workers do not share counters. See README.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

from fastapi import Request

from app.core.exceptions import RateLimitError

TOO_MANY_ATTEMPTS = "Demasiados intentos. Vuelve a probar más tarde."


class AttemptWindowLimiter:
    """Sliding-window counter: block when ``max_attempts`` timestamps fall in the window."""

    def __init__(
        self,
        *,
        max_attempts: int = 5,
        window_seconds: float = 900.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        # Call through a lambda so freezegun can patch time.time later.
        self._clock: Callable[[], float] = clock or (lambda: time.time())
        self._attempts: dict[str, list[float]] = {}
        self._lock = threading.RLock()

    def configure(self, *, max_attempts: int, window_seconds: float) -> None:
        with self._lock:
            self.max_attempts = max_attempts
            self.window_seconds = float(window_seconds)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def _prune_unlocked(self, key: str, now: float) -> list[float]:
        cutoff = now - self.window_seconds
        kept = [ts for ts in self._attempts.get(key, []) if ts > cutoff]
        if kept:
            self._attempts[key] = kept
        else:
            self._attempts.pop(key, None)
        return kept

    def retry_after_seconds(self, key: str) -> int:
        """Seconds until the oldest attempt leaves the window; 0 if under the cap."""
        with self._lock:
            now = self._clock()
            kept = self._prune_unlocked(key, now)
            if len(kept) < self.max_attempts:
                return 0
            oldest = min(kept)
            return max(1, math.ceil(oldest + self.window_seconds - now))

    def is_blocked(self, key: str) -> bool:
        return self.retry_after_seconds(key) > 0

    def record(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            kept = self._prune_unlocked(key, now)
            kept.append(now)
            self._attempts[key] = kept

    def record_if_allowed(self, key: str) -> bool:
        """Atomically reserve one attempt, for background recovery deliveries."""
        with self._lock:
            now = self._clock()
            kept = self._prune_unlocked(key, now)
            if len(kept) >= self.max_attempts:
                return False
            kept.append(now)
            self._attempts[key] = kept
            return True

    def assert_allowed(self, key: str, *, detail: str = TOO_MANY_ATTEMPTS) -> None:
        wait = self.retry_after_seconds(key)
        if wait > 0:
            raise RateLimitError(detail, retry_after=wait)


# Module singletons — reconfigured from settings in main; replaceable in tests.
login_attempt_limiter = AttemptWindowLimiter(max_attempts=5, window_seconds=900.0)
register_attempt_limiter = AttemptWindowLimiter(max_attempts=10, window_seconds=3600.0)
# HU-32: wrong current passwords when changing it, counted per user
password_change_limiter = AttemptWindowLimiter(max_attempts=5, window_seconds=900.0)


def configure_auth_rate_limits(
    *,
    login_max_attempts: int,
    login_window_seconds: float,
    register_max_attempts: int,
    register_window_seconds: float,
) -> None:
    """Apply env-backed thresholds to the shared limiters (idempotent for tests)."""
    login_attempt_limiter.configure(
        max_attempts=login_max_attempts,
        window_seconds=login_window_seconds,
    )
    register_attempt_limiter.configure(
        max_attempts=register_max_attempts,
        window_seconds=register_window_seconds,
    )


def client_ip(request: Request) -> str:
    """Best-effort client IP (first X-Forwarded-For hop, else ASGI client host)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def login_rate_key(email: str, ip: str) -> str:
    from app.services.auth_service import normalize_email

    return f"login:{normalize_email(email)}|{ip}"


def register_rate_key(ip: str) -> str:
    return f"register:{ip}"


def password_change_rate_key(user_id: int) -> str:
    return f"password:{user_id}"
