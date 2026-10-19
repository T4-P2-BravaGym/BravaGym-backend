"""Integration tests for admin GET /payments, /payments/export and POST …/refund (HU-26)."""

import csv
import io
from datetime import date, datetime

import pytest
from app.models import MembershipPlan, Order, Payment, Subscription
from app.models.enums import PaymentStatus, RoleName
from freezegun import freeze_time

from tests.conftest import auth_header_for

PAYMENTS_URL = "/api/v1/payments"
EXPORT_URL = "/api/v1/payments/export"
TODAY = "2026-10-08"


def refund_url(payment_id: int) -> str:
    return f"/api/v1/payments/{payment_id}/refund"


def add_subscription_payment(
    db,
    user,
    *,
    base_cents=5000,
    status=PaymentStatus.PENDING,
    paid_at=None,
    subscription=None,
    created_at=None,
):
    if subscription is None:
        plan = MembershipPlan(
            name=f"Plan {user.id}-{base_cents}-{id(user)}",
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
        status=status,
        paid_at=paid_at,
    )
    db.add(payment)
    db.flush()
    if created_at is not None:
        payment.created_at = created_at
    db.commit()
    db.refresh(payment)
    return payment


def add_order_payment(db, user, *, base_cents=2500, created_at=None):
    order = Order(user_id=user.id)
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
    db.flush()
    if created_at is not None:
        payment.created_at = created_at
    db.commit()
    db.refresh(payment)
    return payment


def test_admin_list_filters_by_status_and_dates(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    early = add_subscription_payment(
        db, member, base_cents=3900, created_at=datetime(2026, 10, 1, 8, 0, 0)
    )
    paid = add_subscription_payment(
        db,
        member,
        base_cents=5900,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 5),
        subscription=early.subscription,
        created_at=datetime(2026, 10, 5, 12, 0, 0),
    )
    headers = auth_header_for(admin)

    by_status = client.get(f"{PAYMENTS_URL}?status=paid", headers=headers)
    by_dates = client.get(
        f"{PAYMENTS_URL}?from=2026-10-05T00:00:00&to=2026-10-05T23:59:59",
        headers=headers,
    )

    assert by_status.status_code == 200
    assert by_status.json()["total"] == 1
    assert by_status.json()["items"][0]["id"] == paid.id
    assert by_status.json()["items"][0]["user_id"] == member.id

    assert by_dates.status_code == 200
    assert by_dates.json()["total"] == 1
    assert by_dates.json()["items"][0]["id"] == paid.id


def test_admin_list_filters_by_user_id_and_concept(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member_a = make_user(RoleName.MEMBER)
    member_b = make_user(RoleName.MEMBER)
    sub = add_subscription_payment(db, member_a, base_cents=3000)
    order = add_order_payment(db, member_b, base_cents=1500)
    headers = auth_header_for(admin)

    by_user = client.get(f"{PAYMENTS_URL}?user_id={member_a.id}", headers=headers)
    by_concept = client.get(f"{PAYMENTS_URL}?concept=order", headers=headers)

    assert by_user.status_code == 200
    assert by_user.json()["total"] == 1
    assert by_user.json()["items"][0]["id"] == sub.id

    assert by_concept.status_code == 200
    assert by_concept.json()["total"] == 1
    assert by_concept.json()["items"][0]["id"] == order.id
    assert by_concept.json()["items"][0]["concept"] == "order"


def test_admin_list_invalid_date_range_returns_422(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    response = client.get(
        f"{PAYMENTS_URL}?from=2026-10-10T00:00:00&to=2026-10-01T00:00:00",
        headers=auth_header_for(admin),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@freeze_time(TODAY)
def test_admin_refund_paid_returns_refunded_and_persists(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    payment = add_subscription_payment(
        db,
        member,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )

    response = client.post(refund_url(payment.id), headers=auth_header_for(admin))

    assert response.status_code == 200
    assert response.json()["status"] == "refunded"
    assert response.json()["id"] == payment.id
    db.refresh(payment)
    assert payment.status == PaymentStatus.REFUNDED


@freeze_time(TODAY)
def test_admin_refund_pending_returns_409(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    payment = add_subscription_payment(db, make_user(RoleName.MEMBER))

    response = client.post(refund_url(payment.id), headers=auth_header_for(admin))

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING


def test_admin_refund_unknown_returns_404(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    response = client.post(refund_url(999_999), headers=auth_header_for(admin))
    assert response.status_code == 404


def test_export_csv_has_header_and_filtered_rows(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    pending = add_subscription_payment(db, member, base_cents=1000)
    paid = add_subscription_payment(
        db,
        member,
        base_cents=2000,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 2),
        subscription=pending.subscription,
    )

    response = client.get(
        f"{EXPORT_URL}?status=paid",
        headers=auth_header_for(admin),
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "payments.csv" in response.headers.get("content-disposition", "")

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][0] == "id"
    assert "user_id" in rows[0]
    assert "final_amount_cents" in rows[0]
    assert len(rows) == 2
    assert rows[1][0] == str(paid.id)
    assert "paid" in rows[1]


def test_export_csv_same_filters_as_list(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member_a = make_user(RoleName.MEMBER)
    member_b = make_user(RoleName.MEMBER)
    add_subscription_payment(db, member_a, created_at=datetime(2026, 10, 3, 10, 0, 0))
    target = add_order_payment(
        db, member_b, base_cents=777, created_at=datetime(2026, 10, 4, 11, 0, 0)
    )
    headers = auth_header_for(admin)

    listed = client.get(
        f"{PAYMENTS_URL}?user_id={member_b.id}&concept=order",
        headers=headers,
    )
    exported = client.get(
        f"{EXPORT_URL}?user_id={member_b.id}&concept=order",
        headers=headers,
    )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == target.id

    rows = list(csv.reader(io.StringIO(exported.text)))
    assert len(rows) == 2
    assert rows[1][0] == str(target.id)
    assert rows[1][rows[0].index("concept")] == "order"
    assert rows[1][rows[0].index("user_id")] == str(member_b.id)


def test_admin_endpoints_without_token_return_401(client, db, make_user):
    payment = add_subscription_payment(
        db,
        make_user(RoleName.MEMBER),
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )
    assert client.get(PAYMENTS_URL).status_code == 401
    assert client.get(EXPORT_URL).status_code == 401
    assert client.post(refund_url(payment.id)).status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_admin_endpoints_forbidden_for_non_admin(client, db, make_user, role):
    actor = make_user(role)
    payment = add_subscription_payment(
        db,
        make_user(RoleName.MEMBER),
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )
    headers = auth_header_for(actor)

    assert client.get(PAYMENTS_URL, headers=headers).status_code == 403
    assert client.get(EXPORT_URL, headers=headers).status_code == 403
    assert client.post(refund_url(payment.id), headers=headers).status_code == 403


def test_superadmin_can_list_export_and_refund(client, db, make_user):
    superadmin = make_user(RoleName.SUPERADMIN)
    member = make_user(RoleName.MEMBER)
    payment = add_subscription_payment(
        db,
        member,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )
    headers = auth_header_for(superadmin)

    listed = client.get(PAYMENTS_URL, headers=headers)
    exported = client.get(EXPORT_URL, headers=headers)
    refunded = client.post(refund_url(payment.id), headers=headers)

    assert listed.status_code == 200
    assert exported.status_code == 200
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"
