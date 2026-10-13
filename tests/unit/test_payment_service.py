"""Unit tests for member payments (HU-24, RN-14 to RN-16)."""
from datetime import date, datetime

import pytest
from freezegun import freeze_time

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models import DiscountCode, MembershipPlan, Payment, Subscription
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
