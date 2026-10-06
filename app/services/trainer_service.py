"""Public trainer list and each trainer's own profile (HU-15)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role, User
from app.models.enums import RoleName
from app.schemas.user import TrainerOut


def list_trainers(db: Session) -> list[TrainerOut]:
    """Active trainers ordered by first name, with their public profile."""
    trainers = db.scalars(
        select(User)
        .join(User.role)
        .where(Role.name == RoleName.TRAINER, User.is_active.is_(True))
        .order_by(User.first_name)
    ).all()

    return [
        TrainerOut(
            id=trainer.id,
            name=f"{trainer.first_name} {trainer.last_name}",
            specialty=trainer.trainer_profile.specialty if trainer.trainer_profile else None,
            bio=trainer.trainer_profile.bio if trainer.trainer_profile else None,
        )
        for trainer in trainers
    ]
