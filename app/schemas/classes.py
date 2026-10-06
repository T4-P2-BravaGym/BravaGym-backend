"""Class type and session schemas for the public schedule (HU-10)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SessionStatus
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
