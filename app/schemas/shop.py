from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.schemas.common import Page

if TYPE_CHECKING:
    from app.models import Product

MAX_PRICE_CENTS = 1_000_000
MAX_STOCK = 100_000

CATEGORY_EXAMPLE = {"id": 1, "name": "Suplementos"}

PRODUCT_EXAMPLE = {
    "id": 1,
    "category_id": 1,
    "category_name": "Suplementos",
    "name": "Proteína whey 1 kg",
    "description": "Sabor vainilla.",
    "price_cents": 3490,
    "stock": 20,
    "in_stock": True,
}

PRODUCT_ADMIN_EXAMPLE = {**PRODUCT_EXAMPLE, "is_active": True}

PRODUCT_PAGE_EXAMPLE = {
    "items": [PRODUCT_EXAMPLE],
    "total": 1,
    "page": 1,
    "size": 20,
}

PRODUCT_ADMIN_PAGE_EXAMPLE = {**PRODUCT_PAGE_EXAMPLE, "items": [PRODUCT_ADMIN_EXAMPLE]}


class CategoryOut(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": CATEGORY_EXAMPLE},
    )

    id: int
    name: str = Field(max_length=60)


class CategoryIn(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"example": {"name": "Accesorios"}},
    )

    name: str = Field(min_length=1, max_length=60)


def _product_fields(product: "Product") -> dict[str, Any]:
    return {
        "id": product.id,
        "category_id": product.category_id,
        "category_name": product.category.name,
        "name": product.name,
        "description": product.description,
        "price_cents": product.price_cents,
        "stock": product.stock,
    }


class ProductOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_EXAMPLE})

    id: int
    category_id: int
    category_name: str = Field(max_length=60)
    name: str = Field(max_length=120)
    description: str | None
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0)

    @computed_field
    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @classmethod
    def from_product(cls, product: "Product") -> "ProductOut":
        return cls(**_product_fields(product))


class ProductAdminOut(ProductOut):

    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_ADMIN_EXAMPLE})

    is_active: bool

    @classmethod
    def from_product(cls, product: "Product") -> "ProductAdminOut":
        return cls(**_product_fields(product), is_active=product.is_active)


class ProductCreate(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "category_id": 1,
                "name": "Proteína whey 1 kg",
                "description": "Sabor vainilla.",
                "price_cents": 3490,
                "stock": 20,
            }
        },
    )

    category_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int = Field(ge=0, le=MAX_PRICE_CENTS)
    stock: int = Field(default=0, ge=0, le=MAX_STOCK)


_NOT_NULL_FIELDS = ("category_id", "name", "price_cents", "stock", "is_active")


class ProductUpdate(BaseModel):

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={"example": {"price_cents": 2990, "stock": 15}},
    )

    category_id: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int | None = Field(default=None, ge=0, le=MAX_PRICE_CENTS)
    stock: int | None = Field(default=None, ge=0, le=MAX_STOCK)
    is_active: bool | None = None

    @model_validator(mode="after")
    def reject_null_for_required_columns(self) -> "ProductUpdate":
        for field in _NOT_NULL_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ProductPage(Page[ProductOut]):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_PAGE_EXAMPLE})


class ProductAdminPage(Page[ProductAdminOut]):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_ADMIN_PAGE_EXAMPLE})