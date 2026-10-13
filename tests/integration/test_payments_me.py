"""Integration tests for GET /payments/me and POST /payments/{id}/pay (HU-24)."""
from datetime import date, datetime

import pytest
from freezegun import freeze_time
from sqlalchemy import select

from app.models import DiscountCode, MembershipPlan, Payment, Subscription
from app.models.enums import PaymentStatus, RoleName
from tests.conftest import auth_header_for

PAYMENTS_ME_URL = "/api/v1/payments/me"
TODAY = "2026-10-08"


def pay_url(payment_id: int) -> str:
    return f"/api/v1/payments/{payment_id}/pay"


def add_code(db, admin, **changes):
    data = {
        "code": "VERANO20",
        "percent_off": 20,
        "valid_from": date(2026, 10, 1),
        "valid_until": date(2026, 10, 31),
        "max_uses": 10,
        "is_active": True,
        **changes,
    }
    code = DiscountCode(**data, created_by=admin.id)
    db.add(code)
    db.commit()
    return code


def add_pending_payment(db, user, *, base_cents=5000, subscription=None):
    """Create a pending payment; reuse subscription to avoid RN-11 unique active conflict."""
    if subscription is None:
        plan = MembershipPlan(name=f"Plan {user.id}-{base_cents}-{id(user)}", monthly_price_cents=base_cents)
        subscription = Subscription(user=user, plan=plan, start_date=date(2026, 10, 1))
        db.add(subscription)
        db.flush()
    payment = Payment(
        user_id=user.id,
        subscription_id=subscription.id,
        base_amount_cents=base_cents,
        final_amount_cents=base_cents,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@freeze_time(TODAY)
def test_rn15_rn16_pay_pending_with_20_percent_code(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    add_code(db, make_user(RoleName.ADMIN), code="BRAVA20", percent_off=20)
    payment = add_pending_payment(db, member, base_cents=5000)

    response = client.post(
        pay_url(payment.id),
        json={"discount_code": "  brava20 "},
        headers=auth_header_for(member),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "paid"
    assert body["base_amount_cents"] == 5000
    assert body["final_amount_cents"] == 4000
    assert body["discount_code"] == "BRAVA20"
    assert body["concept"] == "subscription"
    assert body["paid_at"] == "2026-10-08T00:00:00"

    db.refresh(payment)
    assert payment.status == PaymentStatus.PAID
    assert payment.final_amount_cents == 4000


@freeze_time(TODAY)
def test_rn14_expired_or_exhausted_code_returns_422_and_leaves_payment(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    add_code(
        db,
        admin,
        code="CADUCADO",
        valid_from=date(2026, 9, 1),
        valid_until=date(2026, 9, 30),
    )
    exhausted = add_code(db, admin, code="AGOTADO", max_uses=1)
    other = make_user(RoleName.MEMBER)
    used = add_pending_payment(db, other)
    used.status = PaymentStatus.PAID
    used.paid_at = datetime(2026, 10, 2)
    used.discount_code_id = exhausted.id
    used.final_amount_cents = 4000
    db.commit()

    payment = add_pending_payment(db, member)
    headers = auth_header_for(member)

    expired = client.post(pay_url(payment.id), json={"discount_code": "CADUCADO"}, headers=headers)
    assert expired.status_code == 422

    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None

    used_up = client.post(pay_url(payment.id), json={"discount_code": "AGOTADO"}, headers=headers)
    assert used_up.status_code == 422

    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.discount_code_id is None


@freeze_time(TODAY)
def test_rn16_pay_already_paid_returns_409(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, member)
    first = client.post(pay_url(payment.id), json={}, headers=auth_header_for(member))
    assert first.status_code == 200

    second = client.post(pay_url(payment.id), json={}, headers=auth_header_for(member))

    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


def test_list_my_payments_only_own_and_filter_by_status(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    pending = add_pending_payment(db, member, base_cents=3900)
    paid = add_pending_payment(db, member, base_cents=5900, subscription=pending.subscription)
    paid.status = PaymentStatus.PAID
    paid.paid_at = datetime(2026, 10, 1)
    db.commit()
    add_pending_payment(db, other, base_cents=8900)

    headers = auth_header_for(member)
    all_mine = client.get(PAYMENTS_ME_URL, headers=headers)
    only_pending = client.get(f"{PAYMENTS_ME_URL}?status=pending", headers=headers)

    assert all_mine.status_code == 200
    assert all_mine.json()["total"] == 2
    assert {item["id"] for item in all_mine.json()["items"]} == {pending.id, paid.id}

    assert only_pending.status_code == 200
    assert only_pending.json()["total"] == 1
    assert only_pending.json()["items"][0]["id"] == pending.id
    assert only_pending.json()["items"][0]["status"] == "pending"


def test_pay_foreign_payment_returns_404(client, db, make_user):
    owner = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, owner)

    response = client.post(pay_url(payment.id), json={}, headers=auth_header_for(other))

    assert response.status_code == 404
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING


def test_pay_and_list_without_token_return_401(client, db, make_user):
    payment = add_pending_payment(db, make_user(RoleName.MEMBER))

    assert client.get(PAYMENTS_ME_URL).status_code == 401
    assert client.post(pay_url(payment.id), json={}).status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_list_and_pay(client, db, make_user, role):
    actor = make_user(role)
    member = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, member)
    headers = auth_header_for(actor)

    assert client.get(PAYMENTS_ME_URL, headers=headers).status_code == 403
    assert client.post(pay_url(payment.id), json={}, headers=headers).status_code == 403


@freeze_time(TODAY)
def test_pay_without_body_works(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, member, base_cents=5900)

    response = client.post(pay_url(payment.id), headers=auth_header_for(member))

    assert response.status_code == 200
    assert response.json()["final_amount_cents"] == 5900
    assert response.json()["discount_code"] is None


@freeze_time(TODAY)
def test_subscribe_then_pay_pending_fee(client, db, make_user, make_plan):
    """Happy path across HU-19 subscription + HU-24 pay."""
    member = make_user(RoleName.MEMBER)
    plan = make_plan(monthly_price_cents=5900)
    headers = auth_header_for(member)

    subscribed = client.post("/api/v1/subscriptions", json={"plan_id": plan.id}, headers=headers)
    assert subscribed.status_code == 201

    payment = db.scalar(select(Payment).where(Payment.user_id == member.id))
    assert payment is not None and payment.status == PaymentStatus.PENDING

    paid = client.post(pay_url(payment.id), json={}, headers=headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["final_amount_cents"] == 5900
