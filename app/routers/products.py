from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.shop import CategoryOut, ProductOut, ProductPage
from app.services import shop_service

router = APIRouter(prefix="/products", tags=["shop"])
categories_router = APIRouter(prefix="/product-categories", tags=["shop"])

DbSession = Annotated[Session, Depends(get_db)]

MAX_PRICE_CENTS = 1_000_000


@router.get(
    "",
    response_model=ProductPage,
    summary="List shop products",
    description=(
            "Public list of active products, ordered by name. Filters: category, "
            "price range in cents (both limits inclusive) and a search in the name. "
            "Sold-out products are included with in_stock=false."
    ),
    responses={
        422: {"description": "min_price greater than max_price, or invalid query parameters"},
    },
)
def list_products(
        db: DbSession,
        category_id: Annotated[int | None, Query(ge=1)] = None,
        min_price: Annotated[
            int | None,
            Query(ge=0, le=MAX_PRICE_CENTS, description="Minimum price in cents (inclusive)"),
        ] = None,
        max_price: Annotated[
            int | None,
            Query(ge=0, le=MAX_PRICE_CENTS, description="Maximum price in cents (inclusive)"),
        ] = None,
        q: Annotated[
            str | None,
            Query(max_length=60, description="Case-insensitive search in the product name"),
        ] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductPage:
    products, total = shop_service.list_products(
        db,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        q=q,
        page=page,
        size=size,
    )
    return ProductPage(
        items=[ProductOut.from_product(product) for product in products],
        total=total,
        page=page,
        size=size,
    )


@categories_router.get(
    "",
    response_model=list[CategoryOut],
    summary="List product categories",
    description="Public list of categories, in alphabetical order, for the shop filters.",
)
def list_categories(db: DbSession) -> list[CategoryOut]:
    return [CategoryOut.model_validate(category) for category in shop_service.list_categories(db)]