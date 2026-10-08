"""Cancellation request schemas (HU-19 RN-12, HU-20 RN-13)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CancellationStatus
from app.schemas.common import Page

if TYPE_CHECKING:
    from app.models.membership import CancellationRequest

CANCELLATION_EXAMPLE = {
    "id": 3,
    "subscription_id": 7,
    "reason": "Me mudo de ciudad",
    "status": "pending",
    "requested_at": "2026-10-08T10:00:00Z",
    "reviewed_at": None,
    "admin_notes": None,
    "member_name": "Lucía García",
    "member_email": "lucia@example.com",
    "plan_name": "Completo",
}

APPROVED_EXAMPLE = {
    **CANCELLATION_EXAMPLE,
    "status": "approved",
    "reviewed_at": "2026-10-08T12:00:00Z",
    "admin_notes": "Baja confirmada tras la revisión.",
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


class CancellationApprove(BaseModel):
    """Optional notes when approving a cancellation (RN-13)."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"admin_notes": "Baja confirmada tras la revisión."}
        },
    )

    admin_notes: str | None = Field(default=None, max_length=2000)


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
    member_name: str | None = None
    member_email: str | None = None
    plan_name: str | None = None

    @classmethod
    def from_request(cls, request: CancellationRequest) -> CancellationRequestOut:
        """Build the API DTO including member/plan labels for the admin inbox."""
        subscription = request.subscription
        user = subscription.user if subscription is not None else None
        plan = subscription.plan if subscription is not None else None
        member_name = None
        if user is not None:
            member_name = (
                f"{user.first_name} {user.last_name}".strip() or user.email
            )
        return cls(
            id=request.id,
            subscription_id=request.subscription_id,
            reason=request.reason,
            status=request.status,
            requested_at=request.requested_at,
            reviewed_at=request.reviewed_at,
            admin_notes=request.admin_notes,
            member_name=member_name,
            member_email=user.email if user is not None else None,
            plan_name=plan.name if plan is not None else None,
        )


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
