"""Unit tests for Stripe Checkout helpers (HU-29 / #123)."""

from datetime import date
from types import SimpleNamespace

import pytest
from app.models import MembershipPlan, Payment, Subscription
from app.models.enums import PaymentMethod, PaymentStatus, RoleName
from app.core.exceptions import ConflictError, ServiceUnavailableError
from app.services import payment_service, stripe_service


class _FakeSession:
    def __init__(self, *, session_id="cs_test_abc", url="https://checkout.stripe.com/pay/cs_test_abc"):
        self.id = session_id
        self.url = url


class _FakeSessions:
    last_params = None

    def create(self, params=None, options=None):
        type(self).last_params = params
        return _FakeSession()


class _FakeClient:
    def __init__(self):
        self.v1 = SimpleNamespace(
            checkout=SimpleNamespace(sessions=_FakeSessions())
        )


def _pending_payment(db, user, *, base_cents=5000):
    plan = MembershipPlan(name=f"Plan-{user.id}-{base_cents}", monthly_price_cents=base_cents)
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


def test_stripe_disabled_raises_503(monkeypatch):
    monkeypatch.setattr(
        stripe_service,
        "get_settings",
        lambda: SimpleNamespace(stripe_enabled=False, stripe_secret_key=None),
    )
    with pytest.raises(ServiceUnavailableError):
        stripe_service._require_stripe_secret()


def test_create_checkout_session_builds_line_item(db, make_user, monkeypatch):
    member = make_user(RoleName.MEMBER)
    payment = _pending_payment(db, member, base_cents=5900)
    _FakeSessions.last_params = None

    monkeypatch.setattr(stripe_service, "_require_stripe_secret", lambda: "sk_test_fake")
    monkeypatch.setattr(
        stripe_service,
        "get_settings",
        lambda: SimpleNamespace(
            stripe_enabled=True,
            stripe_secret_key="sk_test_fake",
            stripe_success_url="http://localhost/ok",
            stripe_cancel_url="http://localhost/cancel",
        ),
    )
    monkeypatch.setattr(stripe_service, "_stripe_client", lambda: _FakeClient())

    result = stripe_service.create_checkout_session(db, member, payment.id)

    assert result.session_id == "cs_test_abc"
    assert "checkout.stripe.com" in result.checkout_url
    params = _FakeSessions.last_params
    assert params["mode"] == "payment"
    assert params["metadata"]["payment_id"] == str(payment.id)
    assert params["line_items"][0]["price_data"]["unit_amount"] == 5900
    assert params["line_items"][0]["price_data"]["currency"] == "eur"


def test_create_checkout_non_pending_raises_409(db, make_user, monkeypatch):
    member = make_user(RoleName.MEMBER)
    payment = _pending_payment(db, member)
    payment.status = PaymentStatus.PAID
    payment.paid_at = payment.created_at
    db.commit()

    monkeypatch.setattr(stripe_service, "_require_stripe_secret", lambda: "sk_test_fake")
    monkeypatch.setattr(
        stripe_service,
        "get_settings",
        lambda: SimpleNamespace(
            stripe_enabled=True,
            stripe_secret_key="sk_test_fake",
            stripe_success_url="http://localhost/ok",
            stripe_cancel_url="http://localhost/cancel",
        ),
    )

    with pytest.raises(ConflictError):
        stripe_service.create_checkout_session(db, member, payment.id)


def test_fulfill_checkout_marks_paid_and_idempotent(db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = _pending_payment(db, member, base_cents=4000)

    session = SimpleNamespace(
        id="cs_test_paid",
        payment_status="paid",
        metadata={"payment_id": str(payment.id), "user_id": str(member.id)},
        client_reference_id=str(payment.id),
    )

    updated = stripe_service.fulfill_checkout_session(db, session)
    assert updated is not None
    assert updated.status == PaymentStatus.PAID
    assert updated.method == PaymentMethod.STRIPE
    assert updated.provider_ref == "cs_test_paid"

    again = stripe_service.fulfill_checkout_session(db, session)
    assert again.status == PaymentStatus.PAID
    assert again.provider_ref == "cs_test_paid"


def test_fulfill_skips_when_not_paid_yet(db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = _pending_payment(db, member)
    session = SimpleNamespace(
        id="cs_test_unpaid",
        payment_status="unpaid",
        metadata={"payment_id": str(payment.id)},
        client_reference_id=str(payment.id),
    )
    assert stripe_service.fulfill_checkout_session(db, session) is None
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING


def test_apply_discount_shared_with_pay(db, make_user):
    """Checkout and simulated pay share RN-15 rounding via apply_optional_discount."""
    from app.models import DiscountCode

    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    payment = _pending_payment(db, member, base_cents=5000)
    code = DiscountCode(
        code="BRAVA20",
        percent_off=20,
        valid_from=date(2026, 10, 1),
        valid_until=date(2026, 12, 31),
        max_uses=10,
        is_active=True,
        created_by=admin.id,
    )
    db.add(code)
    db.commit()

    payment_service.apply_optional_discount(db, payment, "brava20")
    assert payment.final_amount_cents == 4000
    assert payment.discount_code_id == code.id
