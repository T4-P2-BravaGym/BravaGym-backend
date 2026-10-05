"""Class types, sessions and bookings (HU-10 to HU-14).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    ClassType: id, name (unique), description, extra_price_cents (0 = included),
               is_personal_training, is_active
    ClassSession: id, class_type_id -> class_types.id, trainer_id -> users.id, starts_at,
                  duration_minutes, capacity, status (scheduled | cancelled)
    Booking: id, user_id -> users.id, class_session_id -> class_sessions.id,
             status (confirmed | waitlisted | cancelled), created_at, cancelled_at (nullable)
             UNIQUE(user_id, class_session_id)
"""
from app.core.database import Base  # noqa: F401
