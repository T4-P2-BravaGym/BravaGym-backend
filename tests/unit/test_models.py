from datetime import date

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import MembershipPlan, Payment, Role, Subscription, User
from app.models.enums import RoleName, SubscriptionStatus

EXPECTED_TABLES = {
    "roles",
    "users",
    "trainer_profiles",
    "membership_plans",
    "subscriptions",
    "cancellation_requests",
    "class_types",
    "class_sessions",
    "bookings",
    "exercises",
    "routines",
    "routine_exercises",
    "product_categories",
    "products",
    "orders",
    "order_items",
    "discount_codes",
    "payments",
}


def make_member(db) -> User:
    member = User(
        email="socia@example.com",
        password_hash="not-a-real-hash",
        first_name="Lucía",
        last_name="Gil",
        role=Role(name=RoleName.MEMBER),
    )
    db.add(member)
    db.flush()
    return member


def test_schema_has_the_18_tables(db):
    assert set(inspect(db.get_bind()).get_table_names()) == EXPECTED_TABLES


def test_foreign_key_is_enforced(db):
    db.add(
        User(
            email="nadie@example.com",
            password_hash="x",
            first_name="Nadie",
            last_name="Nadie",
            role_id=999,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_check_rejects_a_negative_price(db):
    db.add(MembershipPlan(name="Gratis", monthly_price_cents=-100))
    with pytest.raises(IntegrityError):
        db.flush()


def test_enum_check_rejects_an_unknown_role(db):
    with pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO roles (name) VALUES ('hacker')"))


def test_unique_rejects_a_repeated_email(db):
    make_member(db)
    db.add(
        User(
            email="socia@example.com",
            password_hash="x",
            first_name="Otra",
            last_name="Socia",
            role=Role(name=RoleName.TRAINER),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_payment_needs_exactly_one_concept(db):
    member = make_member(db)
    db.add(Payment(user=member, base_amount_cents=1000, final_amount_cents=1000))
    with pytest.raises(IntegrityError):
        db.flush()


def test_rn11_only_one_active_subscription_per_user(db):
    member = make_member(db)
    plan = MembershipPlan(name="Básico", monthly_price_cents=3900)
    db.add_all(
        [
            Subscription(user=member, plan=plan, start_date=date.today()),
            Subscription(user=member, plan=plan, start_date=date.today()),
        ]
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_rn11_a_cancelled_subscription_does_not_block_a_new_one(db):
    member = make_member(db)
    plan = MembershipPlan(name="Básico", monthly_price_cents=3900)
    db.add_all(
        [
            Subscription(
                user=member,
                plan=plan,
                start_date=date.today(),
                status=SubscriptionStatus.CANCELLED,
            ),
            Subscription(user=member, plan=plan, start_date=date.today()),
        ]
    )
    db.flush()

    assert db.scalar(select(func.count()).select_from(Subscription)) == 2