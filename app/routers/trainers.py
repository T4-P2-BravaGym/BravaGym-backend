"""Controller for trainers: receives the request, checks permissions, calls the service, returns a schema.
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.user import TrainerOut, TrainerProfileUpdate
from app.services import trainer_service

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get(
    "",
    response_model=list[TrainerOut],
    summary="List active trainers with their public profile",
)
def list_trainers(db: Annotated[Session, Depends(get_db)]) -> list[TrainerOut]:
    return trainer_service.list_trainers(db)


@router.patch(
    "/me/profile",
    response_model=TrainerOut,
    summary="Update my public trainer profile (specialty and bio)",
    responses={401: {"description": "Not logged in"}, 403: {"description": "Not a trainer"}},
)
def update_my_profile(
        changes: TrainerProfileUpdate,
        trainer: Annotated[User, Depends(require_roles(RoleName.TRAINER))],
        db: Annotated[Session, Depends(get_db)],
) -> TrainerOut:
    return trainer_service.update_my_profile(db, trainer, changes)
