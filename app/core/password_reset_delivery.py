"""Background infrastructure: owns the task session, never the request session."""

import logging
from hashlib import sha256

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.email import OutboxEmailSender, UnavailableEmailSender
from app.core.rate_limit import AttemptWindowLimiter
from app.services.auth_service import normalize_email
from app.services.password_reset_service import request_password_reset

logger = logging.getLogger(__name__)
reset_delivery_limiter = AttemptWindowLimiter(max_attempts=3, window_seconds=900)


def get_reset_session_factory():
    return SessionLocal


def get_reset_email_sender():
    settings = get_settings()
    if settings.environment != "local":
        return UnavailableEmailSender()
    return OutboxEmailSender(settings.outbox_dir)


def deliver_password_reset(email, session_factory, sender, frontend_url):
    key = sha256(normalize_email(email).encode()).hexdigest()
    if not reset_delivery_limiter.record_if_allowed(key):
        return
    try:
        with session_factory() as db:
            request_password_reset(db, email, sender, frontend_url)
    except Exception:  # noqa: BLE001 -- background failures must not reveal delivery details
        # Exceptions from transports may contain the token or recipient. Never log them.
        logger.error(
            "Password recovery delivery failed; check transport configuration and database"
        )
