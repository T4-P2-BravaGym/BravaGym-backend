"""Integration tests for Stripe Checkout + webhook (HU-29 / #121–#123)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import date
from types import SimpleNamespace

import pytest
from app.core.config import get_settings
from app.models import DiscountCode, MembershipPlan, Order, Payment, Subscription
from app.models.enums import OrderStatus, PaymentMethod, PaymentStatus, RoleName
from freezegun import freeze_time

from tests.conftest import auth_header_for

TODAY = "2026-10-08"
CHECKOUT_URL = "/api/v1/payments/{payment_id}/checkout"
WEBHOOK_URL = "/api/v1/webhooks/stripe"
WEBHOOK_SECRET = "whsec_test_brava_secret"


def checkout_url(payment_id: int) -> str:
    return CHECKOUT_URL.format(payment_id=payment_id)


def add_pending_payment(db, user, *, base_cents=5000):
    plan = MembershipPlan(
        name=f"StripePlan-{user.id}-{base_cents}",
        monthly_price_cents=base_cents,
    )
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


def add_order_payment(db, user, *, base_cents=2500):
    order = Order(user_id=user.id, status=OrderStatus.PENDING)
    db.add(order)
    db.flush()
    payment = Payment(
        user_id=user.id,
        order_id=order.id,
        base_amount_cents=base_cents,
        final_amount_cents=base_cents,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.refresh(order)
    return payment, order


def enable_stripe(monkeypatch, *, secret="sk_test_fake", webhook=WEBHOOK_SECRET):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", secret)
    monkeypatch.setattr(settings, "stripe_publishable_key", "pk_test_fake")
    monkeypatch.setattr(settings, "stripe_webhook_secret", webhook)
    monkeypatch.setattr(
        settings, "stripe_success_url", "http://localhost:5173/ok"
    )
    monkeypatch.setattr(
        settings, "stripe_cancel_url", "http://localhost:5173/cancel"
    )


def sign_payload(payload: bytes, secret: str = WEBHOOK_SECRET) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.{payload.decode('utf-8')}"
    digest = hmac.new(
        secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


class _FakeSession:
    id = "cs_test_integration"
    url = "https://checkout.stripe.com/c/pay/cs_test_integration"


class _FakeSessions:
    last_params = None

    def create(self, params=None, options=None):
        type(self).last_params = params
        return _FakeSession()


@pytest.fixture
def fake_stripe_client(monkeypatch):
    from app.services import stripe_service

    client = SimpleNamespace(
        v1=SimpleNamespace(checkout=SimpleNamespace(sessions=_FakeSessions()))
    )
    monkeypatch.setattr(stripe_service, "_stripe_client", lambda: client)
    _FakeSessions.last_params = None
    return client


@freeze_time(TODAY)
def test_checkout_without_stripe_keys_returns_503(client, db, make_user, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", None)
    member = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, member)

    response = client.post(
        checkout_url(payment.id),
        headers=auth_header_for(member),
    )

    assert response.status_code == 503
    assert "Stripe" in response.json()["detail"]
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING


@freeze_time(TODAY)
def test_simulated_pay_still_works_without_stripe(client, db, make_user, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "stripe_secret_key", None)
    member = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, member)

    response = client.post(
        f"/api/v1/payments/{payment.id}/pay",
        headers=auth_header_for(member),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"
    assert response.json()["method"] == "simulated"


@freeze_time(TODAY)
def test_checkout_creates_session_with_discount(
    client, db, make_user, monkeypatch, fake_stripe_client
):
    enable_stripe(monkeypatch)
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    payment = add_pending_payment(db, member, base_cents=5000)
    db.add(
        DiscountCode(
            code="BRAVA20",
            percent_off=20,
            valid_from=date(2026, 10, 1),
            valid_until=date(2026, 10, 31),
            max_uses=10,
            is_active=True,
            created_by=admin.id,
        )
    )
    db.commit()

    response = client.post(
        checkout_url(payment.id),
        json={"discount_code": "brava20"},
        headers=auth_header_for(member),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "cs_test_integration"
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")
    assert _FakeSessions.last_params["line_items"][0]["price_data"]["unit_amount"] == 4000
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.final_amount_cents == 4000


@freeze_time(TODAY)
def test_webhook_invalid_signature_returns_400(client, db, make_user, monkeypatch):
    enable_stripe(monkeypatch)
    payload = b'{"id":"evt_1","type":"checkout.session.completed","data":{"object":{}}}'

    response = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=deadbeef", "Content-Type": "application/json"},
    )

    assert response.status_code == 400


@freeze_time(TODAY)
def test_webhook_marks_payment_paid_and_order(
    client, db, make_user, monkeypatch
):
    enable_stripe(monkeypatch)
    member = make_user(RoleName.MEMBER)
    payment, order = add_order_payment(db, member, base_cents=2500)

    session_obj = {
        "id": "cs_test_webhook_1",
        "object": "checkout.session",
        "payment_status": "paid",
        "client_reference_id": str(payment.id),
        "metadata": {"payment_id": str(payment.id), "user_id": str(member.id)},
    }
    event = {
        "id": "evt_test_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": session_obj},
    }
    payload = json.dumps(event).encode("utf-8")
    signature = sign_payload(payload)

    response = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={
            "Stripe-Signature": signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"received": True}
    db.refresh(payment)
    db.refresh(order)
    assert payment.status == PaymentStatus.PAID
    assert payment.method == PaymentMethod.STRIPE
    assert payment.provider_ref == "cs_test_webhook_1"
    assert payment.paid_at is not None
    assert order.status == OrderStatus.PAID

    # Idempotent replay
    response2 = client.post(
        WEBHOOK_URL,
        content=payload,
        headers={
            "Stripe-Signature": sign_payload(payload),
            "Content-Type": "application/json",
        },
    )
    assert response2.status_code == 200
    db.refresh(payment)
    assert payment.status == PaymentStatus.PAID


@freeze_time(TODAY)
def test_checkout_foreign_payment_404(
    client, db, make_user, monkeypatch, fake_stripe_client
):
    enable_stripe(monkeypatch)
    owner = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    payment = add_pending_payment(db, owner)

    response = client.post(
        checkout_url(payment.id),
        headers=auth_header_for(other),
    )
    assert response.status_code == 404
