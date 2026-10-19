"""HU-17: trainers pick a member from GET /users/members."""

import pytest
from app.models.enums import RoleName

from tests.conftest import auth_header_for

MEMBERS_URL = "/api/v1/users/members"


def test_trainer_sees_only_active_members(client, make_user):
    active = make_user(RoleName.MEMBER)
    make_user(RoleName.MEMBER, is_active=False)  # deactivated: must not appear
    make_user(RoleName.ADMIN)  # not a member: must not appear

    response = client.get(
        MEMBERS_URL, headers=auth_header_for(make_user(RoleName.TRAINER))
    )

    assert response.status_code == 200
    assert [member["id"] for member in response.json()] == [active.id]


def test_members_list_has_no_contact_data(client, make_user):
    make_user(RoleName.MEMBER)

    response = client.get(
        MEMBERS_URL, headers=auth_header_for(make_user(RoleName.TRAINER))
    )

    # set(dict) gives its keys: exactly these three, nothing else
    assert set(response.json()[0]) == {"id", "first_name", "last_name"}


def test_members_without_token_returns_401(client):
    assert client.get(MEMBERS_URL).status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.ADMIN])
def test_only_trainers_list_members(client, make_user, role):
    response = client.get(MEMBERS_URL, headers=auth_header_for(make_user(role)))

    assert response.status_code == 403
