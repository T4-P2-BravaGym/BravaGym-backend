"""TODO(HU-04, HU-05, HU-15): UserUpdate (no role, no is_active), RoleUpdate, TrainerOut.

Rules: limits on every field (max_length, ge, le); output schemas list only safe fields.
"""

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.models.enums import RoleName


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
