"""Class type and session schemas (HU-10 schedule, HU-11 trainer management, HU-14 PT)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BookingStatus, SessionStatus
from app.schemas.common import Page

SESSION_EXAMPLE = {
    "id": 3,
    "trainer_id": 2,
    "starts_at": "2026-10-07T17:30:00Z",
    "duration_minutes": 60,
    "capacity": 8,
    "status": "scheduled",
    "free_spots": 5,
    "class_type": {
        "id": 3,
        "name": "Taller de halterofilia",
        "extra_price_cents": 1200,
        "is_personal_training": False,
    },
}

SESSION_PAGE_EXAMPLE = {
    "items": [SESSION_EXAMPLE],
    "total": 1,
    "page": 1,
    "size": 20,
}

CLASS_TYPE_EXAMPLE = {
    "id": 1,
    "name": "Fuerza total",
    "description": "Sentadilla, peso muerto y press.",
    "extra_price_cents": 0,
    "is_personal_training": False,
    "is_active": True,
}

SESSION_BOOKING_EXAMPLE = {
    "id": 12,
    "status": "confirmed",
    "waitlist_position": None,
    "created_at": "2026-10-07T08:15:00Z",
    "cancelled_at": None,
    "user": {
        "id": 5,
        "email": "lucia@example.com",
        "first_name": "Lucía",
        "last_name": "García",
    },
}


class SessionClassTypeOut(BaseModel):
    """Class type fields shown on each session in the schedule."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    extra_price_cents: int = Field(ge=0)
    is_personal_training: bool


class SessionOut(BaseModel):
    """A scheduled class session with computed free spots and extra price."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": SESSION_EXAMPLE},
    )

    id: int
    trainer_id: int
    starts_at: datetime
    duration_minutes: int = Field(ge=1)
    capacity: int = Field(ge=1)
    status: SessionStatus
    free_spots: int = Field(ge=0)
    class_type: SessionClassTypeOut


class SessionPage(Page[SessionOut]):
    model_config = ConfigDict(json_schema_extra={"example": SESSION_PAGE_EXAMPLE})


class PersonalTrainingSlotCreate(BaseModel):
    """Body for a trainer to open a one-hour personal-training slot (RN-08)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "starts_at": "2026-10-08T10:00:00Z",
                "class_type_id": 4,
            }
        }
    )

    starts_at: datetime
    class_type_id: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional personal-training class type. "
            "When omitted, the first active PT class type is used."
        ),
    )


class SessionCreate(BaseModel):
    """Body to create a session. Trainers become the owner; superadmin may set trainer_id."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "class_type_id": 1,
                "starts_at": "2026-10-08T17:30:00Z",
                "duration_minutes": 60,
                "capacity": 12,
            }
        }
    )

    class_type_id: int = Field(ge=1)
    starts_at: datetime
    duration_minutes: int = Field(default=60, ge=1, le=24 * 60)
    capacity: int = Field(ge=1, le=500)
    trainer_id: int | None = Field(
        default=None,
        ge=1,
        description="Required when the caller is superadmin; ignored for trainers",
    )


class SessionUpdate(BaseModel):
    """Partial update of a session. Omitted fields stay unchanged."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "starts_at": "2026-10-08T18:00:00Z",
                "duration_minutes": 60,
                "capacity": 10,
            }
        }
    )

    class_type_id: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=24 * 60)
    capacity: int | None = Field(default=None, ge=1, le=500)


class ClassTypeOut(BaseModel):
    """Public class type used in schedules and trainer forms."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": CLASS_TYPE_EXAMPLE},
    )

    id: int
    name: str
    description: str | None
    extra_price_cents: int = Field(ge=0)
    is_personal_training: bool
    is_active: bool


class ClassTypeCreate(BaseModel):
    """Body to create a class type."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Movilidad y core",
                "description": "Movilidad, estabilidad y core.",
                "extra_price_cents": 0,
                "is_personal_training": False,
            }
        }
    )

    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    extra_price_cents: int = Field(default=0, ge=0)
    is_personal_training: bool = False


class ClassTypeUpdate(BaseModel):
    """Partial update of a class type. Omitted fields stay unchanged."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Actualizado.",
                "extra_price_cents": 500,
            }
        }
    )

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    extra_price_cents: int | None = Field(default=None, ge=0)
    is_personal_training: bool | None = None
    is_active: bool | None = None


class ClassTypePage(Page[ClassTypeOut]):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [CLASS_TYPE_EXAMPLE],
                "total": 1,
                "page": 1,
                "size": 20,
            }
        }
    )


class SessionBookingUserOut(BaseModel):
    """Member summary on a session booking list (no password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str


class SessionBookingOut(BaseModel):
    """Confirmed or waitlisted booking for a session roster."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": SESSION_BOOKING_EXAMPLE},
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
    user: SessionBookingUserOut
