"""Unit tests for cancellation requests (RN-12)."""

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ConflictError, NotFoundError
from app.models import CancellationRequest, User
from app.models.enums import CancellationStatus, SubscriptionStatus
from app.services import cancellation_service


def count_rows(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_rn12_create_pending_keeps_member_and_subscription_active(
        db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())

    request = cancellation_service.create_cancellation_request(
        db, user=member, reason="Me mudo de ciudad"
    )

    assert request.status == CancellationStatus.PENDING
    assert request.subscription_id == subscription.id
    assert request.reason == "Me mudo de ciudad"
    assert count_rows(db, CancellationRequest) == 1

    db.refresh(member)
    db.refresh(subscription)
    assert member.is_active is True
    assert member.deactivated_at is None
    assert subscription.status == SubscriptionStatus.ACTIVE


def test_rn12_second_pending_raises_conflict(db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())
    cancellation_service.create_cancellation_request(db, user=member, reason="Primera")

    with pytest.raises(ConflictError, match="pendiente"):
        cancellation_service.create_cancellation_request(db, user=member, reason="Segunda")

    assert count_rows(db, CancellationRequest) == 1


def test_rn12_simultaneous_request_stopped_by_unique_index_raises_conflict(
        db, make_user, make_plan, make_subscription, monkeypatch
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    real_check = cancellation_service.get_pending_for_subscription
    calls = []

    def stale_check(db_session, subscription_id):
        calls.append(subscription_id)
        return None if len(calls) == 1 else real_check(db_session, subscription_id)

    monkeypatch.setattr(cancellation_service, "get_pending_for_subscription", stale_check)

    # Seed a pending row as if a concurrent request already committed.
    db.add(
        CancellationRequest(
            subscription_id=subscription.id,
            reason="Concurrente",
            status=CancellationStatus.PENDING,
        )
    )
    db.commit()
    # First service check still returns None (stale), commit hits the unique index.
    with pytest.raises(ConflictError, match="pendiente"):
        cancellation_service.create_cancellation_request(db, user=member, reason="Otra")

    assert count_rows(db, CancellationRequest) == 1


def test_create_without_active_subscription_raises_not_found(db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan(), status=SubscriptionStatus.CANCELLED)

    with pytest.raises(NotFoundError, match="suscripción activa"):
        cancellation_service.create_cancellation_request(db, user=member, reason="Quiero irme")

    assert count_rows(db, CancellationRequest) == 0


def test_can_request_again_after_previous_was_rejected(
        db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    db.add(
        CancellationRequest(
            subscription_id=subscription.id,
            reason="Antes",
            status=CancellationStatus.REJECTED,
            admin_notes="Te esperamos",
        )
    )
    db.commit()

    request = cancellation_service.create_cancellation_request(
        db, user=member, reason="Otra vez"
    )

    assert request.status == CancellationStatus.PENDING
    assert count_rows(db, CancellationRequest) == 2


def test_get_my_cancellation_request_returns_latest(
        db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    older = CancellationRequest(
        subscription_id=subscription.id,
        reason="Antigua",
        status=CancellationStatus.REJECTED,
        admin_notes="No",
    )
    newer = CancellationRequest(
        subscription_id=subscription.id,
        reason="Nueva",
        status=CancellationStatus.PENDING,
    )
    db.add_all([older, newer])
    db.commit()

    found = cancellation_service.get_my_cancellation_request(db, user_id=member.id)

    assert found.id == newer.id
    assert found.reason == "Nueva"


def test_get_my_cancellation_request_raises_when_none(db, make_user):
    member = make_user()

    with pytest.raises(NotFoundError, match="solicitud de baja"):
        cancellation_service.get_my_cancellation_request(db, user_id=member.id)


def test_rn12_there_is_no_user_self_delete_in_the_service_layer(db, make_user):
    """RN-12: members cannot delete themselves; only a cancellation request exists."""
    member = make_user()
    assert not hasattr(cancellation_service, "delete_user")
    assert not hasattr(cancellation_service, "delete_me")
    db.refresh(member)
    assert isinstance(member, User)
    assert member.is_active is True
