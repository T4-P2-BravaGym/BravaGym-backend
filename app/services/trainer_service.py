"""Public trainer list and each trainer's own profile (HU-15) and photo (T-291)."""

import logging
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.media import trainer_photo_url, trainer_photos_dir
from app.models import Role, TrainerProfile, User
from app.models.enums import RoleName
from app.schemas.user import TrainerOut, TrainerProfileUpdate
from app.services.image_files import delete_image, read_image, save_image

logger = logging.getLogger(__name__)


def _to_trainer_out(trainer: User) -> TrainerOut:
    profile = trainer.trainer_profile
    return TrainerOut(
        id=trainer.id,
        name=f"{trainer.first_name} {trainer.last_name}",
        specialty=profile.specialty if profile else None,
        bio=profile.bio if profile else None,
        photo_url=trainer_photo_url(profile.photo_path if profile else None),
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


def update_my_profile(
    db: Session, trainer: User, changes: TrainerProfileUpdate
) -> TrainerOut:
    """Change only the fields the trainer sent. Creates the profile if she has none yet."""
    if trainer.trainer_profile is None:
        trainer.trainer_profile = TrainerProfile()
    for field, value in changes.model_dump(exclude_unset=True).items():
        setattr(trainer.trainer_profile, field, value)
    db.commit()
    logger.info("Trainer %s updated her public profile", trainer.id)
    return _to_trainer_out(trainer)


def _my_profile(trainer: User) -> TrainerProfile:
    if trainer.trainer_profile is None:
        trainer.trainer_profile = TrainerProfile()
    return trainer.trainer_profile


def set_my_photo(db: Session, trainer: User, stream: BinaryIO) -> TrainerOut:
    """T-291: save the new photo, commit, then delete the old one (same order as HU-30)."""
    data, extension = read_image(stream)
    folder = trainer_photos_dir()
    new_name = save_image(folder, data, extension)

    profile = _my_profile(trainer)
    old_name = profile.photo_path
    profile.photo_path = new_name
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_image(folder, new_name)
        raise

    delete_image(folder, old_name)
    logger.info(
        "Trainer %s set her photo (%s, %s bytes)", trainer.id, extension, len(data)
    )
    return _to_trainer_out(trainer)


def remove_my_photo(db: Session, trainer: User) -> TrainerOut:
    """T-291: back to the initials. Without a photo it changes nothing."""
    profile = trainer.trainer_profile
    if profile is None or profile.photo_path is None:
        return _to_trainer_out(trainer)

    old_name = profile.photo_path
    profile.photo_path = None
    db.commit()
    delete_image(trainer_photos_dir(), old_name)
    logger.info("Trainer %s removed her photo", trainer.id)
    return _to_trainer_out(trainer)
