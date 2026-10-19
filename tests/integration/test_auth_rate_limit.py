"""HTTP acceptance tests for auth attempt limits (HU-34)."""

from app.core.rate_limit import (
    TOO_MANY_ATTEMPTS,
    login_attempt_limiter,
    register_attempt_limiter,
)
from app.models.enums import RoleName
from freezegun import freeze_time

from tests.conftest import TEST_PASSWORD

LOGIN_URL = "/api/v1/auth/login"
REGISTER_URL = "/api/v1/auth/register"


def login(client, email: str, password: str, *, ip: str = "203.0.113.10"):
    return client.post(
        LOGIN_URL,
        data={"username": email, "password": password},
        headers={"X-Forwarded-For": ip},
    )


def register(client, email: str, *, ip: str = "203.0.113.20"):
    return client.post(
        REGISTER_URL,
        json={
            "email": email,
            "password": "BravaDemo2026!",
            "first_name": "Lucía",
            "last_name": "Gil",
        },
        headers={"X-Forwarded-For": ip},
    )


def test_sixth_failed_login_returns_429_with_retry_after_even_if_password_correct(
    client, make_user
):
    member = make_user(RoleName.MEMBER, email="locked@example.com")
    login_attempt_limiter.configure(max_attempts=5, window_seconds=900)

    with freeze_time("2026-10-14 12:00:00"):
        for _ in range(5):
            response = login(client, member.email, "wrong-password")
            assert response.status_code == 401

        # Sixth attempt: correct password still blocked.
        blocked = login(client, member.email, TEST_PASSWORD)
        assert blocked.status_code == 429
        assert blocked.json() == {
            "detail": TOO_MANY_ATTEMPTS,
            "code": "rate_limited",
        }
        assert "Retry-After" in blocked.headers
        assert int(blocked.headers["Retry-After"]) > 0


def test_successful_login_resets_failed_attempt_counter(client, make_user):
    member = make_user(email="reset@example.com")
    login_attempt_limiter.configure(max_attempts=5, window_seconds=900)

    with freeze_time("2026-10-14 12:00:00"):
        for _ in range(4):
            assert login(client, member.email, "wrong-password").status_code == 401

        ok = login(client, member.email, TEST_PASSWORD)
        assert ok.status_code == 200

        # Counter cleared: five more failures are allowed again.
        for _ in range(5):
            assert login(client, member.email, "wrong-password").status_code == 401
        assert login(client, member.email, TEST_PASSWORD).status_code == 429


def test_login_allowed_again_after_window_expires(client, make_user):
    member = make_user(email="window@example.com")
    login_attempt_limiter.configure(max_attempts=5, window_seconds=900)

    with freeze_time("2026-10-14 12:00:00") as frozen:
        for _ in range(5):
            assert login(client, member.email, "wrong-password").status_code == 401
        assert login(client, member.email, TEST_PASSWORD).status_code == 429

        frozen.tick(901)
        assert login(client, member.email, TEST_PASSWORD).status_code == 200


def test_login_limit_is_per_email_and_ip(client, make_user):
    member = make_user(email="same@example.com")
    other = make_user(email="other@example.com")
    login_attempt_limiter.configure(max_attempts=5, window_seconds=900)

    with freeze_time("2026-10-14 12:00:00"):
        for _ in range(5):
            assert (
                login(client, member.email, "wrong", ip="198.51.100.1").status_code
                == 401
            )

        # Same email, different IP → still allowed.
        assert (
            login(client, member.email, TEST_PASSWORD, ip="198.51.100.2").status_code
            == 200
        )
        # Different email, same IP → still allowed.
        assert (
            login(client, other.email, TEST_PASSWORD, ip="198.51.100.1").status_code
            == 200
        )


def test_eleventh_register_from_same_ip_returns_429(client, roles):
    register_attempt_limiter.configure(max_attempts=10, window_seconds=3600)
    ip = "198.51.100.50"

    with freeze_time("2026-10-14 15:00:00"):
        for i in range(10):
            response = register(client, f"user{i}@example.com", ip=ip)
            assert response.status_code == 201, response.text

        blocked = register(client, "user10@example.com", ip=ip)
        assert blocked.status_code == 429
        assert blocked.json()["code"] == "rate_limited"
        assert int(blocked.headers["Retry-After"]) > 0

        # Different IP is unaffected.
        assert (
            register(client, "other-ip@example.com", ip="198.51.100.51").status_code
            == 201
        )


def test_register_allowed_again_after_window_expires(client, roles):
    register_attempt_limiter.configure(max_attempts=2, window_seconds=3600)

    with freeze_time("2026-10-14 15:00:00") as frozen:
        assert register(client, "a@example.com").status_code == 201
        assert register(client, "b@example.com").status_code == 201
        assert register(client, "c@example.com").status_code == 429

        frozen.tick(3601)
        assert register(client, "c@example.com").status_code == 201
