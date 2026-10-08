import logging
from enum import StrEnum

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import Product, ProductCategory
from app.schemas.shop import CategoryIn, ProductCreate, ProductUpdate

logger = logging.getLogger(__name__)

INVALID_PRICE_RANGE = "El precio mínimo no puede ser mayor que el precio máximo."
PRODUCT_NOT_FOUND = "Producto no encontrado."
CATEGORY_NOT_FOUND = "Categoría no encontrada."
UNKNOWN_CATEGORY = "La categoría elegida no existe."
CATEGORY_NAME_TAKEN = "Ya existe una categoría con ese nombre."
CATEGORY_HAS_PRODUCTS = "No se puede borrar: esta categoría tiene productos."

class ProductStatus(StrEnum):

    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


_STATUS_CONDITION = {
    ProductStatus.ACTIVE: Product.is_active.is_(True),
    ProductStatus.INACTIVE: Product.is_active.is_(False),
    ProductStatus.OUT_OF_STOCK: Product.stock == 0,
}

class ProductSort(StrEnum):

    NAME = "name"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"


_ORDER_BY = {
    ProductSort.NAME: (Product.name, Product.id),
    ProductSort.PRICE_ASC: (Product.price_cents, Product.name, Product.id),
    ProductSort.PRICE_DESC: (Product.price_cents.desc(), Product.name, Product.id),
}


def list_categories(db: Session) -> list[ProductCategory]:
    stmt = select(ProductCategory).order_by(ProductCategory.name)
    return list(db.scalars(stmt).all())


def list_products(
        db: Session,
        *,
        category_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        q: str | None = None,
        sort: ProductSort = ProductSort.NAME,
        page: int = 1,
        size: int = 20,
        include_inactive: bool = False,
        status: ProductStatus | None = None,
) -> tuple[list[Product], int]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationAppError(INVALID_PRICE_RANGE)

    conditions = [] if include_inactive else [Product.is_active.is_(True)]
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if min_price is not None:
        conditions.append(Product.price_cents >= min_price)
    if max_price is not None:
        conditions.append(Product.price_cents <= max_price)
    if status is not None:
        conditions.append(_STATUS_CONDITION[status])

    search = q.strip() if q else ""
    if search:
        conditions.append(Product.name.icontains(search, autoescape=True))

    total = db.scalar(select(func.count(Product.id)).where(*conditions)) or 0

    order_by = _ORDER_BY[sort]
    if include_inactive:
        order_by = (Product.is_active.desc(), *order_by)

    stmt = (
        select(Product)
        .options(joinedload(Product.category))
        .where(*conditions)
        .order_by(*order_by)
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt).all()), int(total)


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(PRODUCT_NOT_FOUND)
    return product


def _category_for_product(db: Session, category_id: int) -> ProductCategory:
    category = db.get(ProductCategory, category_id)
    if category is None:
        raise ValidationAppError(UNKNOWN_CATEGORY)
    return category


def create_product(db: Session, data: ProductCreate) -> Product:
    fields = data.model_dump()
    category = _category_for_product(db, fields.pop("category_id"))
    product = Product(**fields, category=category, is_active=True)
    db.add(product)
    db.commit()
    db.refresh(product)
    logger.info("Created product %s in category %s", product.id, category.id)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = data.model_dump(exclude_unset=True)
    if "category_id" in changes:
        # Set the relationship, not only the id, so product.category is never stale.
        product.category = _category_for_product(db, changes.pop("category_id"))
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    logger.info("Updated product %s (fields: %s)", product.id, ", ".join(sorted(data.model_fields_set)))
    return product


def deactivate_product(db: Session, product_id: int) -> Product:
    product = get_product(db, product_id)
    if not product.is_active:
        return product
    product.is_active = False
    db.commit()
    db.refresh(product)
    logger.info("Deactivated product %s", product.id)
    return product


def get_category(db: Session, category_id: int) -> ProductCategory:
    category = db.get(ProductCategory, category_id)
    if category is None:
        raise NotFoundError(CATEGORY_NOT_FOUND)
    return category


def _commit_category(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CATEGORY_NAME_TAKEN) from None


def create_category(db: Session, data: CategoryIn) -> ProductCategory:
    category = ProductCategory(name=data.name)
    db.add(category)
    _commit_category(db)
    db.refresh(category)
    logger.info("Created product category %s", category.id)
    return category


def update_category(db: Session, category_id: int, data: CategoryIn) -> ProductCategory:
    category = get_category(db, category_id)
    category.name = data.name
    _commit_category(db)
    db.refresh(category)
    logger.info("Renamed product category %s", category.id)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    has_products = db.scalar(select(exists().where(Product.category_id == category.id)))
    if has_products:
        raise ConflictError(CATEGORY_HAS_PRODUCTS)
    db.delete(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(CATEGORY_HAS_PRODUCTS) from None
    logger.info("Deleted product category %s", category_id)