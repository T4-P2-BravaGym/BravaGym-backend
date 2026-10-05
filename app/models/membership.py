"""Plans, subscriptions and cancellation requests (HU-07, HU-09, HU-19, HU-20).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    MembershipPlan: id, name (unique), description, monthly_price_cents,
                    includes_personal_training, is_active
    Subscription: id, user_id -> users.id, plan_id -> membership_plans.id, start_date,
                  end_date (nullable), status (active | cancelled | expired)
    CancellationRequest: id, subscription_id -> subscriptions.id, reason,
                         status (pending | approved | rejected), requested_at,
                         reviewed_by -> users.id (nullable), reviewed_at (nullable), admin_notes
"""
from app.core.database import Base  # noqa: F401
