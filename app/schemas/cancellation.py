"""Cancellation request schemas (HU-19 RN-12, HU-20 RN-13)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CancellationStatus
from app.schemas.common import Page

CANCELLATION_EXAMPLE = {
    "id": 3,
    "subscription_id": 7,
    "reason": "Me mudo de ciudad",
    "status": "pending",
    "requested_at": "2026-10-08T10:00:00Z",
    "reviewed_at": None,
    "admin_notes": None,
}

APPROVED_EXAMPLE = {
    **CANCELLATION_EXAMPLE,
    "status": "approved",
    "reviewed_at": "2026-10-08T12:00:00Z",
    "admin_notes": None,
}

REJECTED_EXAMPLE = {
    **CANCELLATION_EXAMPLE,
    "status": "rejected",
    "reviewed_at": "2026-10-08T12:00:00Z",
    "admin_notes": "Queremos proponerte un plan más flexible.",
}


class CancellationRequestCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"reason": "Me mudo de ciudad"}},
    )

    reason: str = Field(min_length=1, max_length=2000)


class CancellationReject(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"admin_notes": "Queremos proponerte un plan más flexible."}
        },
    )

    admin_notes: str = Field(min_length=1, max_length=2000)


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


class CancellationRequestPage(Page[CancellationRequestOut]):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [CANCELLATION_EXAMPLE, APPROVED_EXAMPLE, REJECTED_EXAMPLE],
                "total": 3,
                "page": 1,
                "size": 20,
            }
        }
    )
