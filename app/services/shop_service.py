from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ValidationAppError
from app.models import Product, ProductCategory

INVALID_PRICE_RANGE = "El precio mínimo no puede ser mayor que el precio máximo."


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
        page: int = 1,
        size: int = 20,
) -> tuple[list[Product], int]:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationAppError(INVALID_PRICE_RANGE)

    conditions = [Product.is_active.is_(True)]
    if category_id is not None:
        conditions.append(Product.category_id == category_id)
    if min_price is not None:
        conditions.append(Product.price_cents >= min_price)
    if max_price is not None:
        conditions.append(Product.price_cents <= max_price)

    search = q.strip() if q else ""
    if search:
        conditions.append(Product.name.icontains(search, autoescape=True))

    total = db.scalar(select(func.count(Product.id)).where(*conditions)) or 0

    stmt = (
        select(Product)
        .options(joinedload(Product.category))
        .where(*conditions)
        .order_by(Product.name, Product.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(stmt).all()), int(total)