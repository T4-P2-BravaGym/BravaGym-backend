"""Profile, user list with filters and role changes (RN-18, RN-19).

TODO(HU-05). role changes. Business rules RN-xx: docs/business-rules.md.
"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models import Role, User
from app.models.enums import RoleName
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


def list_users(
    db: Session,
    *,
    role: RoleName | None = None,
    is_active: bool | None = None,
    q: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[User], int]:
    """Users for administration, filtered and paginated. Returns (users of this page, total)."""
    conditions = []
    if role is not None:
# The role name lives in the roles table, so filter through the relationship
        conditions.append(User.role.has(Role.name == role))
    if is_active is not None:
        conditions.append(User.is_active == is_active)

    search = q.strip() if q else ""
    if search:
        conditions.append(
            or_(
                User.first_name.icontains(search, autoescape=True),
                User.last_name.icontains(search, autoescape=True),
                User.email.icontains(search, autoescape=True),
            )
        )

    total = db.scalar(select(func.count(User.id)).where(*conditions)) or 0

    stmt = (
        select(User)
        .where(*conditions)
# id breaks ties so pagination is stable
        .order_by(User.last_name, User.first_name, User.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt).all()), int(total)
