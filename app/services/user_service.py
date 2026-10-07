"""Profile, user list with filters and role changes (RN-18, RN-19).

TODO(HU-04, HU-05, HU-06). Business rules RN-xx: docs/business-rules.md.
"""
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models import User
from app.schemas.user import UserUpdate
from app.services.auth_service import get_user_by_email, normalize_email

logger = logging.getLogger(__name__)

EMAIL_TAKEN = "Ya existe una cuenta con ese email."


def update_me(db: Session, user: User, changes: UserUpdate) -> User:
    """Change only the fields the user sent. 409 if the new email belongs to someone else."""
    data = changes.model_dump(exclude_unset=True)
    if "email" in data:
        data["email"] = normalize_email(data["email"])
        owner = get_user_by_email(db, data["email"])
        if owner is not None and owner.id != user.id:
            raise ConflictError(EMAIL_TAKEN)

    for field, value in data.items():
        setattr(user, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(EMAIL_TAKEN) from None

    logger.info("User %s updated her profile", user.id)
    return user