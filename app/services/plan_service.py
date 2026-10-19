"""Membership plans; delete = deactivate."""

import logging

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import PLANS_CACHE_KEY, invalidate_plans_cache, response_cache
from app.core.exceptions import ConflictError, NotFoundError
from app.models.membership import MembershipPlan
from app.schemas.plan import PlanCreate, PlanOut, PlanUpdate

logger = logging.getLogger(__name__)


def list_active_plans(db: Session) -> list[PlanOut]:
    """Public pricing list; served from an in-memory TTL cache when possible (HU-28)."""
    cached = response_cache.get(PLANS_CACHE_KEY)
    if cached is not None:
        return [PlanOut.model_validate(item) for item in cached]

    query = (
        select(MembershipPlan)
        .where(MembershipPlan.is_active.is_(True))
        .order_by(MembershipPlan.monthly_price_cents)
    )
    plans = [PlanOut.model_validate(plan) for plan in db.scalars(query).all()]
    response_cache.set(PLANS_CACHE_KEY, [plan.model_dump(mode="json") for plan in plans])
    return plans


def list_admin_plans(db: Session, *, page: int = 1, size: int = 20):
    """List active and retired plans, with active plans first."""
    total = db.scalar(select(func.count(MembershipPlan.id))) or 0
    query = (
        select(MembershipPlan)
        .order_by(MembershipPlan.is_active.desc(), MembershipPlan.monthly_price_cents, MembershipPlan.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(query).all()), total


def create_plan(db: Session, data: PlanCreate) -> MembershipPlan:
    """Create a plan; reject a name that already exists."""
    existing = db.scalar(
        select(MembershipPlan).where(MembershipPlan.name == data.name)
    )

    if existing is not None:
        raise ConflictError("Ya existe un plan con ese nombre.")

    plan = MembershipPlan(**data.model_dump())
    db.add(plan)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Ya existe un plan con ese nombre.") from None

    db.refresh(plan)
    invalidate_plans_cache()
    logger.info("Membership plan %s created", plan.id)
    return plan


def update_plan(
    db: Session, plan_id: int, changes: PlanUpdate
) -> MembershipPlan:
    """Update only the fields supplied for an existing plan."""
    plan = db.get(MembershipPlan, plan_id)

    if plan is None:
        raise NotFoundError("No se ha encontrado el plan.")

    data = changes.model_dump(exclude_unset=True)

    if "name" in data:
        existing = db.scalar(
            select(MembershipPlan).where(
                MembershipPlan.name == data["name"],
                MembershipPlan.id != plan_id,
            )
        )

        if existing is not None:
            raise ConflictError("Ya existe un plan con ese nombre.")

    for field, value in data.items():
        setattr(plan, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Ya existe un plan con ese nombre.") from None

    db.refresh(plan)
    invalidate_plans_cache()
    logger.info("Membership plan %s updated", plan.id)
    return plan


def deactivate_plan(db: Session, plan_id: int) -> MembershipPlan:
    """Deactivate a plan without deleting it or changing subscriptions."""
    plan = db.get(MembershipPlan, plan_id)

    if plan is None:
        raise NotFoundError("No se ha encontrado el plan.")

    plan.is_active = False
    db.commit()
    db.refresh(plan)
    invalidate_plans_cache()

    logger.info("Membership plan %s deactivated", plan.id)
    return plan
