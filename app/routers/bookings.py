"""Controller for bookings: receives the request, checks permissions, calls the service, returns a schema.

Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember
from app.models.enums import BookingStatus
from app.schemas.booking import BookingOut, BookingPage
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])

DbSession = Annotated[Session, Depends(get_db)]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}


@router.get(
    "/me",
    response_model=BookingPage,
    summary="List my bookings",
    description=(
        "Returns the authenticated member's bookings. "
        "Filter by status and whether the session is upcoming or past. "
        "Waitlist position is computed, never stored."
    ),
    responses=AUTH_RESPONSES,
)
def list_my_bookings(
    member: CurrentMember,
    db: DbSession,
    status: Annotated[
        BookingStatus | None,
        Query(description="Filter by booking status"),
    ] = None,
    upcoming: Annotated[
        bool | None,
        Query(
            description=(
                "If true, only future sessions; if false, only past sessions; "
                "if omitted, both"
            )
        ),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BookingPage:
    rows, total = booking_service.list_my_bookings(
        db,
        user_id=member.id,
        status=status,
        upcoming=upcoming,
        page=page,
        size=size,
    )
    return BookingPage(
        items=[
            BookingOut.from_booking(row.booking, row.waitlist_position) for row in rows
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingOut,
    summary="Cancel my booking",
    description=(
        "Cancels the authenticated member's booking (RN-05, RN-06). "
        "Confirmed bookings need at least 60 minutes before starts_at; "
        "leaving the waitlist is always allowed. Cancelling a confirmed spot "
        "promotes the oldest waitlisted booking in the same transaction."
    ),
    responses={
        **AUTH_RESPONSES,
        404: {"description": "The booking does not exist or is not yours"},
        409: {
            "description": (
                "Already cancelled, or confirmed cancel within 60 minutes of start (RN-05)"
            )
        },
    },
)
def cancel_booking(
    booking_id: int,
    member: CurrentMember,
    db: DbSession,
) -> BookingOut:
    row = booking_service.cancel_booking(
        db, user_id=member.id, booking_id=booking_id
    )
    return BookingOut.from_booking(row.booking, row.waitlist_position)
