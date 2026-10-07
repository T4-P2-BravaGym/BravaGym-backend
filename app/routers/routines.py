"""Controller for routines: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-17, HU-18): POST/GET/PATCH/DELETE /routines, /routines/{id}/exercises, GET /routines/me
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
from app.schemas.routine import RoutineOut
from app.services import routine_service

router = APIRouter(prefix="/routines", tags=["routines"])


@router.get(
    "/me",
    response_model=RoutineOut,
    summary="Get my active routine with its exercises grouped by day",
    responses={404: {"description": "The member has no active routine"}},
)
def get_my_routine(
        member: Annotated[User, Depends(require_roles(RoleName.MEMBER))],
        db: Annotated[Session, Depends(get_db)],
) -> RoutineOut:
    return routine_service.my_routine(db, member)
