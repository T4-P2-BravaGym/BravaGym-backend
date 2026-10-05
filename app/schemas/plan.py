"""TODO(HU-07, HU-08, HU-09): PlanOut, PlanCreate, PlanUpdate, SubscriptionOut.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""

from pydantic import BaseModel, ConfigDict

class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    monthly_price_cents: int
    includes_personal_training: bool