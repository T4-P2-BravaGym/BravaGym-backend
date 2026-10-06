"""Controller for trainers: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-15): GET /trainers, PATCH /trainers/me/profile
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user import TrainerOut
from app.services import trainer_service

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get(
    "",
    response_model=list[TrainerOut],
    summary="List active trainers with their public profile",
)
def list_trainers(db: Annotated[Session, Depends(get_db)]) -> list[TrainerOut]:
    return trainer_service.list_trainers(db)
