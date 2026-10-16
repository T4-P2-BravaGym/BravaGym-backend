import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache

import jwt
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token_for_logout,
    decode_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models import RefreshToken, RevokedToken, Role, User
from app.models.enums import RoleName
from app.models.types import utc_now
from app.schemas.auth import UserCreate

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Email o contraseña incorrectos."
INVALID_SESSION_TOKEN = "Sesión no válida o caducada. Vuelve a iniciar sesión."


@dataclass(frozen=True)
class SessionTokens:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)


def _token_expiry(payload: dict) -> datetime:
    return datetime.fromtimestamp(payload["exp"], UTC).replace(tzinfo=None)


def _new_session_tokens(db: Session, user: User) -> SessionTokens:
    refresh = create_refresh_token(user.id, user.role.name)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=_token_expiry(decode_refresh_token(refresh)),
        )
    )
    return SessionTokens(create_access_token(user.id, user.role.name), refresh)


def issue_session(db: Session, user: User) -> SessionTokens:
    """Issue a session and store only the refresh hash."""
    if not user.is_active:
        raise UnauthorizedError(INVALID_SESSION_TOKEN)
    tokens = _new_session_tokens(db, user)
    _delete_expired_revocations(db)
    db.commit()
    logger.info("Session issued for user %s", user.id)
    return tokens


def refresh_session(db: Session, refresh_token: str) -> SessionTokens:
    """Consume the old refresh once and save its replacement atomically."""
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise UnauthorizedError(INVALID_SESSION_TOKEN) from None
    user = db.get(User, user_id, populate_existing=True)
    if user is None or not user.is_active:
        raise UnauthorizedError(INVALID_SESSION_TOKEN)
    now = utc_now()
    consumed = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
            RefreshToken.user_id.in_(select(User.id).where(User.is_active.is_(True))),
        )
        .values(revoked_at=now)
        .execution_options(synchronize_session="fetch")
    )
    if consumed.rowcount != 1:
        db.rollback()
        raise UnauthorizedError(INVALID_SESSION_TOKEN)
    try:
        tokens = _new_session_tokens(db, user)
        _delete_expired_revocations(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Session refreshed for user %s", user.id)
    return tokens


def logout_session(db: Session, access_token: str, refresh_token: str) -> None:
    """Revoke a refresh and the current access; never revoke another user's token."""
    try:
        access = decode_access_token_for_logout(access_token)
        refresh = decode_refresh_token(refresh_token)
        user_id = int(access["sub"])
        if user_id != int(refresh["sub"]):
            raise ValueError("Token owners differ")
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise UnauthorizedError(INVALID_SESSION_TOKEN) from None
    saved = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(refresh_token),
            RefreshToken.user_id == user_id,
        )
    )
    user = db.get(User, user_id, populate_existing=True)
    if (
        saved is None
        or saved.expires_at <= utc_now()
        or user is None
        or not user.is_active
    ):
        raise UnauthorizedError(INVALID_SESSION_TOKEN)
    if saved.revoked_at is None:
        saved.revoked_at = utc_now()
    # The database handles duplicate logout atomically, including concurrent calls.
    if _token_expiry(access) > utc_now():
        db.execute(
            sqlite_insert(RevokedToken)
            .values(jti=access["jti"], expires_at=_token_expiry(access))
            .on_conflict_do_nothing(index_elements=["jti"])
        )
    _delete_expired_revocations(db)
    db.commit()
    logger.info("Session logged out for user %s", user_id)


def _delete_expired_revocations(db: Session) -> int:
    result = db.execute(
        delete(RevokedToken).where(RevokedToken.expires_at <= utc_now())
    )
    if result.rowcount:
        logger.info("Expired access revocations removed: %s", result.rowcount)
    return result.rowcount


def cleanup_expired_tokens(db: Session) -> int:
    """Remove access revocations only after the corresponding JWT has expired."""
    count = _delete_expired_revocations(db)
    db.commit()
    return count


@cache
def _dummy_password_hash() -> str:
    return hash_password("not-a-real-password")


def normalize_email(email: str) -> str:
    """One place for the rule, so register and login always compare the same way."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register(db: Session, data: UserCreate) -> User:
    """Create an active member. 409 if the email already exists."""
    if get_user_by_email(db, data.email) is not None:
        raise ConflictError("Ya existe una cuenta con ese email.")

    member_role = db.scalar(select(Role).where(Role.name == RoleName.MEMBER))
    if member_role is None:
        raise RuntimeError("Role 'member' not found. Run scripts/seed.py first.")

    user = User(
        email=normalize_email(data.email),
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=member_role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Ya existe una cuenta con ese email.") from None

    logger.info("Member registered: user_id=%s", user.id)
    return user


def login(db: Session, email: str, password: str) -> SessionTokens:
    user = get_user_by_email(db, email)

    password_hash = user.password_hash if user else _dummy_password_hash()
    password_ok = verify_password(password, password_hash)

    if user is None or not password_ok or not user.is_active:
        logger.info("Failed login attempt")
        raise UnauthorizedError(INVALID_CREDENTIALS)

    logger.info("User %s logged in", user.id)
    return issue_session(db, user)
