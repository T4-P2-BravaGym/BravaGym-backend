"""TODO(HU-02, HU-04, HU-05, HU-15): UserOut (never password_hash), UserUpdate (no role, no is_active), RoleUpdate, TrainerOut.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from pydantic import BaseModel, ConfigDict


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
    