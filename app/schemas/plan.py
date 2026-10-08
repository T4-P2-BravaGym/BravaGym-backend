"""TODO(HU-07, HU-08): PlanOut, PlanCreate, PlanUpdate. (SubscriptionOut lives in subscription.py.)

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
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
    

class PlanCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Strength",
                "description": "Hasta 3 clases a la semana.",
                "monthly_price_cents": 4500,
                "includes_personal_training": False,
            }
        }
    )
    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    monthly_price_cents: int = Field(ge=0)
    includes_personal_training: bool = False


class PlanUpdate(BaseModel):
    """Fields left out of the request are not changed."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "monthly_price_cents": 4500,
                "description": "Hasta 3 clases a la semana.",
            }
        }
    )
    name: str = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    monthly_price_cents: int = Field(default=None, ge=0)
    includes_personal_training: bool = Field(default=None)
