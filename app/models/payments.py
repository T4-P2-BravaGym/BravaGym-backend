"""Discount codes and payments (HU-24 to HU-26).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    DiscountCode: id, code (unique), percent_off (1-100), valid_from, valid_until,
                  max_uses (nullable), is_active, created_by -> users.id
    Payment: id, user_id -> users.id, subscription_id / booking_id / order_id (exactly one
             is not null: CHECK constraint), discount_code_id (nullable), base_amount_cents,
             final_amount_cents, status (pending | paid | failed | refunded),
             method (simulated | stripe), provider_ref (nullable), created_at, paid_at (nullable)
"""
from app.core.database import Base  # noqa: F401
