"""TODO(HU-07, HU-08): PlanOut, PlanCreate, PlanUpdate. (SubscriptionOut lives in subscription.py.)

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic import BaseModel, ConfigDict, computed_field


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    monthly_price_cents: int = Field(ge=0)
    includes_personal_training: bool

    @computed_field
    @property
    def monthly_price_formatted(self) -> str:
        euros, cents = divmod(self.monthly_price_cents, 100)
        return f"{euros},{cents:02d} €"
    



