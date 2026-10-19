"""Bounded reset inputs; validation errors must be sanitized by the reset router."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.auth import check_fits_bcrypt


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid", json_schema_extra={"example": {"email": "lucia@example.com"}}
    )
    email: EmailStr = Field(max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def strip_email(cls, value):
        return value.strip() if isinstance(value, str) else value


class PasswordResetConfirm(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {"token": "<reset token>", "new_password": "OtraClave2026!"}
        },
    )
    token: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        return check_fits_bcrypt(value)


class PasswordResetAccepted(BaseModel):
    detail: str
