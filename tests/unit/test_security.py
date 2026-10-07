from datetime import UTC, datetime

import jwt
import pytest
from freezegun import freeze_time

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_token_has_sub_role_and_expires_in_60_minutes():
    with freeze_time("2026-10-06 10:00:00"):
        payload = decode_access_token(create_access_token(user_id=7, role="trainer"))

    assert payload["sub"] == "7"
    assert payload["role"] == "trainer"
    assert payload["exp"] == datetime(2026, 10, 6, 11, 0, tzinfo=UTC).timestamp()


def test_payload_only_has_the_allowed_claims():
    payload = decode_access_token(create_access_token(user_id=7, role="member"))

    assert set(payload) == {"sub", "role", "exp", "iss", "aud"}


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
