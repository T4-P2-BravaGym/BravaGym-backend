"""TODO(HU-04, HU-05, HU-15): UserUpdate (no role, no is_active), RoleUpdate, TrainerOut.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""
from pydantic import AliasPath, BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RoleName


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


class UserOut(BaseModel):
    """Public view of a user. Never includes password_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None
    is_active: bool
    role: RoleName = Field(validation_alias=AliasPath("role", "name"))


class UserUpdate(BaseModel):
    """What a user can change in her own profile. Never role or is_active."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"first_name": "Lucía", "last_name": "García", "phone": "600123456", "email": "lucia@example.com"}
        }
    )

    # Names can be left out, but never sent as null: the database requires them
    first_name: str = Field(default=None, min_length=1, max_length=80)
    last_name: str = Field(default=None, min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr = Field(default=None, max_length=255)