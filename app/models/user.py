"""Users, roles and trainer profiles (HU-01, HU-02, HU-05, HU-15).

TODO(HU-01): write these SQLAlchemy models (inherit from app.core.database.Base).
Full diagram and normalization notes: docs/er.md. Money in integer cents, dates in UTC,
statuses as Enum (it creates a CHECK constraint in SQLite).

    Role: id, name (unique: member | trainer | admin | superadmin)
    User: id, email (unique), password_hash, first_name, last_name, phone,
          role_id -> roles.id, is_active, created_at, deactivated_at (nullable, soft delete)
    TrainerProfile: user_id (PK, FK -> users.id), bio, specialty
"""
from app.core.database import Base  # noqa: F401
