from datetime import UTC, datetime

import jwt
import pytest
from app.core import security
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from freezegun import freeze_time


def test_token_has_sub_role_and_expires_in_60_minutes():
    with freeze_time("2026-10-06 10:00:00"):
        payload = decode_access_token(create_access_token(user_id=7, role="trainer"))

    assert payload["sub"] == "7"
    assert payload["role"] == "trainer"
    assert payload["exp"] == datetime(2026, 10, 6, 11, 0, tzinfo=UTC).timestamp()


def test_payload_only_has_the_allowed_claims():
    payload = decode_access_token(create_access_token(user_id=7, role="member"))

    assert set(payload) == {"sub", "role", "exp", "iss", "aud", "jti", "type"}
    assert payload["type"] == "access"


def test_each_access_token_has_a_different_identifier():
    with freeze_time("2026-10-06 10:00:00"):
        first = decode_access_token(create_access_token(7, "member"))
        second = decode_access_token(create_access_token(7, "member"))
    assert first["jti"] != second["jti"]


def test_refresh_token_has_seven_day_expiry_and_refresh_type():
    assert hasattr(security, "create_refresh_token")
    with freeze_time("2026-10-06 10:00:00"):
        payload = security.decode_refresh_token(
            security.create_refresh_token(7, "member")
        )
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    assert payload["jti"]
    assert payload["exp"] == datetime(2026, 10, 13, 10, 0, tzinfo=UTC).timestamp()


def test_refresh_token_is_rejected_as_an_access_token():
    token = security.create_refresh_token(7, "member")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


def test_access_token_is_rejected_as_a_refresh_token():
    token = create_access_token(7, "member")
    with pytest.raises(jwt.InvalidTokenError):
        security.decode_refresh_token(token)


def test_refresh_token_expires_at_its_exact_expiry():
    with freeze_time("2026-10-06 10:00:00"):
        token = security.create_refresh_token(7, "member")
    with freeze_time("2026-10-13 09:59:59"):
        assert security.decode_refresh_token(token)["sub"] == "7"
    with freeze_time("2026-10-13 10:00:00"), pytest.raises(jwt.ExpiredSignatureError):
        security.decode_refresh_token(token)


@pytest.mark.parametrize("missing", ["jti", "type"])
def test_access_token_without_required_session_claim_is_rejected(missing):
    settings = get_settings()
    payload = decode_access_token(create_access_token(7, "member"))
    payload.pop(missing)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(jwt.MissingRequiredClaimError):
        decode_access_token(token)


def test_refresh_expiry_is_configurable(monkeypatch):
    monkeypatch.setattr(get_settings(), "refresh_token_expire_days", 2)
    with freeze_time("2026-10-06 10:00:00"):
        payload = security.decode_refresh_token(
            security.create_refresh_token(7, "member")
        )
    assert payload["exp"] == datetime(2026, 10, 8, 10, 0, tzinfo=UTC).timestamp()


def test_refresh_token_hash_is_stable_and_not_the_token():
    token = security.create_refresh_token(7, "member")
    hashed = security.hash_refresh_token(token)
    assert hashed != token
    assert len(hashed) == 64
    assert security.hash_refresh_token(token) == hashed


def test_token_is_valid_at_59_minutes_and_expired_at_61():
    with freeze_time("2026-10-06 10:00:00"):
        token = create_access_token(user_id=7, role="member")

    with freeze_time("2026-10-06 10:59:00"):
        assert decode_access_token(token)["sub"] == "7"

    with freeze_time("2026-10-06 11:01:00"), pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_token_signed_with_another_key_is_rejected():
    settings = get_settings()
    forged = jwt.encode(
        {
            "sub": "1",
            "role": "superadmin",
            "exp": 9999999999,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        },
        "another-secret-key-that-is-long-enough",
        algorithm="HS256",
    )

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(forged)


def test_token_for_another_audience_is_rejected():
    settings = get_settings()
    other_app_token = jwt.encode(
        {
            "sub": "1",
            "role": "member",
            "exp": 9999999999,
            "iss": settings.jwt_issuer,
            "aud": "another-app",
            "jti": "test-audience-token",
            "type": "access",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(other_app_token)


def test_hash_is_not_the_plain_password():
    assert hash_password("BravaDemo2026!") != "BravaDemo2026!"


def test_hash_uses_bcrypt():
    assert hash_password("BravaDemo2026!").startswith("$2b$12$")


def test_same_password_gives_different_hashes():
    assert hash_password("BravaDemo2026!") != hash_password("BravaDemo2026!")


def test_verify_password_accepts_the_right_one():
    assert verify_password("BravaDemo2026!", hash_password("BravaDemo2026!"))


def test_verify_password_rejects_a_wrong_one():
    assert not verify_password("otra-cosa", hash_password("BravaDemo2026!"))


def test_verify_password_with_a_broken_hash_returns_false():
    assert not verify_password("BravaDemo2026!", "not-a-hash")
