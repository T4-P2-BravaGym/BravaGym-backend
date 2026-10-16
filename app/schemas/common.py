"""Shared schemas: paginated lists and the body of every error (T-02)."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Paginated list payload: {items, total, page, size}."""

    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)


class ErrorOut(BaseModel):
    """Body of every error the API sends (app/core/exceptions.py): a Spanish message and a code."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"detail": "No existe ese usuario.", "code": "not_found"}
        }
    )

    detail: str
    code: str
