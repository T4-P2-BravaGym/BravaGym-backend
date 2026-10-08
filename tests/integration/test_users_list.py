from app.models.enums import RoleName

USERS_URL = "/api/v1/users"


# --- Acceptance criteria ---------------------------------------------------

def test_admin_filters_active_members_paginated(client, make_user, auth_headers):
    # Two active members, plus noise that must be filtered out
    make_user(RoleName.MEMBER)
    make_user(RoleName.MEMBER)
    make_user(RoleName.MEMBER, is_active=False)
    make_user(RoleName.TRAINER)

    response = client.get(
        USERS_URL,
        params={"role": "member", "is_active": "true"},
        headers=auth_headers(RoleName.ADMIN),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert all(user["role"] == "member" and user["is_active"] for user in body["items"])


def test_member_cannot_list_users_returns_403(client, auth_headers):
    response = client.get(USERS_URL, headers=auth_headers(RoleName.MEMBER))

    assert response.status_code == 403


# --- Permissions -----------------------------------------------------------

def test_list_users_without_token_returns_401(client):
    response = client.get(USERS_URL)

    assert response.status_code == 401


def test_trainer_cannot_list_users_returns_403(client, auth_headers):
    response = client.get(USERS_URL, headers=auth_headers(RoleName.TRAINER))

    assert response.status_code == 403


def test_superadmin_can_list_users(client, auth_headers):
    response = client.get(USERS_URL, headers=auth_headers(RoleName.SUPERADMIN))

    assert response.status_code == 200


# --- Pagination and search -------------------------------------------------

def test_second_page_returns_the_remaining_users(client, make_user, auth_headers):
    for _ in range(3):
        make_user(RoleName.MEMBER)

    response = client.get(
        USERS_URL,
        params={"role": "member", "page": 2, "size": 2},
        headers=auth_headers(RoleName.ADMIN),
    )

    body = response.json()
    assert body["total"] == 3  # total counts every match, not just this page
    assert len(body["items"]) == 1


def test_search_finds_users_by_email_ignoring_case(client, make_user, auth_headers):
    make_user(RoleName.MEMBER, email="lucia.garcia@example.com")
    make_user(RoleName.MEMBER, email="marta.lopez@example.com")

    response = client.get(USERS_URL, params={"q": "GARCIA"}, headers=auth_headers(RoleName.ADMIN))

    emails = [user["email"] for user in response.json()["items"]]
    assert emails == ["lucia.garcia@example.com"]


# --- Error paths and safe output -------------------------------------------

def test_size_over_100_returns_422(client, auth_headers):
    response = client.get(USERS_URL, params={"size": 101}, headers=auth_headers(RoleName.ADMIN))

    assert response.status_code == 422


def test_unknown_role_returns_422(client, auth_headers):
    response = client.get(USERS_URL, params={"role": "boss"}, headers=auth_headers(RoleName.ADMIN))

    assert response.status_code == 422


def test_list_never_exposes_password_hash(client, make_user, auth_headers):
    make_user(RoleName.MEMBER)

    response = client.get(USERS_URL, headers=auth_headers(RoleName.ADMIN))

    assert all("password_hash" not in user for user in response.json()["items"])