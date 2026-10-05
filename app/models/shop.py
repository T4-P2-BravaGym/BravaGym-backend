"""Shop: categories, products and orders (HU-21 to HU-23).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    ProductCategory: id, name (unique)
    Product: id, category_id -> product_categories.id, name, description, price_cents,
             stock, is_active
    Order: id, user_id -> users.id, status (pending | paid | cancelled), created_at
    OrderItem: id, order_id -> orders.id, product_id -> products.id, quantity,
               unit_price_cents (price at the moment of buying)
               UNIQUE(order_id, product_id)
"""
from app.core.database import Base  # noqa: F401
