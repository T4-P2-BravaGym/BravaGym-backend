from datetime import timedelta

import pytest
from app.core.config import get_settings
from app.models import RefreshToken, RevokedToken
from app.models.types import utc_now
from freezegun import freeze_time
from sqlalchemy import func, select

from tests.conftest import TEST_PASSWORD

AUTH = "/api/v1/auth"
COOKIE = "brava.refresh"
CSRF = {"X-Brava-CSRF": "1"}


def login_session(client, user, headers=None):
    return client.post(
        AUTH + "/login",
        data={"username": user.email, "password": TEST_PASSWORD},
        headers=headers,
    )


def test_login_sets_httponly_refresh_and_keeps_swagger_bearer_response(
    client, make_user
):
    response = login_session(client, make_user())
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "token_type"}
    assert response.json()["token_type"] == "bearer"
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "path=/api/v1/auth" in cookie
    assert "samesite=lax" in cookie
    assert "domain=" not in cookie
    assert response.cookies.get(COOKIE)
    assert response.headers["cache-control"] == "no-store"


def test_refresh_rotates_cookie_and_rejects_old_cookie(client, make_user):
    login = login_session(client, make_user())
    old_refresh = login.cookies.get(COOKIE)
    response = client.post(AUTH + "/refresh", headers=CSRF)
    assert response.status_code == 200
    assert response.json()["access_token"] != login.json()["access_token"]
    assert response.cookies.get(COOKIE) != old_refresh
    assert "refresh_token" not in response.json()
    client.cookies.clear()
    client.cookies.set(COOKIE, old_refresh, path=AUTH)
    assert client.post(AUTH + "/refresh", headers=CSRF).status_code == 401


def test_logout_invalidates_access_refresh_and_clears_cookie(client, make_user):
    login = login_session(client, make_user())
    old_refresh = login.cookies.get(COOKIE)
    bearer = {"Authorization": "Bearer " + login.json()["access_token"]}
    response = client.post(AUTH + "/logout", headers={**CSRF, **bearer})
    assert response.status_code == 204
    assert response.content == b""
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/api/v1/users/me", headers=bearer).status_code == 401
    client.cookies.clear()
    client.cookies.set(COOKIE, old_refresh, path=AUTH)
    assert client.post(AUTH + "/refresh", headers=CSRF).status_code == 401


@pytest.mark.parametrize("path", ["/refresh", "/logout"])
def test_session_endpoints_reject_missing_csrf_header_without_revoking(
    client, db, make_user, path
):
    login_session(client, make_user())
    response = client.post(AUTH + path)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 1
    assert db.scalar(select(RefreshToken)).revoked_at is None


@pytest.mark.parametrize("path", ["/refresh", "/logout"])
def test_session_endpoints_reject_untrusted_origin(client, db, make_user, path):
    login_session(client, make_user())
    response = client.post(
        AUTH + path, headers={**CSRF, "Origin": "https://untrusted.example"}
    )
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert db.scalar(select(RefreshToken)).revoked_at is None


def test_login_rejects_untrusted_origin_before_issuing_session(client, db, make_user):
    response = login_session(
        client, make_user(), headers={"Origin": "https://untrusted.example"}
    )
    assert response.status_code == 403
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0


def test_allowed_frontend_origin_can_refresh(client, make_user):
    login_session(client, make_user(), headers={"Origin": "http://localhost:5173"})
    response = client.post(
        AUTH + "/refresh", headers={**CSRF, "Origin": "http://localhost:5173"}
    )
    assert response.status_code == 200


def test_swagger_origin_can_log_in_and_refresh(client, make_user):
    login_session(client, make_user(), headers={"Origin": "http://testserver"})
    response = client.post(
        AUTH + "/refresh", headers={**CSRF, "Origin": "http://testserver"}
    )
    assert response.status_code == 200


def test_refresh_without_cookie_returns_401_and_clears_cookie(client):
    response = client.post(AUTH + "/refresh", headers=CSRF)
    assert response.status_code == 401
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_invalid_cookie_returns_401_and_clears_cookie(client):
    client.cookies.set(COOKIE, "invalid-token", path=AUTH)
    response = client.post(AUTH + "/refresh", headers=CSRF)
    assert response.status_code == 401
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_expired_refresh_returns_401(client, make_user):
    with freeze_time("2026-10-06 10:00:00"):
        login_session(client, make_user())
    with freeze_time("2026-10-13 10:00:00"):
        assert client.post(AUTH + "/refresh", headers=CSRF).status_code == 401


def test_deactivated_user_cannot_refresh(client, db, make_user):
    user = make_user()
    login_session(client, user)
    user.is_active = False
    db.commit()
    assert client.post(AUTH + "/refresh", headers=CSRF).status_code == 401


def test_logout_accepts_expired_access_with_valid_own_refresh(client, db, make_user):
    with freeze_time("2026-10-06 10:00:00"):
        login = login_session(client, make_user())
    with freeze_time("2026-10-06 11:01:00"):
        response = client.post(
            AUTH + "/logout",
            headers={**CSRF, "Authorization": "Bearer " + login.json()["access_token"]},
        )
    assert response.status_code == 204
    assert db.scalar(select(RefreshToken)).revoked_at is not None
    assert db.scalar(select(func.count()).select_from(RevokedToken)) == 0


def test_logout_cannot_use_another_users_refresh(client, db, make_user):
    first = login_session(client, make_user())
    login_session(client, make_user())
    response = client.post(
        AUTH + "/logout",
        headers={**CSRF, "Authorization": "Bearer " + first.json()["access_token"]},
    )
    assert response.status_code == 401
    assert all(row.revoked_at is None for row in db.scalars(select(RefreshToken)))


def test_production_cookie_requires_https(client, make_user, monkeypatch):
    monkeypatch.setattr(get_settings(), "environment", "production")
    response = login_session(client, make_user())
    assert "secure" in response.headers["set-cookie"].lower()


def test_login_cleans_only_expired_access_revocations(client, db, make_user):
    db.add_all(
        [
            RevokedToken(jti="expired", expires_at=utc_now() - timedelta(seconds=1)),
            RevokedToken(jti="live", expires_at=utc_now() + timedelta(hours=1)),
        ]
    )
    db.commit()
    assert login_session(client, make_user()).status_code == 200
    assert db.get(RevokedToken, "expired") is None
    assert db.get(RevokedToken, "live") is not None


def test_login_rejects_cross_site_browser_request_without_origin(client, db, make_user):
    response = login_session(
        client, make_user(), headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert response.status_code == 403
    assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0
