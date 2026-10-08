from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.shop import (
    MAX_PRICE_CENTS,
    CategoryIn,
    CategoryOut,
    ProductAdminOut,
    ProductAdminPage,
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductUpdate,
)
from app.services import shop_service
from app.services.shop_service import ProductSort, ProductStatus

router = APIRouter(prefix="/products", tags=["shop"])
categories_router = APIRouter(prefix="/product-categories", tags=["shop"])

DbSession = Annotated[Session, Depends(get_db)]
ShopAdmin = Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))]

AUTH_ERRORS = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Caller is not admin or superadmin"},
}


@router.get(
    "",
    response_model=ProductPage,
    summary="List shop products",
    description=(
            "Public list of active products. Filters: category, price range in cents "
            "(both limits inclusive) and a search in the name. Sort by name (default) "
            "or price. Sold-out products are included with in_stock=false."
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
        sort: Annotated[ProductSort, Query(description="Order of the results")] = ProductSort.NAME,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductPage:
    products, total = shop_service.list_products(
        db,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        q=q,
        sort=sort,
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


@router.get(
    "/admin",
    response_model=ProductAdminPage,
    summary="List all products for the admin panel",
    description=(
            "Same filters as the public list, but inactive products are included, "
            "every item has is_active and deactivated products always go last. "
            "Extra filter: status (active, inactive or out_of_stock)."
    ),
    responses=AUTH_ERRORS,
)
def list_products_for_admin(
        _: ShopAdmin,
        db: DbSession,
        category_id: Annotated[int | None, Query(ge=1)] = None,
        q: Annotated[
            str | None,
            Query(max_length=60, description="Case-insensitive search in the product name"),
        ] = None,
        status: Annotated[
            ProductStatus | None,
            Query(description="active, inactive or out_of_stock (stock 0, active or not)"),
        ] = None,
        sort: Annotated[ProductSort, Query(description="Order of the results")] = ProductSort.NAME,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ProductAdminPage:
    products, total = shop_service.list_products(
        db,
        category_id=category_id,
        q=q,
        sort=sort,
        page=page,
        size=size,
        include_inactive=True,
        status=status,
    )
    return ProductAdminPage(
        items=[ProductAdminOut.from_product(product) for product in products],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=ProductAdminOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    responses={
        **AUTH_ERRORS,
        422: {"description": "Negative price or stock, empty name or unknown category"},
    },
)
def create_product(body: ProductCreate, _: ShopAdmin, db: DbSession) -> ProductAdminOut:
    return ProductAdminOut.from_product(shop_service.create_product(db, body))


@router.patch(
    "/{product_id}",
    response_model=ProductAdminOut,
    summary="Update a product",
    description="Partial update. Send is_active=true to reactivate a product.",
    responses={
        **AUTH_ERRORS,
        404: {"description": "Product not found"},
        422: {"description": "Invalid values, null in a required field or unknown category"},
    },
)
def update_product(
        product_id: int, body: ProductUpdate, _: ShopAdmin, db: DbSession
) -> ProductAdminOut:
    return ProductAdminOut.from_product(shop_service.update_product(db, product_id, body))


@router.delete(
    "/{product_id}",
    response_model=ProductAdminOut,
    summary="Deactivate a product",
    description=(
            "Soft delete: sets is_active=false, also when the product has orders. "
            "It disappears from the shop and can be reactivated with PATCH."
    ),
    responses={**AUTH_ERRORS, 404: {"description": "Product not found"}},
)
def deactivate_product(product_id: int, _: ShopAdmin, db: DbSession) -> ProductAdminOut:
    return ProductAdminOut.from_product(shop_service.deactivate_product(db, product_id))


@categories_router.post(
    "",
    response_model=CategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product category",
    responses={
        **AUTH_ERRORS,
        409: {"description": "A category with that name already exists"},
    },
)
def create_category(body: CategoryIn, _: ShopAdmin, db: DbSession) -> CategoryOut:
    return CategoryOut.model_validate(shop_service.create_category(db, body))


@categories_router.patch(
    "/{category_id}",
    response_model=CategoryOut,
    summary="Rename a product category",
    responses={
        **AUTH_ERRORS,
        404: {"description": "Category not found"},
        409: {"description": "A category with that name already exists"},
    },
)
def update_category(
        category_id: int, body: CategoryIn, _: ShopAdmin, db: DbSession
) -> CategoryOut:
    return CategoryOut.model_validate(shop_service.update_category(db, category_id, body))


@categories_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a product category",
    description="Only possible when no product, active or inactive, belongs to it.",
    responses={
        **AUTH_ERRORS,
        404: {"description": "Category not found"},
        409: {"description": "The category still has products"},
    },
)
def delete_category(category_id: int, _: ShopAdmin, db: DbSession) -> None:
    shop_service.delete_category(db, category_id)