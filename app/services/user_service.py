"""Profile, user list with filters and role changes (HU-04, HU-05, HU-06).

Business rules RN-18, RN-19: docs/business-rules.md.
"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Role, TrainerProfile, User
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


STAFF_ROLES = {RoleName.ADMIN, RoleName.SUPERADMIN}


def change_role(db: Session, actor: User, user_id: int, new_role: RoleName) -> User:
    """Change another user's role following RN-18 and RN-19."""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("No existe ese usuario.")

    old_role = user.role.name
    # RN-19: nobody changes her own role
    if user.id == actor.id:
        raise ConflictError("No puedes cambiar tu propio rol.")
    # RN-18: only the superadmin gives or removes admin and superadmin
    if actor.role.name != RoleName.SUPERADMIN and (old_role in STAFF_ROLES or new_role in STAFF_ROLES):
        raise PermissionDeniedError("Solo la superadmin puede dar o quitar los roles de administración.")
    # RN-19: there is always at least one superadmin
    if old_role == RoleName.SUPERADMIN and new_role != RoleName.SUPERADMIN and _count_superadmins(db) == 1:
        raise ConflictError("Tiene que quedar al menos una superadmin.")

    role = db.scalar(select(Role).where(Role.name == new_role))
    if role is None:
        raise RuntimeError(f"Role '{new_role}' not found. Run scripts/seed.py first.")
    user.role = role
    if new_role == RoleName.TRAINER and user.trainer_profile is None:
        user.trainer_profile = TrainerProfile()
    db.commit()
    logger.info("User %s changed the role of user %s from %s to %s", actor.id, user.id, old_role, new_role)
    return user


def _count_superadmins(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).join(User.role).where(Role.name == RoleName.SUPERADMIN))
