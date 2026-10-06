import logging
from functools import cache

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Role, User
from app.models.enums import RoleName
from app.schemas.auth import UserCreate

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Email o contraseña incorrectos."


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


def login(db: Session, email: str, password: str) -> str:
    user = get_user_by_email(db, email)

    password_hash = user.password_hash if user else _dummy_password_hash()
    password_ok = verify_password(password, password_hash)

    if user is None or not password_ok or not user.is_active:
        logger.info("Failed login attempt")
        raise UnauthorizedError(INVALID_CREDENTIALS)

    logger.info("User %s logged in", user.id)
    return create_access_token(user.id, user.role.name)
