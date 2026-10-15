"""Profile, password, user list, role changes and admin user management (HU-04, HU-05, HU-06, HU-31, HU-32).
Every change records who made it and when (T-03).

Business rules RN-18, RN-19: docs/business-rules.md.
"""

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.rate_limit import password_change_limiter, password_change_rate_key
from app.core.security import hash_password, verify_password
from app.models import Role, TrainerProfile, User
from app.models.enums import RoleName, SubscriptionStatus
from app.models.types import utc_now
from app.schemas.auth import PasswordChange
from app.schemas.user import UserUpdate
from app.services import booking_service
from app.services.auth_service import get_user_by_email, normalize_email
from app.services.subscription_service import get_active_subscription

logger = logging.getLogger(__name__)

EMAIL_TAKEN = "Ya existe una cuenta con ese email."
WRONG_PASSWORD = "La contraseña actual no es correcta."


def _mark_updated(user: User, actor: User) -> None:
    """T-03: who changed this account last, and when. Call it right before the commit."""
    user.updated_at = utc_now()
    user.updated_by_id = actor.id


def update_me(db: Session, user: User, changes: UserUpdate) -> User:
    """Change only the fields the user sent. 409 if the new email belongs to someone else."""
    _apply_profile_changes(db, user, changes, actor=user)
    logger.info("User %s updated her profile", user.id)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    """HU-32: 400 if the current password is wrong (not 401: the front logs out on a 401).
    After 5 wrong tries in 15 minutes, 429 like the login (HU-34)."""
    key = password_change_rate_key(user.id)
    password_change_limiter.assert_allowed(key)
    if not verify_password(data.current_password, user.password_hash):
        password_change_limiter.record(key)
        logger.info("User %s failed to change her password", user.id)
        raise AppError(WRONG_PASSWORD)  # the base AppError is a 400

    user.password_hash = hash_password(data.new_password)
    _mark_updated(user, user)
    db.commit()
    password_change_limiter.reset(key)
    logger.info("User %s changed her password", user.id)


def _apply_profile_changes(
    db: Session, user: User, changes: UserUpdate, *, actor: User
) -> None:
    """Shared by update_me (HU-04) and update_user (HU-31): only the fields sent, email checked."""
    data = changes.model_dump(exclude_unset=True)
    if not data:
        return  # nothing sent, nothing changed (T-03: not a modification)
    if "email" in data:
        data["email"] = normalize_email(data["email"])
        owner = get_user_by_email(db, data["email"])
        if owner is not None and owner.id != user.id:
            raise ConflictError(EMAIL_TAKEN)

    for field, value in data.items():
        setattr(user, field, value)
    _mark_updated(user, actor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(EMAIL_TAKEN) from None


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


def list_active_members(db: Session) -> list[User]:
    """Active members ordered by name, for the trainer's routine editor."""
    stmt = (
        select(User)
        .where(User.is_active.is_(True), User.role.has(Role.name == RoleName.MEMBER))
        .order_by(User.first_name, User.last_name, User.id)
    )
    return list(db.scalars(stmt).all())


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
    if actor.role.name != RoleName.SUPERADMIN and (
        old_role in STAFF_ROLES or new_role in STAFF_ROLES
    ):
        raise PermissionDeniedError(
            "Solo la superadmin puede dar o quitar los roles de administración."
        )
    # RN-19: there is always at least one superadmin
    if (
        old_role == RoleName.SUPERADMIN
        and new_role != RoleName.SUPERADMIN
        and _count_superadmins(db) == 1
    ):
        raise ConflictError("Tiene que quedar al menos una superadmin.")

    role = db.scalar(select(Role).where(Role.name == new_role))
    if role is None:
        raise RuntimeError(f"Role '{new_role}' not found. Run scripts/seed.py first.")
    user.role = role
    if new_role == RoleName.TRAINER and user.trainer_profile is None:
        user.trainer_profile = TrainerProfile()
    _mark_updated(user, actor)
    db.commit()
    logger.info(
        "User %s changed the role of user %s from %s to %s",
        actor.id,
        user.id,
        old_role,
        new_role,
    )
    return user


def _count_superadmins(db: Session) -> int:
    return db.scalar(
        select(func.count(User.id))
        .join(User.role)
        .where(Role.name == RoleName.SUPERADMIN)
    )


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("No existe ese usuario.")
    return user


def _check_can_manage(actor: User, user: User) -> None:
    """RN-18 for edits and deactivations: only the superadmin touches admin and superadmin accounts."""
    if actor.role.name != RoleName.SUPERADMIN and user.role.name in STAFF_ROLES:
        raise PermissionDeniedError(
            "Solo la superadmin puede editar o dar de baja a otras administradoras."
        )


def update_user(db: Session, actor: User, user_id: int, changes: UserUpdate) -> User:
    """An admin edits another user's name, phone or email (HU-31)."""
    user = get_user(db, user_id)
    _check_can_manage(actor, user)
    _apply_profile_changes(db, user, changes, actor=actor)
    logger.info("User %s updated the profile of user %s", actor.id, user.id)
    return user


def deactivate_user(db: Session, actor: User, user_id: int) -> None:
    """Soft delete (HU-31): same chain as an approved cancellation (HU-20).

    The active subscription is cancelled, future bookings are cancelled (waitlists move up)
    and the user can no longer log in. The row is never deleted.
    """
    user = get_user(db, user_id)
    if user.id == actor.id:
        raise ConflictError("No puedes darte de baja a ti misma.")
    _check_can_manage(actor, user)
    if user.role.name == RoleName.SUPERADMIN and _count_superadmins(db) == 1:
        raise ConflictError("Tiene que quedar al menos una superadmin.")
    if not user.is_active:
        return

    now = utc_now()
    subscription = get_active_subscription(db, user.id)
    if subscription is not None:
        subscription.status = SubscriptionStatus.CANCELLED
    user.is_active = False
    user.deactivated_at = now
    _mark_updated(user, actor)
    affected_sessions = booking_service.cancel_future_bookings_for_user(
        db, user_id=user.id, now=now
    )
    db.commit()

    booking_service.notify_sessions_updated(affected_sessions)
    logger.info(
        "User %s deactivated user %s (%s sessions updated)",
        actor.id,
        user.id,
        len(affected_sessions),
    )
