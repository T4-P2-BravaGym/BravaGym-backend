"""HU-32: POST /users/me/password."""

import logging

from app.core.security import create_access_token
from app.models.enums import RoleName

from tests.conftest import TEST_PASSWORD

PASSWORD_URL = "/api/v1/users/me/password"
LOGIN_URL = "/api/v1/auth/login"
NEW_PASSWORD = "OtraClave2026!"


def headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


def change(client, user, current=TEST_PASSWORD, new=NEW_PASSWORD):
    return client.post(
        PASSWORD_URL,
        json={"current_password": current, "new_password": new},
        headers=headers_for(user),
    )


def login(client, email, password):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def test_change_password_returns_204_and_login_works_with_the_new_one(
    client, make_user
):
    member = make_user(RoleName.MEMBER)

    response = change(client, member)

    assert response.status_code == 204
    assert login(client, member.email, NEW_PASSWORD).status_code == 200


def test_old_password_no_longer_works(client, make_user):
    member = make_user(RoleName.MEMBER)
    change(client, member)

    assert login(client, member.email, TEST_PASSWORD).status_code == 401


def test_any_role_can_change_her_password(client, make_user):
    trainer = make_user(RoleName.TRAINER)

    assert change(client, trainer).status_code == 204


def test_wrong_current_password_returns_400_and_keeps_the_old_one(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = change(client, member, current="NoEsMiClave1")

    assert response.status_code == 400
    assert response.json()["detail"] == "La contraseña actual no es correcta."
    assert login(client, member.email, TEST_PASSWORD).status_code == 200


def test_new_password_shorter_than_8_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    assert change(client, member, new="corta").status_code == 422


def test_new_password_equal_to_the_current_one_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    assert change(client, member, new=TEST_PASSWORD).status_code == 422


def test_new_password_over_72_bytes_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    # "ñ" uses 2 bytes: 40 of them are 80 bytes
    assert change(client, member, new="ñ" * 40).status_code == 422


def test_change_password_without_token_returns_401(client):
    response = client.post(
        PASSWORD_URL,
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
    )

    assert response.status_code == 401


def test_five_wrong_tries_block_the_next_one_with_429(client, make_user):
    member = make_user(RoleName.MEMBER)
    for _ in range(5):
        assert change(client, member, current="NoEsMiClave1").status_code == 400

    # Blocked even with the right password
    response = change(client, member)

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_the_limit_is_per_user(client, make_user):
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)
    for _ in range(5):
        change(client, member, current="NoEsMiClave1")

    assert change(client, other).status_code == 204


def test_log_shows_the_change_but_never_the_password(client, make_user, caplog):
    member = make_user(RoleName.MEMBER)

    with caplog.at_level(logging.INFO):
        change(client, member, current="NoEsMiClave1")
        change(client, member)

    assert f"User {member.id} changed her password" in caplog.text
    assert TEST_PASSWORD not in caplog.text
    assert NEW_PASSWORD not in caplog.text
    assert "NoEsMiClave1" not in caplog.text
