from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SubscriptionStatus

SUBSCRIPTION_EXAMPLE = {
    "id": 7,
    "status": "active",
    "start_date": "2026-10-06",
    "end_date": None,
    "plan": {
        "id": 2,
        "name": "Ilimitado",
        "monthly_price_cents": 5900,
        "includes_personal_training": False,
    },
}


class SubscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"plan_id": 2}})

    plan_id: int = Field(ge=1, le=2_147_483_647)


class SubscriptionPlanOut(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    monthly_price_cents: int
    includes_personal_training: bool


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": SUBSCRIPTION_EXAMPLE})

    id: int
    status: SubscriptionStatus
    start_date: date
    end_date: date | None
    plan: SubscriptionPlanOut


class MySubscriptionsOut(BaseModel):

    model_config = ConfigDict(
        json_schema_extra={"example": {"current": SUBSCRIPTION_EXAMPLE, "history": []}}
    )

    current: SubscriptionOut | None
    history: list[SubscriptionOut]