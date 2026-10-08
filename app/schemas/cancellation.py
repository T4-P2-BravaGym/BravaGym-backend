"""Cancellation request schemas (HU-19, RN-12)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CancellationStatus

CANCELLATION_EXAMPLE = {
    "id": 3,
    "subscription_id": 7,
    "reason": "Me mudo de ciudad",
    "status": "pending",
    "requested_at": "2026-10-08T10:00:00Z",
    "reviewed_at": None,
    "admin_notes": None,
}


class CancellationRequestCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"reason": "Me mudo de ciudad"}},
    )

    reason: str = Field(min_length=1, max_length=2000)


class CancellationRequestOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": CANCELLATION_EXAMPLE},
    )

    id: int
    subscription_id: int
    reason: str | None
    status: CancellationStatus
    requested_at: datetime
    reviewed_at: datetime | None
    admin_notes: str | None
