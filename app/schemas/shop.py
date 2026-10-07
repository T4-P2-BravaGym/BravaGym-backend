from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.common import Page

if TYPE_CHECKING:
    from app.models import Product

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

PRODUCT_PAGE_EXAMPLE = {
    "items": [PRODUCT_EXAMPLE],
    "total": 1,
    "page": 1,
    "size": 20,
}


class CategoryOut(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": CATEGORY_EXAMPLE},
    )

    id: int
    name: str = Field(max_length=60)


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
        return cls(
            id=product.id,
            category_id=product.category_id,
            category_name=product.category.name,
            name=product.name,
            description=product.description,
            price_cents=product.price_cents,
            stock=product.stock,
        )


class ProductPage(Page[ProductOut]):
    model_config = ConfigDict(json_schema_extra={"example": PRODUCT_PAGE_EXAMPLE})