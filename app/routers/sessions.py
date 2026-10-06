"""Controller for sessions: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-11, HU-12): POST/PATCH /sessions, POST /sessions/{id}/cancel, GET/POST /sessions/{id}/bookings
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.classes import SessionClassTypeOut, SessionOut, SessionPage
from app.services import session_service
from app.services.session_service import SessionWithFreeSpots

router = APIRouter(prefix="/sessions", tags=["sessions"])

DbSession = Annotated[Session, Depends(get_db)]


def _to_session_out(row: SessionWithFreeSpots) -> SessionOut:
    session = row.session
    return SessionOut(
        id=session.id,
        trainer_id=session.trainer_id,
        starts_at=session.starts_at,
        duration_minutes=session.duration_minutes,
        capacity=session.capacity,
        status=session.status,
        free_spots=row.free_spots,
        class_type=SessionClassTypeOut.model_validate(session.class_type),
    )


@router.get(
    "",
    response_model=SessionPage,
    summary="List class sessions with free spots",
    description=(
        "Public schedule of scheduled sessions. Free spots are computed as "
        "capacity minus confirmed bookings (never stored). Use only_available=true "
        "to hide full sessions. Extra price comes from the class type when present."
    ),
    responses={
        422: {"description": "Invalid date range (from after to) or query parameters"},
    },
)
def list_sessions(
    db: DbSession,
    from_: Annotated[
        datetime | None,
        Query(alias="from", description="Inclusive start of the starts_at range (UTC)"),
    ] = None,
    to: Annotated[
        datetime | None,
        Query(description="Inclusive end of the starts_at range (UTC)"),
    ] = None,
    class_type_id: Annotated[int | None, Query(ge=1)] = None,
    trainer_id: Annotated[int | None, Query(ge=1)] = None,
    only_available: Annotated[
        bool,
        Query(description="If true, exclude sessions with no free spots"),
    ] = False,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SessionPage:
    rows, total = session_service.list_sessions(
        db,
        from_=from_,
        to=to,
        class_type_id=class_type_id,
        trainer_id=trainer_id,
        only_available=only_available,
        page=page,
        size=size,
    )
    return SessionPage(
        items=[_to_session_out(row) for row in rows],
        total=total,
        page=page,
        size=size,
    )
