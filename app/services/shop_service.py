import logging
from enum import StrEnum

from sqlalchemy import and_, case, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.cache import (
    invalidate_products_cache,
    products_cache_key,
    response_cache,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import Product, ProductCategory, ProductVariant
from app.schemas.shop import (
    CategoryIn,
    ProductCreate,
    ProductOut,
    ProductPage,
    ProductUpdate,
    SizeIn,
)

logger = logging.getLogger(__name__)

INVALID_PRICE_RANGE = "El precio mínimo no puede ser mayor que el precio máximo."
PRODUCT_NOT_FOUND = "Producto no encontrado."
CATEGORY_NOT_FOUND = "Categoría no encontrada."
UNKNOWN_CATEGORY = "La categoría elegida no existe."
CATEGORY_NAME_TAKEN = "Ya existe una categoría con ese nombre."
CATEGORY_HAS_PRODUCTS = "No se puede borrar: esta categoría tiene productos."
STOCK_IS_PER_SIZE = "Este producto tiene tallas: el stock se pone en cada talla."

_ACTIVE_SIZE = and_(ProductVariant.product_id == Product.id, ProductVariant.is_active.is_(True))
_HAS_SIZES = exists().where(_ACTIVE_SIZE)
_SIZES_STOCK = (
    select(func.coalesce(func.sum(ProductVariant.stock), 0)).where(_ACTIVE_SIZE).scalar_subquery()
)
AVAILABLE_STOCK = case((_HAS_SIZES, _SIZES_STOCK), else_=Product.stock)


class ProductStatus(StrEnum):

    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


_STATUS_CONDITION = {
    ProductStatus.ACTIVE: Product.is_active.is_(True),
    ProductStatus.INACTIVE: Product.is_active.is_(False),
    ProductStatus.OUT_OF_STOCK: AVAILABLE_STOCK == 0,
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
        .options(joinedload(Product.category), selectinload(Product.variants))
        .where(*conditions)
        .order_by(*order_by)
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt).all()), int(total)


def list_public_products(
        db: Session,
        *,
        category_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        q: str | None = None,
        sort: ProductSort = ProductSort.NAME,
        page: int = 1,
        size: int = 20,
) -> ProductPage:
    """Public shop list; served from an in-memory TTL cache when possible (HU-28)."""
    key = products_cache_key(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        q=q,
        sort=sort.value,
        page=page,
        size=size,
    )
    cached = response_cache.get(key)
    if cached is not None:
        return ProductPage.model_validate(cached)

    products, total = list_products(
        db,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        q=q,
        sort=sort,
        page=page,
        size=size,
    )
    page_payload = ProductPage(
        items=[ProductOut.from_product(product) for product in products],
        total=total,
        page=page,
        size=size,
    )
    response_cache.set(key, page_payload.model_dump(mode="json"))
    return page_payload


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


def _apply_sizes(product: Product, sizes: list[SizeIn]) -> None:
    wanted = {item.size: item.stock for item in sizes}
    existing = {variant.size: variant for variant in product.variants}
    for size, stock in wanted.items():
        variant = existing.get(size)
        if variant is None:
            product.variants.append(ProductVariant(size=size, stock=stock, is_active=True))
        else:
            variant.stock = stock
            variant.is_active = True
    for size, variant in existing.items():
        if size not in wanted and variant.is_active:
            variant.stock = 0
            variant.is_active = False
    if wanted:
        product.stock = 0


def create_product(db: Session, data: ProductCreate) -> Product:
    fields = data.model_dump(exclude={"sizes"})
    category = _category_for_product(db, fields.pop("category_id"))
    product = Product(**fields, category=category, is_active=True)
    if data.sizes:
        _apply_sizes(product, data.sizes)
    db.add(product)
    db.commit()
    db.refresh(product)
    invalidate_products_cache()
    logger.info(
        "Created product %s in category %s (%s sizes)", product.id, category.id, len(data.sizes)
    )
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    changes = data.model_dump(exclude_unset=True, exclude={"sizes"})
    sizes_sent = "sizes" in data.model_fields_set
    will_have_sizes = bool(data.sizes) if sizes_sent else product.has_sizes
    if "stock" in changes and will_have_sizes:
        raise ValidationAppError(STOCK_IS_PER_SIZE)

    if sizes_sent:
        _apply_sizes(product, data.sizes)
    if "category_id" in changes:
        product.category = _category_for_product(db, changes.pop("category_id"))
    for field, value in changes.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    invalidate_products_cache()
    logger.info("Updated product %s (fields: %s)", product.id, ", ".join(sorted(data.model_fields_set)))
    return product


def deactivate_product(db: Session, product_id: int) -> Product:
    product = get_product(db, product_id)
    if not product.is_active:
        return product
    product.is_active = False
    db.commit()
    db.refresh(product)
    invalidate_products_cache()
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
    # Category name appears on product cards; keep public lists coherent.
    invalidate_products_cache()
    logger.info("Created product category %s", category.id)
    return category


def update_category(db: Session, category_id: int, data: CategoryIn) -> ProductCategory:
    category = get_category(db, category_id)
    category.name = data.name
    _commit_category(db)
    db.refresh(category)
    invalidate_products_cache()
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
    invalidate_products_cache()
    logger.info("Deleted product category %s", category_id)