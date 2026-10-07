"""Plan response schema.

TODO(HU-08): PlanCreate, PlanUpdate.
SubscriptionOut lives in subscription.py.
"""


from pydantic import BaseModel, ConfigDict, Field, computed_field

class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str = Field(max_length=80)
    description: str | None
    monthly_price_cents: int = Field(ge=0)
    includes_personal_training: bool

    @computed_field
    @property
    def monthly_price_formatted(self) -> str:
        euros, cents = divmod(self.monthly_price_cents, 100)
        return f"{euros},{cents:02d} €"
    



