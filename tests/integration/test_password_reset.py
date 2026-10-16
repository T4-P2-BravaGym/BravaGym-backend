import json
import logging
from hashlib import sha256
from urllib.parse import parse_qs, urlsplit

import pytest
from app import models
from app.core.config import get_settings
from freezegun import freeze_time
from sqlalchemy import select

REQUEST = "/api/v1/auth/password-reset"
CONFIRM = REQUEST + "/confirm"
GENERIC = {
    "detail": "Si existe una cuenta activa con ese email, recibirás un enlace para recuperar tu contraseña."
}


def test_request_endpoint_returns_generic_202_for_unknown_email(client):
    response = client.post(REQUEST, json={"email": "unknown@example.com"})
    assert response.status_code == 202
    assert response.json() == GENERIC


@pytest.fixture
def recovery(client, db, tmp_path, monkeypatch):
    from app.core.password_reset_delivery import (
        get_reset_session_factory,
        reset_delivery_limiter,
    )
    from app.main import app
    from sqlalchemy.orm import sessionmaker

    monkeypatch.setattr(get_settings(), "outbox_dir", tmp_path / "outbox")
    app.dependency_overrides[get_reset_session_factory] = lambda: sessionmaker(
        bind=db.get_bind(), expire_on_commit=False
    )
    reset_delivery_limiter.clear()
    yield tmp_path / "outbox"
    reset_delivery_limiter.clear()
    app.dependency_overrides.pop(get_reset_session_factory, None)


def read_token(outbox):
    message = json.loads(next(outbox.iterdir()).read_text())
    url = next(line for line in message["body"].splitlines() if line.startswith("http"))
    return parse_qs(urlsplit(url).fragment)["token"][0]


def test_known_unknown_inactive_have_same_response_and_private_delivery(
    client, db, make_user, recovery, caplog
):
    user = make_user(email="recovery@example.com")
    make_user(email="inactive@example.com", is_active=False)
    with caplog.at_level(logging.INFO):
        responses = [
            client.post(REQUEST, json={"email": email})
            for email in (
                " RECOVERY@example.com ",
                "unknown@example.com",
                "inactive@example.com",
            )
        ]
    assert [r.status_code for r in responses] == [202] * 3
    assert all(
        r.json() == GENERIC and r.headers["cache-control"] == "no-store"
        for r in responses
    )
    files = list(recovery.iterdir())
    assert len(files) == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    assert recovery.stat().st_mode & 0o777 == 0o700
    token = read_token(recovery)
    saved = db.scalar(select(models.PasswordResetToken))
    assert saved.user_id == user.id
    assert saved.token_hash == sha256(token.encode()).hexdigest()
    assert token not in saved.token_hash
    assert token not in caplog.text and user.email not in caplog.text
    assert "recovery" not in files[0].name


def test_request_throttles_delivery_but_keeps_generic_202(client, make_user, recovery):
    make_user(email="recovery@example.com")
    for _ in range(5):
        response = client.post(REQUEST, json={"email": "recovery@example.com"})
        assert response.status_code == 202 and response.json() == GENERIC
    assert len(list(recovery.iterdir())) == 3


def test_outbox_failure_still_generic_without_secrets(
    client, make_user, recovery, monkeypatch, caplog
):
    from app.core.email import OutboxEmailSender

    make_user(email="recovery@example.com")

    def fail(*_args, **_kwargs):
        raise OSError("SECRET-TOKEN recipient@example.com")

    monkeypatch.setattr(OutboxEmailSender, "send", fail)
    with caplog.at_level(logging.ERROR):
        response = client.post(REQUEST, json={"email": "recovery@example.com"})
    assert response.status_code == 202 and response.json() == GENERIC
    assert (
        "SECRET-TOKEN" not in caplog.text and "recipient@example.com" not in caplog.text
    )


@pytest.mark.parametrize(
    "body",
    [
        {"email": "bad", "new_password": "PRIVATE-PASSWORD", "token": "PRIVATE-TOKEN"},
        {"token": "PRIVATE-TOKEN", "new_password": "short"},
        {"token": "PRIVATE-TOKEN", "new_password": "ñ" * 37},
        {
            "token": "PRIVATE-TOKEN",
            "new_password": "ValidPass2026!",
            "extra": "PRIVATE-PASSWORD",
        },
    ],
)
def test_validation_never_echoes_tokens_or_passwords(client, body):
    response = client.post(REQUEST if "email" in body else CONFIRM, json=body)
    assert response.status_code == 422
    assert "PRIVATE" not in response.text and "ñ" not in response.text


def test_malformed_json_is_sanitized(client):
    response = client.post(
        CONFIRM,
        content='{"new_password":"PRIVATE-PASSWORD",',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422 and "PRIVATE" not in response.text


def test_request_does_not_trust_host_for_link(client, make_user, recovery):
    make_user(email="recovery@example.com")
    client.post(
        REQUEST,
        json={"email": "recovery@example.com"},
        headers={"Host": "evil.example"},
    )
    text = next(recovery.iterdir()).read_text()
    assert "http://localhost:5173/nueva-contrasena#token=" in text
    assert "evil.example" not in text


def issue_link(client, user, outbox):
    client.post(REQUEST, json={"email": user.email})
    return read_token(outbox)


def test_success_changes_password_invalidates_tokens_and_sessions(
    client, db, make_user, recovery
):
    import jwt
    from app.core.security import decode_access_token
    from app.services import auth_service

    user = make_user(email="recovery@example.com")
    sessions = [auth_service.issue_session(db, user) for _ in range(2)]
    payload = decode_access_token(sessions[0].access_token)
    payload.pop("ver")
    settings = get_settings()
    legacy = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    token = issue_link(client, user, recovery)
    client.post(REQUEST, json={"email": user.email})
    other_tokens = [
        parse_qs(
            urlsplit(
                next(
                    line
                    for line in json.loads(path.read_text())["body"].splitlines()
                    if line.startswith("http")
                )
            ).fragment
        )["token"][0]
        for path in recovery.iterdir()
    ]
    response = client.post(
        CONFIRM, json={"token": token, "new_password": "NewPassword2026!"}
    )
    assert response.status_code == 204 and response.content == b""
    assert response.headers["cache-control"] == "no-store"
    db.refresh(user)
    assert user.session_version == 1 and user.updated_at is not None
    assert user.updated_by_id == user.id
    for item in other_tokens:
        assert (
            client.post(
                CONFIRM, json={"token": item, "new_password": "OtherPassword2026!"}
            ).status_code
            == 400
        )
    for old in sessions:
        assert (
            client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {old.access_token}"},
            ).status_code
            == 401
        )
        client.cookies.set("brava.refresh", old.refresh_token, path="/api/v1/auth")
        assert (
            client.post(
                "/api/v1/auth/refresh", headers={"X-Brava-CSRF": "1"}
            ).status_code
            == 401
        )
    assert (
        client.get(
            "/api/v1/users/me", headers={"Authorization": f"Bearer {legacy}"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "Secret123!"},
        ).status_code
        == 401
    )
    current = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "NewPassword2026!"},
    )
    assert current.status_code == 200
    assert (
        client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {current.json()['access_token']}"},
        ).status_code
        == 200
    )


@pytest.mark.parametrize("elapsed, expected", [(1799, 204), (1800, 400), (1801, 400)])
def test_reset_expires_at_exactly_thirty_minutes(
    client, make_user, recovery, elapsed, expected
):
    from datetime import timedelta

    with freeze_time("2026-10-16 10:00:00") as clock:
        token = issue_link(client, make_user(email="recovery@example.com"), recovery)
        clock.tick(timedelta(seconds=elapsed))
        response = client.post(
            CONFIRM, json={"token": token, "new_password": "NewPassword2026!"}
        )
    assert response.status_code == expected


def test_invalid_inputs_do_not_consume_valid_token(client, make_user, recovery):
    token = issue_link(client, make_user(email="recovery@example.com"), recovery)
    assert (
        client.post(
            CONFIRM, json={"token": token, "new_password": "ñ" * 37}
        ).status_code
        == 422
    )
    assert (
        client.post(
            CONFIRM, json={"token": token, "new_password": "ñ" * 36}
        ).status_code
        == 204
    )


def test_inactive_or_manipulated_link_has_same_400(client, db, make_user, recovery):
    user = make_user(email="recovery@example.com")
    token = issue_link(client, user, recovery)
    user.is_active = False
    db.commit()
    results = [
        client.post(CONFIRM, json={"token": value, "new_password": "NewPassword2026!"})
        for value in (token, token + "x", "unknown")
    ]
    assert [r.status_code for r in results] == [400] * 3
    assert len({r.text for r in results}) == 1
