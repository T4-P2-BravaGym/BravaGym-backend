"""Public trainer list and each trainer's own profile (HU-15)."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role, TrainerProfile, User
from app.models.enums import RoleName
from app.schemas.user import TrainerOut, TrainerProfileUpdate

logger = logging.getLogger(__name__)


def _to_trainer_out(trainer: User) -> TrainerOut:
    profile = trainer.trainer_profile
    return TrainerOut(
        id=trainer.id,
        name=f"{trainer.first_name} {trainer.last_name}",
        specialty=profile.specialty if profile else None,
        bio=profile.bio if profile else None,
    )


def list_trainers(db: Session) -> list[TrainerOut]:
    """Active trainers ordered by first name, with their public profile."""
    trainers = db.scalars(
        select(User)
        .join(User.role)
        .where(Role.name == RoleName.TRAINER, User.is_active.is_(True))
        .order_by(User.first_name)
    ).all()

    return [_to_trainer_out(trainer) for trainer in trainers]


def update_my_profile(db: Session, trainer: User, changes: TrainerProfileUpdate) -> TrainerOut:
    """Change only the fields the trainer sent. Creates the profile if she has none yet."""
    if trainer.trainer_profile is None:
        trainer.trainer_profile = TrainerProfile()
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(trainer.trainer_profile, field, value)
    db.commit()
    logger.info("Trainer %s updated her public profile", trainer.id)
    return _to_trainer_out(trainer)
