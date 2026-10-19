"""RN-16: one immutable attempt, reconciled before cancellation or simulated pay."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import stripe
from app.core.exceptions import ConflictError, ServiceUnavailableError
from app.models import DiscountCode, PaymentCheckout
from app.models.enums import PaymentStatus
from app.models.types import utc_now
from app.services import stripe_service

from tests.conftest import auth_header_for
from tests.integration.test_stripe_checkout import add_pending_payment, enable_stripe


@pytest.fixture
def gateway(monkeypatch):
    enable_stripe(monkeypatch)
    session = SimpleNamespace(
        id="cs_test_consistent", url="https://checkout.stripe.com/test", status="open"
    )
    sessions = SimpleNamespace(
        create=Mock(return_value=session),
        retrieve=Mock(return_value=session),
        expire=Mock(return_value=SimpleNamespace(status="expired")),
    )
    monkeypatch.setattr(
        stripe_service,
        "_stripe_client",
        lambda: SimpleNamespace(
            v1=SimpleNamespace(checkout=SimpleNamespace(sessions=sessions))
        ),
    )
    return sessions


def event(payment, **changes):
    return SimpleNamespace(
        **{
            "id": "cs_test_consistent",
            "payment_status": "paid",
            "amount_total": payment.final_amount_cents,
            "currency": "eur",
            "metadata": {
                "payment_id": str(payment.id),
                "user_id": str(payment.user_id),
            },
            **changes,
        }
    )


def test_rn16_repeat_checkout_reuses_session_and_original_discount(
    db, make_user, gateway
):
    user = make_user()
    p = add_pending_payment(db, user)
    db.add(
        DiscountCode(
            code="HALF",
            percent_off=50,
            valid_from=date.today() - timedelta(days=1),
            valid_until=date.today() + timedelta(days=1),
            created_by=user.id,
            is_active=True,
        )
    )
    db.commit()
    first = stripe_service.create_checkout_session(db, user, p.id, "HALF")
    second = stripe_service.create_checkout_session(db, user, p.id)
    assert first == second
    assert gateway.create.call_count == 1
    assert p.final_amount_cents == 2500
    stripe_service.fulfill_checkout_session(db, event(p))
    assert p.final_amount_cents == 2500 and p.status == PaymentStatus.PAID


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_total": 1},
        {"currency": "usd"},
        {"id": "cs_other"},
        {"metadata": {"payment_id": "1", "user_id": "999"}},
    ],
)
def test_rn16_reject_mismatched_session_without_fulfilling(
    db, make_user, gateway, changes
):
    user = make_user()
    p = add_pending_payment(db, user)
    stripe_service.create_checkout_session(db, user, p.id)
    with pytest.raises(ConflictError):
        stripe_service.fulfill_checkout_session(db, event(p, **changes))
    assert p.status == PaymentStatus.PENDING


def test_rn16_network_retry_uses_persisted_key_and_payload(db, make_user, gateway):
    user = make_user()
    p = add_pending_payment(db, user)
    response = gateway.create.return_value
    gateway.create.side_effect = [stripe.APIConnectionError("test timeout"), response]
    with pytest.raises(ServiceUnavailableError):
        stripe_service.create_checkout_session(db, user, p.id)
    attempt = db.get(PaymentCheckout, p.id)
    assert attempt and attempt.session_id is None
    stripe_service.create_checkout_session(db, user, p.id)
    assert gateway.create.call_args_list[0] == gateway.create.call_args_list[1]


def test_rn16_unknown_old_attempt_never_reuses_pruned_key(db, make_user, gateway):
    user = make_user()
    p = add_pending_payment(db, user)
    gateway.create.side_effect = stripe.APIConnectionError("timeout")
    with pytest.raises(ServiceUnavailableError):
        stripe_service.create_checkout_session(db, user, p.id)
    db.get(PaymentCheckout, p.id).created_at = utc_now() - timedelta(days=2)
    db.commit()
    with pytest.raises(ServiceUnavailableError):
        stripe_service.create_checkout_session(db, user, p.id)
    assert gateway.create.call_count == 1


@pytest.mark.parametrize("remote_status,allowed", [("open", True), ("complete", False)])
def test_rn16_cancel_order_expires_checkout_before_restoring_stock(
    client, db, make_user, make_product, gateway, remote_status, allowed
):
    user = make_user()
    h = auth_header_for(user)
    product = make_product(stock=1)
    order = client.post(
        "/api/v1/orders",
        headers=h,
        json={"items": [{"product_id": product.id, "quantity": 1}]},
    ).json()
    from app.models import Payment
    from sqlalchemy import select

    p = db.scalar(select(Payment).where(Payment.order_id == order["id"]))
    stripe_service.create_checkout_session(db, user, p.id)
    gateway.retrieve.return_value.status = remote_status
    response = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)
    assert response.status_code == (200 if allowed else 409)
    db.refresh(product)
    db.refresh(p)
    assert product.stock == (1 if allowed else 0)
    assert p.status == (PaymentStatus.CANCELLED if allowed else PaymentStatus.PENDING)
    assert gateway.expire.call_count == (1 if allowed else 0)


def test_rn16_simulated_pay_does_not_race_completed_checkout(
    client, db, make_user, gateway
):
    user = make_user()
    p = add_pending_payment(db, user)
    stripe_service.create_checkout_session(db, user, p.id)
    gateway.retrieve.return_value.status = "complete"
    response = client.post(
        f"/api/v1/payments/{p.id}/pay", headers=auth_header_for(user), json={}
    )
    assert response.status_code == 409
    assert p.status == PaymentStatus.PENDING


def test_rn16_expiration_releases_attempt_and_stale_expiration_is_ignored(
    db, make_user, gateway
):
    user = make_user()
    p = add_pending_payment(db, user)
    stripe_service.create_checkout_session(db, user, p.id)
    stripe_service.handle_webhook_event(
        db,
        {"type": "checkout.session.expired", "data": {"object": event(p, id="other")}},
    )
    assert db.get(PaymentCheckout, p.id)
    stripe_service.handle_webhook_event(
        db, {"type": "checkout.session.expired", "data": {"object": event(p)}}
    )
    assert db.get(PaymentCheckout, p.id) is None
    assert p.status == PaymentStatus.PENDING


def test_rn16_second_paid_session_is_not_an_idempotent_replay(db, make_user, gateway):
    user = make_user()
    p = add_pending_payment(db, user)
    stripe_service.create_checkout_session(db, user, p.id)
    stripe_service.fulfill_checkout_session(db, event(p))
    with pytest.raises(ConflictError):
        stripe_service.fulfill_checkout_session(db, event(p, id="cs_other_charge"))
    assert p.provider_ref == "cs_test_consistent"


def test_rn16_concurrent_checkout_requests_share_durable_idempotency_key(
    tmp_path, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Lock

    from app.core.database import Base
    from app.models import Payment, Role, User
    from app.models.enums import RoleName
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session

    enable_stripe(monkeypatch)
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        user = User(
            email="concurrency@example.com",
            first_name="Test",
            last_name="Member",
            password_hash="not-used",
            role=Role(name=RoleName.MEMBER),
        )
        db.add(user)
        db.commit()
        p = add_pending_payment(db, user)
        user_id, payment_id = user.id, p.id
    barrier = Barrier(2)
    keys = []
    mutex = Lock()

    def create(params, options):
        with mutex:
            keys.append(options["idempotency_key"])
        barrier.wait(timeout=10)
        return SimpleNamespace(
            id="cs_concurrent", url="https://checkout.stripe.com/concurrent"
        )

    monkeypatch.setattr(
        stripe_service,
        "_stripe_client",
        lambda: SimpleNamespace(
            v1=SimpleNamespace(
                checkout=SimpleNamespace(sessions=SimpleNamespace(create=create))
            )
        ),
    )

    def run():
        with Session(engine) as db:
            return stripe_service.create_checkout_session(
                db, db.get(User, user_id), payment_id
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        assert results[0] == results[1]
        assert len(keys) == 2 and len(set(keys)) == 1
        with Session(engine) as db:
            assert db.scalar(select(func.count()).select_from(PaymentCheckout)) == 1
            assert db.get(Payment, payment_id).status == PaymentStatus.PENDING
    finally:
        engine.dispose()


def test_rn16_expire_failure_preserves_pending_order_and_stock(
    client, db, make_user, make_product, gateway
):
    from app.models import Payment
    from sqlalchemy import select

    user = make_user()
    h = auth_header_for(user)
    product = make_product(stock=1)
    order = client.post(
        "/api/v1/orders",
        headers=h,
        json={"items": [{"product_id": product.id, "quantity": 1}]},
    ).json()
    p = db.scalar(select(Payment).where(Payment.order_id == order["id"]))
    stripe_service.create_checkout_session(db, user, p.id)
    gateway.expire.side_effect = stripe.APIConnectionError("uncertain expiration")
    response = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=h)
    assert response.status_code == 503
    db.refresh(product)
    db.refresh(p)
    assert product.stock == 0 and p.status == PaymentStatus.PENDING
    assert db.get(PaymentCheckout, p.id) is not None
