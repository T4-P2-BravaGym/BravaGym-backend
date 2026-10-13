"""Unit tests for member payments (HU-24) and admin list/export/refund (HU-26, RN-14 to RN-16)."""
import csv
import io
from datetime import date, datetime

import pytest
from freezegun import freeze_time

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import DiscountCode, MembershipPlan, Order, Payment, Subscription
from app.models.enums import PaymentStatus, RoleName
from app.services import payment_service

TODAY = "2026-10-08"


def _add_subscription_payment(
    db,
    user,
    *,
    base_cents=5000,
    status=PaymentStatus.PENDING,
    paid_at=None,
    subscription=None,
):
    """Attach a payment to an existing subscription, or create one active subscription."""
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
        status=status,
        paid_at=paid_at,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def _add_code(db, admin, **changes):
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


@pytest.mark.parametrize(
    ("base", "percent", "expected"),
    [
        (5000, 20, 4000),
        (5900, 20, 4720),
        (1000, 100, 0),
        (1001, 15, 851),  # 1001 * 85 / 100 = 850.85 → 851 (half up)
        (1000, 33, 670),  # 1000 * 67 / 100 = 670 exact
        (3, 50, 2),  # 1.5 → 2
    ],
)
def test_rn15_discount_rounds_to_nearest_cent(base, percent, expected):
    assert payment_service.apply_discount_cents(base, percent) == expected


@freeze_time(TODAY)
def test_rn16_pay_pending_without_code_marks_paid_at_full_amount(db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = _add_subscription_payment(db, member, base_cents=5900)

    result = payment_service.pay_payment(db, member, payment.id)

    assert result.status == PaymentStatus.PAID
    assert result.final_amount_cents == 5900
    assert result.discount_code_id is None
    assert result.paid_at == datetime(2026, 10, 8)


@freeze_time(TODAY)
def test_rn15_rn16_pay_with_20_percent_code_sets_80_percent(db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    _add_code(db, admin, code="OFF20", percent_off=20)
    payment = _add_subscription_payment(db, member, base_cents=5000)

    result = payment_service.pay_payment(db, member, payment.id, discount_code_text="off20")

    assert result.status == PaymentStatus.PAID
    assert result.base_amount_cents == 5000
    assert result.final_amount_cents == 4000
    assert result.discount_code is not None
    assert result.discount_code.code == "OFF20"


@freeze_time(TODAY)
def test_rn14_expired_code_returns_422_and_payment_stays_pending(db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    _add_code(
        db,
        admin,
        code="OLD",
        valid_from=date(2026, 9, 1),
        valid_until=date(2026, 9, 30),
    )
    payment = _add_subscription_payment(db, member)

    with pytest.raises(ValidationAppError):
        payment_service.pay_payment(db, member, payment.id, discount_code_text="OLD")

    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.final_amount_cents == payment.base_amount_cents
    assert payment.discount_code_id is None
    assert payment.paid_at is None


@freeze_time(TODAY)
def test_rn14_exhausted_code_returns_422_and_payment_stays_pending(db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    code = _add_code(db, admin, code="ONCE", max_uses=1)
    other = make_user(RoleName.MEMBER)
    used = _add_subscription_payment(
        db,
        other,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 2),
    )
    used.discount_code_id = code.id
    used.final_amount_cents = 4000
    db.commit()

    payment = _add_subscription_payment(db, member)

    with pytest.raises(ValidationAppError):
        payment_service.pay_payment(db, member, payment.id, discount_code_text="ONCE")

    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.paid_at is None


@freeze_time(TODAY)
def test_rn16_pay_already_paid_returns_409(db, make_user):
    member = make_user(RoleName.MEMBER)
    payment = _add_subscription_payment(
        db,
        member,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )

    with pytest.raises(ConflictError, match="pendiente"):
        payment_service.pay_payment(db, member, payment.id)


def test_pay_unknown_or_foreign_payment_returns_404(db, make_user):
    owner = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    payment = _add_subscription_payment(db, owner)

    with pytest.raises(NotFoundError):
        payment_service.pay_payment(db, other, payment.id)

    with pytest.raises(NotFoundError):
        payment_service.pay_payment(db, owner, payment_id=999_999)


def test_list_my_payments_filters_by_status_and_excludes_others(db, make_user):
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    pending = _add_subscription_payment(db, member, base_cents=3900)
    paid = _add_subscription_payment(
        db,
        member,
        base_cents=5900,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
        subscription=pending.subscription,
    )
    _add_subscription_payment(db, other, base_cents=8900)

    all_mine, total_all = payment_service.list_my_payments(db, user_id=member.id)
    only_pending, total_pending = payment_service.list_my_payments(
        db, user_id=member.id, status=PaymentStatus.PENDING
    )

    assert total_all == 2
    assert {p.id for p in all_mine} == {pending.id, paid.id}
    assert total_pending == 1
    assert only_pending[0].id == pending.id


def _add_order_payment(db, user, *, base_cents=2500, status=PaymentStatus.PENDING, paid_at=None):
    order = Order(user_id=user.id)
    db.add(order)
    db.flush()
    payment = Payment(
        user_id=user.id,
        order_id=order.id,
        base_amount_cents=base_cents,
        final_amount_cents=base_cents,
        status=status,
        paid_at=paid_at,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def test_list_payments_filters_status_dates_user_and_concept(db, make_user):
    member_a = make_user(RoleName.MEMBER)
    member_b = make_user(RoleName.MEMBER)
    early = _add_subscription_payment(db, member_a, base_cents=3900)
    early.created_at = datetime(2026, 10, 1, 10, 0, 0)
    mid = _add_subscription_payment(
        db,
        member_a,
        base_cents=5900,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 5),
        subscription=early.subscription,
    )
    mid.created_at = datetime(2026, 10, 5, 12, 0, 0)
    other = _add_order_payment(db, member_b, base_cents=1200)
    other.created_at = datetime(2026, 10, 5, 15, 0, 0)
    db.commit()

    by_status, total_status = payment_service.list_payments(
        db, status=PaymentStatus.PAID
    )
    by_user, total_user = payment_service.list_payments(db, user_id=member_a.id)
    by_dates, total_dates = payment_service.list_payments(
        db,
        from_=datetime(2026, 10, 5, 0, 0, 0),
        to=datetime(2026, 10, 5, 23, 59, 59),
    )
    by_concept, total_concept = payment_service.list_payments(db, concept="order")

    assert total_status == 1 and by_status[0].id == mid.id
    assert total_user == 2 and {p.id for p in by_user} == {early.id, mid.id}
    assert total_dates == 2 and {p.id for p in by_dates} == {mid.id, other.id}
    assert total_concept == 1 and by_concept[0].id == other.id


def test_list_payments_invalid_date_range_returns_422(db):
    with pytest.raises(ValidationAppError, match="from"):
        payment_service.list_payments(
            db,
            from_=datetime(2026, 10, 10),
            to=datetime(2026, 10, 1),
        )


@freeze_time(TODAY)
def test_rn16_refund_paid_marks_refunded_and_logs(db, make_user, caplog):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    payment = _add_subscription_payment(
        db,
        member,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 1),
    )

    with caplog.at_level("INFO", logger="app.services.payment_service"):
        result = payment_service.refund_payment(db, admin, payment.id)

    assert result.status == PaymentStatus.REFUNDED
    db.refresh(payment)
    assert payment.status == PaymentStatus.REFUNDED
    assert any(
        f"Admin {admin.id} refunded payment {payment.id}" in record.message
        for record in caplog.records
    )


@freeze_time(TODAY)
def test_rn16_refund_non_paid_returns_409(db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    pending = _add_subscription_payment(db, member)
    refunded = _add_subscription_payment(
        db,
        member,
        status=PaymentStatus.REFUNDED,
        subscription=pending.subscription,
    )
    # paid_at required only for paid; refunded may omit it
    refunded.paid_at = datetime(2026, 10, 1)
    db.commit()

    with pytest.raises(ConflictError, match="pagado"):
        payment_service.refund_payment(db, admin, pending.id)

    with pytest.raises(ConflictError, match="pagado"):
        payment_service.refund_payment(db, admin, refunded.id)


def test_refund_unknown_payment_returns_404(db, make_user):
    admin = make_user(RoleName.ADMIN)
    with pytest.raises(NotFoundError):
        payment_service.refund_payment(db, admin, payment_id=999_999)


def test_csv_export_has_header_and_one_row_per_payment(db, make_user):
    member = make_user(RoleName.MEMBER)
    admin = make_user(RoleName.ADMIN)
    code = _add_code(db, admin, code="CSV20", percent_off=20)
    paid = _add_subscription_payment(
        db,
        member,
        base_cents=5000,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 6, 10, 5, 0),
    )
    paid.discount_code_id = code.id
    paid.final_amount_cents = 4000
    paid.created_at = datetime(2026, 10, 6, 10, 0, 0)
    pending = _add_subscription_payment(
        db, member, base_cents=1200, subscription=paid.subscription
    )
    pending.created_at = datetime(2026, 10, 7, 9, 0, 0)
    db.commit()

    payments = payment_service.list_payments_for_export(db, user_id=member.id)
    csv_text = "".join(payment_service.iter_payments_csv(payments))
    rows = list(csv.reader(io.StringIO(csv_text)))

    assert rows[0] == list(payment_service.CSV_COLUMNS)
    assert len(rows) == 3  # header + 2 payments
    # Newest first
    assert rows[1][0] == str(pending.id)
    assert rows[1][payment_service.CSV_COLUMNS.index("status")] == "pending"
    assert rows[1][payment_service.CSV_COLUMNS.index("discount_code")] == ""
    assert rows[2][0] == str(paid.id)
    assert rows[2][payment_service.CSV_COLUMNS.index("concept")] == "subscription"
    assert rows[2][payment_service.CSV_COLUMNS.index("discount_code")] == "CSV20"
    assert rows[2][payment_service.CSV_COLUMNS.index("final_amount_cents")] == "4000"
    assert rows[2][payment_service.CSV_COLUMNS.index("user_id")] == str(member.id)


def test_csv_export_respects_same_filters_as_list(db, make_user):
    member = make_user(RoleName.MEMBER)
    pending = _add_subscription_payment(db, member, base_cents=1000)
    paid = _add_subscription_payment(
        db,
        member,
        base_cents=2000,
        status=PaymentStatus.PAID,
        paid_at=datetime(2026, 10, 2),
        subscription=pending.subscription,
    )
    db.commit()

    payments = payment_service.list_payments_for_export(db, status=PaymentStatus.PAID)
    csv_text = "".join(payment_service.iter_payments_csv(payments))
    rows = list(csv.reader(io.StringIO(csv_text)))

    assert len(rows) == 2
    assert rows[1][0] == str(paid.id)
    assert rows[1][payment_service.CSV_COLUMNS.index("status")] == "paid"
