"""Controller for sessions: receives the request, checks permissions, calls the service.

HU-10: GET /sessions (public schedule).
HU-11: POST/PATCH /sessions, POST /sessions/{id}/cancel, GET /sessions/{id}/bookings.
HU-12: POST /sessions/{id}/bookings (member booking).
HU-14: POST /sessions/personal-training (trainer PT slots).
Keep endpoints thin: no business rules and no complex queries here.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember, require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.booking import BookingOut
from app.schemas.classes import (
    PersonalTrainingSlotCreate,
    SessionBookingOut,
    SessionBookingUserOut,
    SessionClassTypeOut,
    SessionCreate,
    SessionOut,
    SessionPage,
    SessionUpdate,
)
from app.services import booking_service, session_service
from app.services.session_service import SessionWithFreeSpots

router = APIRouter(prefix="/sessions", tags=["sessions"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentTrainer = Annotated[User, Depends(require_roles(RoleName.TRAINER))]
TrainerOrSuperadmin = Annotated[
    User, Depends(require_roles(RoleName.TRAINER, RoleName.SUPERADMIN))
]
TrainerAdminOrSuperadmin = Annotated[
    User,
    Depends(require_roles(RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN)),
]


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


@router.post(
    "/personal-training",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a personal-training slot",
    description=(
        "Trainer opens a 60-minute, capacity-1 personal-training session (RN-08). "
        "Overlapping sessions for the same trainer are rejected (RN-09)."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Only trainers can create personal-training slots"},
        404: {"description": "No active personal-training class type"},
        409: {"description": "Overlapping session for this trainer (RN-09)"},
        422: {"description": "class_type_id is not personal training"},
    },
)
def create_personal_training_slot(
    body: PersonalTrainingSlotCreate,
    trainer: CurrentTrainer,
    db: DbSession,
) -> SessionOut:
    row = session_service.create_personal_training_slot(
        db,
        trainer_id=trainer.id,
        starts_at=body.starts_at,
        class_type_id=body.class_type_id,
    )
    return _to_session_out(row)


@router.post(
    "",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a class session",
    description=(
        "Trainer creates a session for herself; superadmin must pass trainer_id. "
        "Overlapping sessions for the same trainer return 409 (RN-09)."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not a trainer or superadmin"},
        404: {"description": "Class type not found"},
        409: {"description": "Overlap with another session of the same trainer (RN-09)"},
        422: {"description": "Invalid body or missing trainer_id for superadmin"},
    },
)
def create_session(
    body: SessionCreate,
    actor: TrainerOrSuperadmin,
    db: DbSession,
) -> SessionOut:
    return _to_session_out(session_service.create_session(db, actor, body))


@router.patch(
    "/{session_id}",
    response_model=SessionOut,
    summary="Update a class session",
    description=(
        "Only the session trainer or superadmin may edit (RN-10). "
        "Overlaps with another of the trainer's sessions return 409 (RN-09)."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Not the session trainer (RN-10)"},
        404: {"description": "Session not found"},
        409: {
            "description": "Overlap (RN-09), cancelled session, or capacity below confirmed"
        },
    },
)
def update_session(
    session_id: int,
    body: SessionUpdate,
    actor: TrainerOrSuperadmin,
    db: DbSession,
) -> SessionOut:
    return _to_session_out(
        session_service.update_session(db, actor, session_id, body)
    )


@router.post(
    "/{session_id}/cancel",
    response_model=SessionOut,
    summary="Cancel a class session",
    description=(
        "Only the session trainer or superadmin may cancel (RN-10). "
        "Confirmed and waitlisted bookings become cancelled; related extra-class "
        "payments become refunded."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Not the session trainer (RN-10)"},
        404: {"description": "Session not found"},
        409: {"description": "Session already cancelled"},
    },
)
def cancel_session(
    session_id: int,
    actor: TrainerOrSuperadmin,
    db: DbSession,
) -> SessionOut:
    return _to_session_out(session_service.cancel_session(db, actor, session_id))


@router.get(
    "/{session_id}/bookings",
    response_model=list[SessionBookingOut],
    summary="List bookings for a session",
    description=(
        "Confirmed and waitlisted bookings for a session. "
        "Allowed for the session trainer, admin and superadmin."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Not allowed to view this session's bookings"},
        404: {"description": "Session not found"},
    },
)
def list_session_bookings(
    session_id: int,
    actor: TrainerAdminOrSuperadmin,
    db: DbSession,
) -> list[SessionBookingOut]:
    rows = session_service.list_session_bookings(db, actor, session_id)
    return [
        SessionBookingOut(
            id=booking.id,
            status=booking.status,
            waitlist_position=position,
            created_at=booking.created_at,
            cancelled_at=booking.cancelled_at,
            user=SessionBookingUserOut.model_validate(booking.user),
        )
        for booking, position in rows
    ]


@router.post(
    "/{session_id}/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book a class session",
    description=(
        "Reserves a spot for the authenticated member (RN-01–04, RN-07, RN-08). "
        "Confirmed when there is capacity; otherwise waitlisted with a computed position. "
        "Personal training requires a plan with includes_personal_training. "
        "Classes with an extra price create a pending payment on confirm."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {
            "description": (
                "Only members can book, no active subscription (RN-01), "
                "or plan without personal training (RN-08)"
            )
        },
        404: {"description": "The session does not exist"},
        409: {
            "description": (
                "Duplicate booking (RN-03), or the session is past / cancelled (RN-04)"
            )
        },
    },
)
def book_session(
    session_id: int,
    member: CurrentMember,
    db: DbSession,
) -> BookingOut:
    row = booking_service.book_session(
        db, user_id=member.id, class_session_id=session_id
    )
    return BookingOut.from_booking(row.booking, row.waitlist_position)
