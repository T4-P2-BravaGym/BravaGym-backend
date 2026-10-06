from datetime import date

import pytest
from freezegun import freeze_time
from sqlalchemy import func, select

from app.models import Payment, Subscription
from app.models.enums import PaymentMethod, PaymentStatus, RoleName, SubscriptionStatus
from tests.conftest import auth_header_for

SUBSCRIPTIONS_URL = "/api/v1/subscriptions"
MY_SUBSCRIPTIONS_URL = "/api/v1/subscriptions/me"


def count_rows(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


@freeze_time("2026-10-06 10:00:00")
def test_rn11_member_without_subscription_gets_an_active_one_and_a_pending_payment(
        client, db, make_user, make_plan
):
    member = make_user()
    plan = make_plan(monthly_price_cents=5900)

    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": plan.id}, headers=auth_header_for(member))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["start_date"] == "2026-10-06"
    assert body["end_date"] is None
    assert body["plan"] == {
        "id": plan.id,
        "name": plan.name,
        "monthly_price_cents": 5900,
        "includes_personal_training": False,
    }

    payment = db.scalar(select(Payment).where(Payment.subscription_id == body["id"]))
    assert payment.user_id == member.id
    assert payment.status == PaymentStatus.PENDING
    assert payment.method == PaymentMethod.SIMULATED
    assert payment.base_amount_cents == 5900
    assert payment.final_amount_cents == 5900
    assert payment.paid_at is None


def test_rn11_member_with_an_active_subscription_gets_409_and_nothing_changes(
        client, db, make_user, make_plan
):
    member = make_user()
    headers = auth_header_for(member)
    first = client.post(SUBSCRIPTIONS_URL, json={"plan_id": make_plan().id}, headers=headers)

    second = client.post(SUBSCRIPTIONS_URL, json={"plan_id": make_plan().id}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "Ya tienes una suscripción activa.", "code": "conflict"}
    assert count_rows(db, Subscription) == 1
    assert count_rows(db, Payment) == 1


def test_rn11_member_can_subscribe_again_after_a_cancelled_subscription(
        client, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan(), status=SubscriptionStatus.CANCELLED)

    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": make_plan().id}, headers=auth_header_for(member))

    assert response.status_code == 201


def test_subscribing_to_an_inactive_plan_returns_404(client, db, make_user, make_plan):
    member = make_user()
    retired_plan = make_plan(is_active=False)

    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": retired_plan.id}, headers=auth_header_for(member))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert count_rows(db, Subscription) == 0


def test_subscribing_to_a_plan_that_does_not_exist_returns_404(client, auth_headers):
    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": 9999}, headers=auth_headers())

    assert response.status_code == 404


def test_subscribe_without_token_returns_401(client, make_plan):
    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": make_plan().id})

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_subscribe(client, db, auth_headers, make_plan, role):
    response = client.post(SUBSCRIPTIONS_URL, json={"plan_id": make_plan().id}, headers=auth_headers(role))

    assert response.status_code == 403
    assert count_rows(db, Subscription) == 0


def test_a_price_sent_by_the_client_is_rejected(client, db, auth_headers, make_plan):
    body = {"plan_id": make_plan().id, "monthly_price_cents": 1}

    response = client.post(SUBSCRIPTIONS_URL, json=body, headers=auth_headers())

    assert response.status_code == 422
    assert count_rows(db, Subscription) == 0


@pytest.mark.parametrize("body", [{}, {"plan_id": 0}, {"plan_id": -3}, {"plan_id": "abc"}])
def test_malformed_body_returns_422(client, auth_headers, body):
    response = client.post(SUBSCRIPTIONS_URL, json=body, headers=auth_headers())

    assert response.status_code == 422


def test_member_without_subscriptions_gets_an_empty_result(client, auth_headers):
    response = client.get(MY_SUBSCRIPTIONS_URL, headers=auth_headers())

    assert response.status_code == 200
    assert response.json() == {"current": None, "history": []}


def test_member_sees_her_current_subscription_and_her_history_newest_first(
        client, make_user, make_plan, make_subscription
):
    member = make_user()
    plan = make_plan()
    oldest = make_subscription(member, plan, status=SubscriptionStatus.EXPIRED, start_date=date(2026, 6, 1))
    cancelled = make_subscription(member, plan, status=SubscriptionStatus.CANCELLED, start_date=date(2026, 8, 1))
    active = make_subscription(member, plan, start_date=date(2026, 9, 1))

    response = client.get(MY_SUBSCRIPTIONS_URL, headers=auth_header_for(member))

    body = response.json()
    assert body["current"]["id"] == active.id
    assert body["current"]["plan"]["id"] == plan.id
    assert [item["id"] for item in body["history"]] == [cancelled.id, oldest.id]


def test_member_never_sees_subscriptions_of_another_member(
        client, make_user, make_plan, make_subscription
):
    other_member = make_user()
    make_subscription(other_member, make_plan())
    member = make_user()

    response = client.get(MY_SUBSCRIPTIONS_URL, headers=auth_header_for(member))

    assert response.json() == {"current": None, "history": []}


def test_my_subscriptions_without_token_returns_401(client):
    response = client.get(MY_SUBSCRIPTIONS_URL)

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_have_subscriptions(client, auth_headers, role):
    response = client.get(MY_SUBSCRIPTIONS_URL, headers=auth_headers(role))

    assert response.status_code == 403