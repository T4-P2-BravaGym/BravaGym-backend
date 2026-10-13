from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from app.models.enums import ProductSize
from app.schemas.common import Page

if TYPE_CHECKING:
    from app.models import Product

MAX_PRICE_CENTS = 1_000_000
MAX_STOCK = 100_000
MAX_SIZES = len(ProductSize)

STOCK_WITH_SIZES = "when the product has sizes, send the stock of each size instead of stock"

CATEGORY_EXAMPLE = {"id": 1, "name": "Suplementos"}

PRODUCT_EXAMPLE = {
    "id": 1,
    "category_id": 1,
    "category_name": "Suplementos",
    "name": "Proteína whey 1 kg",
    "description": "Sabor vainilla.",
    "price_cents": 3490,
    "stock": 20,
    "sizes": [],
    "in_stock": True,
}

CLOTHING_EXAMPLE = {
    "id": 3,
    "category_id": 2,
    "category_name": "Ropa",
    "name": "Camiseta Brava",
    "description": None,
    "price_cents": 2200,
    "stock": 30,
    "sizes": [
        {"id": 1, "size": "S", "stock": 10},
        {"id": 2, "size": "M", "stock": 12},
        {"id": 3, "size": "L", "stock": 8},
    ],
    "in_stock": True,
}

PRODUCT_ADMIN_EXAMPLE = {**PRODUCT_EXAMPLE, "is_active": True}

PRODUCT_PAGE_EXAMPLE = {
    "items": [PRODUCT_EXAMPLE, CLOTHING_EXAMPLE],
    "total": 2,
    "page": 1,
    "size": 20,
}

PRODUCT_ADMIN_PAGE_EXAMPLE = {**PRODUCT_PAGE_EXAMPLE, "items": [PRODUCT_ADMIN_EXAMPLE], "total": 1}


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


class SizeOut(BaseModel):
    id: int
    size: ProductSize
    stock: int = Field(ge=0)


class SizeIn(BaseModel):
    size: ProductSize
    stock: int = Field(default=0, ge=0, le=MAX_STOCK)


def _reject_repeated_sizes(sizes: list[SizeIn] | None) -> list[SizeIn] | None:
    if sizes is not None:
        names = [item.size for item in sizes]
        if len(names) != len(set(names)):
            raise ValueError("each size can only appear once")
    return sizes


def _product_fields(product: "Product") -> dict[str, Any]:
    return {
        "id": product.id,
        "category_id": product.category_id,
        "category_name": product.category.name,
        "name": product.name,
        "description": product.description,
        "price_cents": product.price_cents,
        "stock": product.available_stock,
        "sizes": [
            SizeOut(id=variant.id, size=variant.size, stock=variant.stock)
            for variant in product.active_variants
        ],
    }


class ProductOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_EXAMPLE})

    id: int
    category_id: int
    category_name: str = Field(max_length=60)
    name: str = Field(max_length=120)
    description: str | None
    price_cents: int = Field(ge=0)
    stock: int = Field(ge=0, description="Units on sale (for clothing, the total of its sizes)")
    sizes: list[SizeOut] = Field(
        default_factory=list,
        description="Sizes on sale, from XS to XL. Empty when the product has no sizes.",
    )

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
                "category_id": 2,
                "name": "Camiseta Brava",
                "description": "Algodón orgánico.",
                "price_cents": 2200,
                "sizes": [{"size": "S", "stock": 10}, {"size": "M", "stock": 12}],
            }
        },
    )

    category_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int = Field(ge=0, le=MAX_PRICE_CENTS)
    stock: int = Field(default=0, ge=0, le=MAX_STOCK)
    sizes: list[SizeIn] = Field(
        default_factory=list,
        max_length=MAX_SIZES,
        description="Only for clothing: the stock of each size. Then do not send stock.",
    )

    @field_validator("sizes")
    @classmethod
    def reject_repeated_sizes(cls, sizes: list[SizeIn]) -> list[SizeIn]:
        return _reject_repeated_sizes(sizes)

    @model_validator(mode="after")
    def stock_goes_in_each_size(self) -> "ProductCreate":
        if self.sizes and "stock" in self.model_fields_set:
            raise ValueError(STOCK_WITH_SIZES)
        return self


_NOT_NULL_FIELDS = ("category_id", "name", "price_cents", "stock", "is_active", "sizes")


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
    sizes: list[SizeIn] | None = Field(
        default=None,
        max_length=MAX_SIZES,
        description="Replaces the sizes. A size left out is hidden, not deleted. [] removes them all.",
    )

    @field_validator("sizes")
    @classmethod
    def reject_repeated_sizes(cls, sizes: list[SizeIn] | None) -> list[SizeIn] | None:
        return _reject_repeated_sizes(sizes)

    @model_validator(mode="after")
    def check_nulls_and_stock(self) -> "ProductUpdate":
        for field in _NOT_NULL_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if self.sizes and "stock" in self.model_fields_set:
            raise ValueError(STOCK_WITH_SIZES)
        return self


class ProductPage(Page[ProductOut]):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_PAGE_EXAMPLE})


class ProductAdminPage(Page[ProductAdminOut]):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_ADMIN_PAGE_EXAMPLE})