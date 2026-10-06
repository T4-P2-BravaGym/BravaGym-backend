import logging
from functools import cache

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Email o contraseña incorrectos."


@cache
def _dummy_password_hash() -> str:
    return hash_password("not-a-real-password")


def login(db: Session, email: str, password: str) -> str:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))

    password_hash = user.password_hash if user else _dummy_password_hash()
    password_ok = verify_password(password, password_hash)

    if user is None or not password_ok or not user.is_active:
        logger.info("Failed login attempt")
        raise UnauthorizedError(INVALID_CREDENTIALS)

    logger.info("User %s logged in", user.id)
    return create_access_token(user.id, user.role.name)