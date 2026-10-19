from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import uuid4

import bcrypt
import jwt

from app.core.config import get_settings

BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


def create_access_token(user_id: int, role: str, session_version: int = 0) -> str:
    lifetime = timedelta(minutes=get_settings().access_token_expire_minutes)
    return _create_token(user_id, role, "access", lifetime, session_version)


def create_refresh_token(user_id: int, role: str, session_version: int = 0) -> str:
    lifetime = timedelta(days=get_settings().refresh_token_expire_days)
    return _create_token(user_id, role, "refresh", lifetime, session_version)


def _create_token(
    user_id: int, role: str, token_type: str, lifetime: timedelta, session_version: int
) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "role": str(role),
        "exp": datetime.now(UTC) + lifetime,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "jti": uuid4().hex,
        "type": token_type,
        "ver": session_version,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "access")


def decode_refresh_token(token: str) -> dict[str, Any]:
    return _decode_token(token, "refresh")


def decode_access_token_for_logout(token: str) -> dict[str, Any]:
    """Check access identity for logout, which also requires its owner's refresh."""
    return _decode_token(token, "access", verify_exp=False)


def _decode_token(
    token: str, expected_type: str, *, verify_exp: bool = True
) -> dict[str, Any]:
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={
            "require": ["sub", "role", "exp", "iss", "aud", "jti", "type"],
            "verify_exp": verify_exp,
        },
    )
    version = payload.get("ver", 0)
    if type(version) is not int or version < 0:
        raise jwt.InvalidTokenError("Invalid session version")
    if payload["type"] != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    if not isinstance(payload["jti"], str) or not 1 <= len(payload["jti"]) <= 64:
        raise jwt.InvalidTokenError("Invalid token identifier")
    try:
        datetime.fromtimestamp(payload["exp"], UTC)
    except (ValueError, TypeError, OverflowError, OSError):
        raise jwt.InvalidTokenError("Invalid token expiry") from None
    return payload


def hash_refresh_token(token: str) -> str:
    """Hash a high-entropy refresh token for lookup without storing its value."""
    return sha256(token.encode("utf-8")).hexdigest()
