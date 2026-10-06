"""Users, roles and trainer profiles (HU-01, HU-02, HU-05, HU-15)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RoleName
from app.models.types import db_enum, utc_now


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[RoleName] = mapped_column(db_enum(RoleName), unique=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(20))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    deactivated_at: Mapped[datetime | None]

    role: Mapped["Role"] = relationship(lazy="joined")
    trainer_profile: Mapped[Optional["TrainerProfile"]] = relationship(back_populates="user")


class TrainerProfile(Base):
    __tablename__ = "trainer_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    bio: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(String(120))

    user: Mapped["User"] = relationship(back_populates="trainer_profile")