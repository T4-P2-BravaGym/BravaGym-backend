from typing import Literal

from pydantic import BaseModel, ConfigDict


class LoginResponse(BaseModel):

    model_config = ConfigDict(
        json_schema_extra={"example": {"access_token": "eyJhbGciOi...", "token_type": "bearer"}}
    )

    access_token: str
    token_type: Literal["bearer"] = "bearer"