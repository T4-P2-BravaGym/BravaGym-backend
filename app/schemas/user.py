"""TODO(HU-02, HU-04, HU-05, HU-15): UserOut (never password_hash), UserUpdate (no role, no is_active), RoleUpdate, TrainerOut.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from pydantic import BaseModel, ConfigDict, Field


class TrainerOut(BaseModel):
    """Public trainer card. Never includes email or phone."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 3,
                "name": "Ana Torres",
                "specialty": "Powerlifting",
                "bio": "Entrenadora de fuerza con 8 años de experiencia.",
            }
        }
    )

    id: int
    name: str
    specialty: str | None
    bio: str | None

    
class TrainerProfileUpdate(BaseModel):
    """What a trainer can change in her public profile. Fields left out are not changed."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"specialty": "Powerlifting", "bio": "Fuerza desde cero."}}
    )

    specialty: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=1000)