"""Membership plan queries.

TODO(HU-08): create, update and deactivate plans.
"""


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.membership import MembershipPlan



def list_active_plans(db: Session) -> list[MembershipPlan]:
    query = (
        select(MembershipPlan)
        .where(MembershipPlan.is_active.is_(True))
        .order_by(MembershipPlan.monthly_price_cents)
    )

    return list(db.scalars(query).all())
