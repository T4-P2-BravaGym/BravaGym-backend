import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ConflictError, NotFoundError
from app.models import MembershipPlan, Payment, Subscription
from app.models.enums import PaymentStatus, SubscriptionStatus
from app.models.types import utc_now

logger = logging.getLogger(__name__)

PLAN_NOT_AVAILABLE = "Este plan no existe o ya no está disponible."
ALREADY_SUBSCRIBED = "Ya tienes una suscripción activa."


def get_active_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.status == SubscriptionStatus.ACTIVE)
    )


def get_my_subscriptions(db: Session, user_id: int) -> tuple[Subscription | None, list[Subscription]]:
    subscriptions = db.scalars(
        select(Subscription)
        .options(joinedload(Subscription.plan))
        .where(Subscription.user_id == user_id)
        .order_by(Subscription.start_date.desc(), Subscription.id.desc())
    ).all()

    current = next((s for s in subscriptions if s.status == SubscriptionStatus.ACTIVE), None)
    history = [s for s in subscriptions if s is not current]
    return current, history


def subscribe(db: Session, user_id: int, plan_id: int) -> Subscription:
    plan = db.get(MembershipPlan, plan_id)
    if plan is None or not plan.is_active:
        raise NotFoundError(PLAN_NOT_AVAILABLE)

    if get_active_subscription(db, user_id) is not None:
        raise ConflictError(ALREADY_SUBSCRIBED)

    subscription = Subscription(
        user_id=user_id,
        plan=plan,
        start_date=utc_now().date(),
        status=SubscriptionStatus.ACTIVE,
    )
    payment = Payment(
        user_id=user_id,
        subscription=subscription,
        base_amount_cents=plan.monthly_price_cents,
        final_amount_cents=plan.monthly_price_cents,
        status=PaymentStatus.PENDING,
    )
    db.add_all([subscription, payment])

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if get_active_subscription(db, user_id) is None:
            raise
        logger.info("Blocked a second active subscription for user %s", user_id)
        raise ConflictError(ALREADY_SUBSCRIBED) from None

    logger.info(
        "User %s subscribed to plan %s (subscription %s, pending payment %s)",
        user_id,
        plan.id,
        subscription.id,
        payment.id,
    )
    return subscription