"""TODO(HU-07, HU-08): PlanOut, PlanCreate, PlanUpdate. (SubscriptionOut lives in subscription.py.)

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.

"""

from pydantic import BaseModel, ConfigDict

class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    monthly_price_cents: int
    includes_personal_training: bool



