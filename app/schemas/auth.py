from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UserCreate(BaseModel):
    """Body for POST /auth/register. No role or is_active: the server decides them."""

    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    first_name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "lucia@example.com",
                    "password": "BravaDemo2026!",
                    "first_name": "Lucía",
                    "last_name": "Gil",
                    "phone": "600123123",   
                }
            ]
        }
    )

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga.")
        return value  

