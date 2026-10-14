"""Admin user management: view, edit and deactivate (HU-31)."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import Booking, ClassSession, ClassType, Subscription
from app.models.enums import BookingStatus, RoleName, SubscriptionStatus
from tests.conftest import TEST_PASSWORD, auth_header_for

USER_URL = "/api/v1/users/{user_id}"
LOGIN_URL = "/api/v1/auth/login"


# --- GET /users/{id} ---


def test_admin_sees_a_user_with_her_role(client, make_user):
    admin = make_user(RoleName.ADMIN)
    trainer = make_user(RoleName.TRAINER)

    response = client.get(USER_URL.format(user_id=trainer.id), headers=auth_header_for(admin))

    assert response.status_code == 200
    assert response.json()["email"] == trainer.email
    assert response.json()["role"] == "trainer"
    assert "password_hash" not in response.json()


def test_unknown_user_returns_404(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.get(USER_URL.format(user_id=9999), headers=auth_header_for(admin))

    assert response.status_code == 404


def test_member_and_trainer_cannot_manage_users_returns_403(client, make_user):
    other = make_user()

    for role in (RoleName.MEMBER, RoleName.TRAINER):
        headers = auth_header_for(make_user(role))
        assert client.get(USER_URL.format(user_id=other.id), headers=headers).status_code == 403
        assert client.patch(USER_URL.format(user_id=other.id), json={"first_name": "X"}, headers=headers).status_code == 403
        assert client.delete(USER_URL.format(user_id=other.id), headers=headers).status_code == 403


def test_manage_users_without_token_returns_401(client, make_user):
    other = make_user()

    assert client.get(USER_URL.format(user_id=other.id)).status_code == 401
    assert client.delete(USER_URL.format(user_id=other.id)).status_code == 401


# --- PATCH /users/{id} ---


def test_admin_edits_name_and_email_and_role_is_ignored(client, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user()

    response = client.patch(
        USER_URL.format(user_id=member.id),
        json={"first_name": "Lucía", "email": " Nueva@Example.com", "role": "admin", "is_active": False, "password": "x"},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["first_name"] == "Lucía"
    assert body["email"] == "nueva@example.com"
    assert body["role"] == "member"
    assert body["is_active"] is True


def test_admin_edit_with_someone_elses_email_returns_409(client, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user()
    other = make_user()

    response = client.patch(USER_URL.format(user_id=member.id), json={"email": other.email}, headers=auth_header_for(admin))

    assert response.status_code == 409


def test_rn18_admin_cannot_edit_or_deactivate_a_superadmin_returns_403(client, make_user):
    admin = make_user(RoleName.ADMIN)
    superadmin = make_user(RoleName.SUPERADMIN)
    headers = auth_header_for(admin)

    edit = client.patch(USER_URL.format(user_id=superadmin.id), json={"email": "mine@example.com"}, headers=headers)
    delete = client.delete(USER_URL.format(user_id=superadmin.id), headers=headers)

    assert (edit.status_code, delete.status_code) == (403, 403)


def test_rn18_admin_cannot_deactivate_another_admin_returns_403(client, make_user):
    admin = make_user(RoleName.ADMIN)
    other_admin = make_user(RoleName.ADMIN)

    response = client.delete(USER_URL.format(user_id=other_admin.id), headers=auth_header_for(admin))

    assert response.status_code == 403


# --- DELETE /users/{id} ---


def test_deactivate_keeps_the_row_and_blocks_login(client, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user()

    response = client.delete(USER_URL.format(user_id=member.id), headers=auth_header_for(admin))

    assert response.status_code == 204
    kept = client.get(USER_URL.format(user_id=member.id), headers=auth_header_for(admin))
    assert kept.status_code == 200
    assert kept.json()["is_active"] is False
    login = client.post(LOGIN_URL, data={"username": member.email, "password": TEST_PASSWORD})
    assert login.status_code == 401


def test_deactivate_sets_deactivated_at(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user()

    client.delete(USER_URL.format(user_id=member.id), headers=auth_header_for(admin))

    db.refresh(member)
    assert member.deactivated_at is not None


def test_rn19_nobody_deactivates_herself_returns_409(client, make_user):
    for role in (RoleName.ADMIN, RoleName.SUPERADMIN):
        user = make_user(role)

        response = client.delete(USER_URL.format(user_id=user.id), headers=auth_header_for(user))

        assert response.status_code == 409


def test_superadmin_can_deactivate_an_admin(client, make_user):
    superadmin = make_user(RoleName.SUPERADMIN)
    admin = make_user(RoleName.ADMIN)

    response = client.delete(USER_URL.format(user_id=admin.id), headers=auth_header_for(superadmin))

    assert response.status_code == 204


def test_deactivate_cancels_subscription_and_future_bookings(client, db, make_user, make_plan, make_subscription):
    """Same chain as an approved cancellation (HU-20)."""
    admin = make_user(RoleName.ADMIN)
    member = make_user()
    subscription = make_subscription(member, make_plan())
    session = ClassSession(
        class_type=ClassType(name="Fuerza futura", extra_price_cents=0),
        trainer=make_user(RoleName.TRAINER),
        starts_at=datetime(2030, 1, 7, 18, 0, tzinfo=timezone.utc),
        capacity=5,
    )
    db.add(Booking(user_id=member.id, class_session=session, status=BookingStatus.CONFIRMED))
    db.commit()

    client.delete(USER_URL.format(user_id=member.id), headers=auth_header_for(admin))

    db.expire_all()
    assert db.get(Subscription, subscription.id).status == SubscriptionStatus.CANCELLED
    booking = db.scalar(select(Booking).where(Booking.user_id == member.id))
    assert booking.status == BookingStatus.CANCELLED


def test_deactivation_is_logged_with_who_and_whom(client, make_user, caplog):
    admin = make_user(RoleName.ADMIN)
    member = make_user()

    with caplog.at_level(logging.INFO, logger="app.services.user_service"):
        client.delete(USER_URL.format(user_id=member.id), headers=auth_header_for(admin))

    assert f"User {admin.id} deactivated user {member.id}" in caplog.text