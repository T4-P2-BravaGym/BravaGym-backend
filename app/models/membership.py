from datetime import date, datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import CancellationStatus, SubscriptionStatus
from app.models.types import db_enum, utc_now

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User

class MembershipPlan(Base):
    __tablename__ = "membership_plans"
    __table_args__ = (
        CheckConstraint("monthly_price_cents >= 0", name="ck_membership_plans_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    monthly_price_cents: Mapped[int]
    includes_personal_training: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_subscriptions_dates"),
        Index(
            "uq_subscriptions_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("membership_plans.id"))
    start_date: Mapped[date]
    end_date: Mapped[date | None]
    status: Mapped[SubscriptionStatus] = mapped_column(
        db_enum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE
    )

    user: Mapped["User"] = relationship()
    plan: Mapped["MembershipPlan"] = relationship()


class CancellationRequest(Base):
    __tablename__ = "cancellation_requests"
    __table_args__ = (
        Index(
            "uq_cancellation_requests_one_pending",
            "subscription_id",
            unique=True,
            sqlite_where=text("status = 'pending'"),
        ),
        CheckConstraint(
            "status != 'rejected' OR admin_notes IS NOT NULL",
            name="ck_cancellation_requests_rejected_notes",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CancellationStatus] = mapped_column(
        db_enum(CancellationStatus), default=CancellationStatus.PENDING
    )
    requested_at: Mapped[datetime] = mapped_column(default=utc_now)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None]
    admin_notes: Mapped[str | None] = mapped_column(Text)

    subscription: Mapped["Subscription"] = relationship()
    reviewer: Mapped[Optional["User"]] = relationship()