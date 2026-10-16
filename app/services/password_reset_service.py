"""Password recovery rules; session and transport are supplied by the caller."""

import logging
import secrets
from datetime import timedelta
from hashlib import sha256
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.email import EmailSender
from app.models import PasswordResetToken
from app.models.types import utc_now
from app.services.auth_service import get_user_by_email

logger = logging.getLogger(__name__)
ACCEPTED_DETAIL = "Si existe una cuenta activa con ese email, recibirás un enlace para recuperar tu contraseña."
INVALID_RESET = "El enlace no es válido o ha caducado. Solicita uno nuevo."


def request_password_reset(
    db: Session, email: str, sender: EmailSender, frontend_url: str
) -> None:
    token = secrets.token_urlsafe(32)
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=sha256(token.encode()).hexdigest(),
            expires_at=utc_now() + timedelta(minutes=30),
        )
    )
    db.commit()
    link = f"{frontend_url.rstrip('/')}/nueva-contrasena#token={quote(token, safe='')}"
    sender.send(
        recipient=user.email,
        subject="Recupera tu contraseña de Brava",
        body=f"Para elegir una nueva contraseña, abre este enlace. Caduca en 30 minutos y solo puede usarse una vez.\n\n{link}\n\nSi no lo has solicitado, puedes ignorar este mensaje.",
    )
    logger.info("Password recovery delivery processed for user %s", user.id)


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    """Consume, reset and invalidate every old session in one transaction."""
    from sqlalchemy import select, update

    from app.core.exceptions import AppError
    from app.core.security import hash_password
    from app.models import RefreshToken, User

    digest = sha256(token.encode()).hexdigest()
    now = utc_now()
    try:
        # Hash only after a plausible valid token; compute before taking the write lock.
        candidate = db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == digest,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
                PasswordResetToken.user_id.in_(
                    select(User.id).where(User.is_active.is_(True))
                ),
            )
        )
        if candidate is None:
            raise AppError(INVALID_RESET)
        password_hash = hash_password(new_password)
        # Recheck expiry after bcrypt, including a token expiring during hashing.
        now = utc_now()
        owner = db.scalar(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.token_hash == digest,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
                PasswordResetToken.user_id.in_(
                    select(User.id).where(User.is_active.is_(True))
                ),
            )
            .values(used_at=now)
            .returning(PasswordResetToken.user_id)
        )
        if owner is None:
            raise AppError(INVALID_RESET)
        changed = db.execute(
            update(User)
            .where(User.id == owner, User.is_active.is_(True))
            .values(
                password_hash=password_hash,
                session_version=User.session_version + 1,
                updated_at=now,
                updated_by_id=owner,
            )
        )
        if changed.rowcount != 1:
            raise AppError(INVALID_RESET)
        db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == owner,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == owner, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Password recovered and old sessions invalidated for user %s", owner)
