import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from datetime import date
from functools import cache
from itertools import count

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, enable_sqlite_foreign_keys, get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import MembershipPlan, Role, Subscription, User
from app.models.enums import RoleName, SubscriptionStatus

TEST_PASSWORD = "Secret123!"
_email_counter = count(1)
_plan_counter = count(1)

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
enable_sqlite_foreign_keys(test_engine)
TestingSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, expire_on_commit=False
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@cache
def _test_password_hash() -> str:
    return hash_password(TEST_PASSWORD)


def auth_header_for(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


@pytest.fixture
def make_user(db):

    def _make_user(
        role: RoleName = RoleName.MEMBER,
        email: str | None = None,
        is_active: bool = True,
    ) -> User:
        role_row = db.scalar(select(Role).where(Role.name == role)) or Role(name=role)
        user = User(
            email=email or f"{role}{next(_email_counter)}@example.com",
            password_hash=_test_password_hash(),
            first_name="Test",
            last_name=str(role).capitalize(),
            role=role_row,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        return user

    return _make_user


@pytest.fixture
def roles(db):
    """The 4 roles. Get or create, so it works with make_user in any order."""
    result = {}
    for name in RoleName:
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name)
            db.add(role)
        result[name] = role
    db.commit()
    return result


@pytest.fixture
def auth_headers(make_user):

    def _auth_headers(role: RoleName = RoleName.MEMBER) -> dict[str, str]:
        return auth_header_for(make_user(role))

    return _auth_headers


@pytest.fixture
def make_plan(db):

    def _make_plan(
        monthly_price_cents: int = 5900,
        is_active: bool = True,
        includes_personal_training: bool = False,
        name: str | None = None,
    ) -> MembershipPlan:
        plan = MembershipPlan(
            name=name or f"Plan {next(_plan_counter)}",
            monthly_price_cents=monthly_price_cents,
            is_active=is_active,
            includes_personal_training=includes_personal_training,
        )
        db.add(plan)
        db.commit()
        return plan

    return _make_plan


@pytest.fixture
def make_subscription(db):

    def _make_subscription(
        user: User,
        plan: MembershipPlan,
        status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
        start_date: date = date(2026, 9, 1),
    ) -> Subscription:
        subscription = Subscription(
            user_id=user.id, plan=plan, status=status, start_date=start_date
        )
        db.add(subscription)
        db.commit()
        return subscription

    return _make_subscription
