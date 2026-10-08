import logging

import pytest

from app.core.security import create_access_token
from app.models import Role
from app.models.enums import RoleName


@pytest.fixture(autouse=True)
def all_roles(db):
    """The four roles exist in the real database (seed); create them here too."""
    db.add_all([Role(name=name) for name in RoleName])
    db.commit()


def role_url(user):
    return f"/api/v1/users/{user.id}/role"


def headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


def test_admin_turns_a_member_into_a_trainer_with_an_empty_profile(client, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    response = client.patch(role_url(member), json={"role": "trainer"}, headers=headers_for(admin))

    assert response.status_code == 200
    assert response.json()["role"] == "trainer"
    trainers = client.get("/api/v1/trainers").json()
    assert [(t["id"], t["bio"], t["specialty"]) for t in trainers] == [(member.id, None, None)]


def test_admin_turns_a_trainer_back_into_a_member(client, make_user):
    admin = make_user(RoleName.ADMIN)
    trainer = make_user(RoleName.TRAINER)

    response = client.patch(role_url(trainer), json={"role": "member"}, headers=headers_for(admin))

    assert response.status_code == 200
    assert response.json()["role"] == "member"


@pytest.mark.parametrize("new_role", ["admin", "superadmin"])
def test_rn18_admin_cannot_give_staff_roles_returns_403(client, make_user, new_role):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    response = client.patch(role_url(member), json={"role": new_role}, headers=headers_for(admin))

    assert response.status_code == 403


def test_rn18_admin_cannot_remove_another_admin_returns_403(client, make_user):
    admin = make_user(RoleName.ADMIN)
    other_admin = make_user(RoleName.ADMIN)

    response = client.patch(role_url(other_admin), json={"role": "member"}, headers=headers_for(admin))

    assert response.status_code == 403


def test_rn18_superadmin_can_make_someone_admin(client, make_user):
    superadmin = make_user(RoleName.SUPERADMIN)
    trainer = make_user(RoleName.TRAINER)

    response = client.patch(role_url(trainer), json={"role": "admin"}, headers=headers_for(superadmin))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


@pytest.mark.parametrize("role", [RoleName.ADMIN, RoleName.SUPERADMIN])
def test_rn19_nobody_changes_her_own_role_returns_409(client, make_user, role):
    user = make_user(role)

    response = client.patch(role_url(user), json={"role": "member"}, headers=headers_for(user))

    assert response.status_code == 409


def test_rn19_superadmin_can_demote_another_superadmin_when_two_exist(client, make_user):
    superadmin = make_user(RoleName.SUPERADMIN)
    other = make_user(RoleName.SUPERADMIN)

    response = client.patch(role_url(other), json={"role": "admin"}, headers=headers_for(superadmin))

    assert response.status_code == 200


def test_member_cannot_change_roles_returns_403(client, make_user):
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)

    response = client.patch(role_url(other), json={"role": "trainer"}, headers=headers_for(member))

    assert response.status_code == 403


def test_change_role_without_token_returns_401(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(role_url(member), json={"role": "trainer"})

    assert response.status_code == 401


def test_change_role_of_an_unknown_user_returns_404(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.patch("/api/v1/users/9999/role", json={"role": "trainer"}, headers=headers_for(admin))

    assert response.status_code == 404


def test_change_role_to_an_unknown_role_returns_422(client, make_user):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    response = client.patch(role_url(member), json={"role": "queen"}, headers=headers_for(admin))

    assert response.status_code == 422


def test_role_change_is_logged_with_who_whom_and_both_roles(client, make_user, caplog):
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)

    with caplog.at_level(logging.INFO, logger="app.services.user_service"):
        client.patch(role_url(member), json={"role": "trainer"}, headers=headers_for(admin))

    assert f"User {admin.id} changed the role of user {member.id} from member to trainer" in caplog.text


    