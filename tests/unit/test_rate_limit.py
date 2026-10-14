"""Unit tests for the in-memory attempt-window limiter (HU-34)."""

from types import SimpleNamespace

from app.core.exceptions import RateLimitError
from app.core.rate_limit import AttemptWindowLimiter, client_ip, login_rate_key
from freezegun import freeze_time


def test_blocks_after_max_attempts_in_window():
    limiter = AttemptWindowLimiter(max_attempts=3, window_seconds=60)

    with freeze_time("2026-10-14 10:00:00") as frozen:
        for _ in range(3):
            limiter.record("k")
            frozen.tick(1)

        assert limiter.is_blocked("k")
        assert limiter.retry_after_seconds("k") >= 1

        try:
            limiter.assert_allowed("k")
            raise AssertionError("expected RateLimitError")
        except RateLimitError as exc:
            assert exc.status_code == 429
            assert exc.headers["Retry-After"].isdigit()


def test_window_expiry_allows_again():
    limiter = AttemptWindowLimiter(max_attempts=2, window_seconds=60)

    with freeze_time("2026-10-14 10:00:00") as frozen:
        limiter.record("k")
        limiter.record("k")
        assert limiter.is_blocked("k")

        frozen.tick(61)
        assert not limiter.is_blocked("k")
        limiter.assert_allowed("k")


def test_reset_clears_counter():
    limiter = AttemptWindowLimiter(max_attempts=2, window_seconds=900)

    with freeze_time("2026-10-14 10:00:00"):
        limiter.record("k")
        limiter.record("k")
        assert limiter.is_blocked("k")
        limiter.reset("k")
        assert not limiter.is_blocked("k")


def test_configure_updates_thresholds():
    limiter = AttemptWindowLimiter(max_attempts=5, window_seconds=900)
    limiter.configure(max_attempts=1, window_seconds=30)

    with freeze_time("2026-10-14 10:00:00"):
        limiter.record("k")
        assert limiter.is_blocked("k")
        assert limiter.retry_after_seconds("k") <= 30


def test_client_ip_prefers_forwarded_for_then_host():
    forwarded = SimpleNamespace(
        headers={"x-forwarded-for": "203.0.113.9, 10.0.0.1"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    assert client_ip(forwarded) == "203.0.113.9"

    direct = SimpleNamespace(headers={}, client=SimpleNamespace(host="127.0.0.1"))
    assert client_ip(direct) == "127.0.0.1"

    blank = SimpleNamespace(headers={"x-forwarded-for": "  , "}, client=None)
    assert client_ip(blank) == "unknown"

    missing = SimpleNamespace(headers={}, client=None)
    assert client_ip(missing) == "unknown"


def test_login_rate_key_normalizes_email():
    assert login_rate_key("  Lucia@Example.com ", "1.2.3.4") == (
        "login:lucia@example.com|1.2.3.4"
    )
