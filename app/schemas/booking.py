"""Booking schemas for reserving a class and listing my bookings (HU-12)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookingStatus, SessionStatus
from app.schemas.classes import SessionClassTypeOut
from app.schemas.common import Page

BOOKING_EXAMPLE = {
    "id": 12,
    "status": "waitlisted",
    "waitlist_position": 2,
    "created_at": "2026-10-07T08:15:00Z",
    "cancelled_at": None,
    "class_session": {
        "id": 3,
        "trainer_id": 2,
        "starts_at": "2026-10-07T17:30:00Z",
        "duration_minutes": 60,
        "capacity": 8,
        "status": "scheduled",
        "class_type": {
            "id": 3,
            "name": "Taller de halterofilia",
            "extra_price_cents": 1200,
            "is_personal_training": False,
        },
    },
}

BOOKING_PAGE_EXAMPLE = {
    "items": [BOOKING_EXAMPLE],
    "total": 1,
    "page": 1,
    "size": 20,
}


class BookingSessionOut(BaseModel):
    """Session fields shown on a booking (no free_spots — not needed here)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trainer_id: int
    starts_at: datetime
    duration_minutes: int = Field(ge=1)
    capacity: int = Field(ge=1)
    status: SessionStatus
    class_type: SessionClassTypeOut


class BookingOut(BaseModel):
    """A booking with computed waitlist position when status is waitlisted."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": BOOKING_EXAMPLE},
    )

    id: int
    status: BookingStatus
    waitlist_position: int | None = Field(
        default=None,
        description="1-based position among waitlisted bookings; null unless waitlisted",
        ge=1,
    )
    created_at: datetime
    cancelled_at: datetime | None
    class_session: BookingSessionOut

    @classmethod
    def from_booking(cls, booking, waitlist_position: int | None) -> "BookingOut":
        return cls(
            id=booking.id,
            status=booking.status,
            waitlist_position=waitlist_position,
            created_at=booking.created_at,
            cancelled_at=booking.cancelled_at,
            class_session=booking.class_session,
        )



class BookingPage(Page[BookingOut]):
    model_config = ConfigDict(json_schema_extra={"example": BOOKING_PAGE_EXAMPLE})
