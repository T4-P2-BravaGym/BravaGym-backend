from app.core.security import create_access_token
from app.models.enums import RoleName
from tests.conftest import TEST_PASSWORD

ME_URL = "/api/v1/users/me"


def headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


def test_get_me_returns_my_data_and_role_without_password(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.get(ME_URL, headers=headers_for(member))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == member.id
    assert body["email"] == member.email
    assert body["role"] == "member"
    assert "password_hash" not in body


def test_get_me_without_token_returns_401(client):
    response = client.get(ME_URL)

    assert response.status_code == 401


def test_update_me_changes_name_and_phone(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"first_name": "Lucía", "phone": "600123456"}, headers=headers_for(member))

    assert response.status_code == 200
    assert response.json()["first_name"] == "Lucía"
    assert response.json()["phone"] == "600123456"
    assert response.json()["last_name"] == member.last_name


def test_update_me_ignores_role_and_is_active(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(
        ME_URL, json={"first_name": "Lucía", "role": "admin", "is_active": False}, headers=headers_for(member)
    )

    assert response.status_code == 200
    assert response.json()["role"] == "member"
    assert response.json()["is_active"] is True


def test_update_me_without_token_returns_401(client):
    response = client.patch(ME_URL, json={"first_name": "Lucía"})

    assert response.status_code == 401


def test_update_me_with_a_too_long_name_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"first_name": "a" * 81}, headers=headers_for(member))

    assert response.status_code == 422


def test_update_me_with_an_empty_name_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"first_name": ""}, headers=headers_for(member))

    assert response.status_code == 422


def test_update_me_with_a_null_name_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"first_name": None}, headers=headers_for(member))

    assert response.status_code == 422


def test_update_me_can_clear_the_phone(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    member.phone = "600123456"
    db.commit()

    response = client.patch(ME_URL, json={"phone": None}, headers=headers_for(member))

    assert response.status_code == 200
    assert response.json()["phone"] is None


def test_update_me_changes_the_email_in_lowercase(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"email": "  Nueva@Example.com "}, headers=headers_for(member))

    assert response.status_code == 200
    assert response.json()["email"] == "nueva@example.com"


def test_update_me_with_someone_elses_email_returns_409(client, make_user):
    member = make_user(RoleName.MEMBER)
    other = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"email": other.email.upper()}, headers=headers_for(member))

    assert response.status_code == 409
    assert response.json()["detail"] == "Ya existe una cuenta con ese email."


def test_update_me_keeping_my_own_email_is_allowed(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"email": member.email}, headers=headers_for(member))

    assert response.status_code == 200


def test_update_me_with_an_invalid_email_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.patch(ME_URL, json={"email": "no-es-un-email"}, headers=headers_for(member))

    assert response.status_code == 422


def test_login_works_with_the_new_email(client, make_user):
    member = make_user(RoleName.MEMBER)
    client.patch(ME_URL, json={"email": "nueva@example.com"}, headers=headers_for(member))

    response = client.post("/api/v1/auth/login", data={"username": "nueva@example.com", "password": TEST_PASSWORD})

    assert response.status_code == 200
    