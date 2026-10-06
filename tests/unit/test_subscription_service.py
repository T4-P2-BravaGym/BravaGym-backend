import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Payment, Subscription
from app.models.enums import SubscriptionStatus
from app.services import subscription_service


def count_rows(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_rn11_subscribe_twice_raises_conflict(db, make_user, make_plan):
    member = make_user()
    subscription_service.subscribe(db, user_id=member.id, plan_id=make_plan().id)

    with pytest.raises(ConflictError):
        subscription_service.subscribe(db, user_id=member.id, plan_id=make_plan().id)

    assert count_rows(db, Subscription) == 1
    assert count_rows(db, Payment) == 1


def test_rn11_simultaneous_request_stopped_by_the_unique_index_raises_conflict(
        db, make_user, make_plan, make_subscription, monkeypatch
):
    member = make_user()
    make_subscription(member, make_plan())
    real_check = subscription_service.get_active_subscription
    calls = []

    def stale_check(db_session, user_id):
        calls.append(user_id)
        return None if len(calls) == 1 else real_check(db_session, user_id)

    monkeypatch.setattr(subscription_service, "get_active_subscription", stale_check)

    with pytest.raises(ConflictError):
        subscription_service.subscribe(db, user_id=member.id, plan_id=make_plan().id)

    assert count_rows(db, Subscription) == 1
    assert count_rows(db, Payment) == 0


def test_subscribe_to_an_inactive_plan_raises_not_found(db, make_user, make_plan):
    member = make_user()
    retired_plan = make_plan(is_active=False)

    with pytest.raises(NotFoundError):
        subscription_service.subscribe(db, user_id=member.id, plan_id=retired_plan.id)

    assert count_rows(db, Subscription) == 0


def test_the_payment_amount_comes_from_the_plan(db, make_user, make_plan):
    member = make_user()
    plan = make_plan(monthly_price_cents=8900)

    subscription = subscription_service.subscribe(db, user_id=member.id, plan_id=plan.id)

    payment = db.scalar(select(Payment).where(Payment.subscription_id == subscription.id))
    assert payment.base_amount_cents == 8900
    assert payment.final_amount_cents == 8900


def test_get_active_subscription_ignores_cancelled_and_expired_ones(
        db, make_user, make_plan, make_subscription
):
    member = make_user()
    plan = make_plan()
    make_subscription(member, plan, status=SubscriptionStatus.CANCELLED)
    make_subscription(member, plan, status=SubscriptionStatus.EXPIRED)

    assert subscription_service.get_active_subscription(db, member.id) is None