"""T-03: every change to a user records who made it (updated_by_id) and when (updated_at)."""

from datetime import datetime

from app.models import User
from app.models.enums import RoleName
from freezegun import freeze_time
from sqlalchemy import select

from tests.conftest import TEST_PASSWORD, auth_header_for

NOW = "2026-10-16 10:00:00"
USERS_URL = "/api/v1/users"


def assert_updated_by(db, user, actor):
    db.refresh(user)
    assert user.updated_at == datetime.fromisoformat(NOW)
    assert user.updated_by_id == actor.id


def assert_not_updated(db, user):
    db.refresh(user)
    assert user.updated_at is None
    assert user.updated_by_id is None


def test_register_leaves_the_audit_columns_empty(client, roles, db):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "nueva@example.com",
            "password": "BravaDemo2026!",
            "first_name": "Nueva",
            "last_name": "Socia",
        },
    )

    assert response.status_code == 201
    user = db.scalar(select(User).where(User.email == "nueva@example.com"))
    assert user.created_by_id is None
    assert user.updated_at is None
    assert user.updated_by_id is None


def test_editing_my_profile_records_me(client, db, make_user):
    member = make_user(RoleName.MEMBER)

    with freeze_time(NOW):
        response = client.patch(
            f"{USERS_URL}/me",
            json={"first_name": "Lucía"},
            headers=auth_header_for(member),
        )

    assert response.status_code == 200
    assert_updated_by(db, member, member)


def test_an_empty_patch_is_not_a_change(client, db, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(f"{USERS_URL}/me", json={}, headers=auth_header_for(member))

    assert response.status_code == 200
    assert_not_updated(db, member)


def test_changing_my_password_records_me(client, db, make_user):
    member = make_user(RoleName.MEMBER)

    with freeze_time(NOW):
        response = client.post(
            f"{USERS_URL}/me/password",
            json={"current_password": TEST_PASSWORD, "new_password": "OtraClave2026!"},
            headers=auth_header_for(member),
        )

    assert response.status_code == 204
    assert_updated_by(db, member, member)


def test_a_wrong_current_password_is_not_a_change(client, db, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.post(
        f"{USERS_URL}/me/password",
        json={"current_password": "NoEsMiClave1", "new_password": "OtraClave2026!"},
        headers=auth_header_for(member),
    )

    assert response.status_code == 400
    assert_not_updated(db, member)


def test_a_role_change_records_the_admin(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    make_user(RoleName.TRAINER)  # creates the trainer role

    with freeze_time(NOW):
        response = client.patch(
            f"{USERS_URL}/{member.id}/role",
            json={"role": "trainer"},
            headers=auth_header_for(admin),
        )

    assert response.status_code == 200
    assert_updated_by(db, member, admin)


def test_a_refused_role_change_is_not_a_change(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    make_user(RoleName.MEMBER)  # creates the member role

    response = client.patch(
        f"{USERS_URL}/{admin.id}/role",
        json={"role": "member"},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 409
    assert_not_updated(db, admin)


def test_an_admin_editing_a_user_records_the_admin(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    with freeze_time(NOW):
        response = client.patch(
            f"{USERS_URL}/{member.id}",
            json={"phone": "600123123"},
            headers=auth_header_for(admin),
        )

    assert response.status_code == 200
    assert_updated_by(db, member, admin)


def test_an_edit_with_someone_elses_email_is_not_a_change(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)

    response = client.patch(
        f"{USERS_URL}/{member.id}",
        json={"email": other.email},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 409
    assert_not_updated(db, member)


def test_a_deactivation_records_the_admin(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    with freeze_time(NOW):
        response = client.delete(
            f"{USERS_URL}/{member.id}", headers=auth_header_for(admin)
        )

    assert response.status_code == 204
    assert_updated_by(db, member, admin)
