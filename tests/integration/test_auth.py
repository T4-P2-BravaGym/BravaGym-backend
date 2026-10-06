import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from freezegun import freeze_time

from app.core.database import get_db
from app.core.deps import CurrentUser, require_roles
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, decode_access_token
from app.models.enums import RoleName
from tests.conftest import TEST_PASSWORD

LOGIN_URL = "/api/v1/auth/login"


def login(client, email: str, password: str):
    return client.post(LOGIN_URL, data={"username": email, "password": password})


def test_login_returns_a_token_with_the_user_id_and_role(client, make_user):
    trainer = make_user(RoleName.TRAINER)

    response = login(client, trainer.email, TEST_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    payload = decode_access_token(body["access_token"])
    assert payload["sub"] == str(trainer.id)
    assert payload["role"] == "trainer"


def test_login_ignores_email_case_and_spaces(client, make_user):
    make_user(email="lucia@example.com")

    response = login(client, "  Lucia@Example.com ", TEST_PASSWORD)

    assert response.status_code == 200


def test_wrong_password_returns_generic_401(client, make_user):
    member = make_user()

    response = login(client, member.email, "wrong-password")

    assert response.status_code == 401
    assert response.json() == {"detail": "Email o contraseña incorrectos.", "code": "unauthorized"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_email_returns_the_same_401_as_a_wrong_password(client, make_user):
    member = make_user()

    wrong_password = login(client, member.email, "wrong-password")
    unknown_email = login(client, "nobody@example.com", TEST_PASSWORD)

    assert unknown_email.status_code == 401
    assert unknown_email.json() == wrong_password.json()


def test_inactive_user_cannot_log_in(client, make_user):
    former_member = make_user(is_active=False)

    response = login(client, former_member.email, TEST_PASSWORD)

    assert response.status_code == 401


@pytest.fixture
def protected_client(db):
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/me")
    def read_me(current_user: CurrentUser) -> dict[str, int]:
        return {"id": current_user.id}

    @test_app.get(
        "/admin-only",
        dependencies=[Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))],
    )
    def admin_only() -> dict[str, bool]:
        return {"ok": True}

    test_app.dependency_overrides[get_db] = lambda: db
    return TestClient(test_app)


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_identifies_the_user(protected_client, make_user):
    member = make_user()

    response = protected_client.get("/me", headers=bearer(create_access_token(member.id, "member")))

    assert response.status_code == 200
    assert response.json() == {"id": member.id}


def test_no_token_returns_401(protected_client):
    response = protected_client.get("/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_malformed_token_returns_401(protected_client):
    response = protected_client.get("/me", headers=bearer("not-a-jwt"))

    assert response.status_code == 401


def test_expired_token_returns_401(protected_client, make_user):
    member = make_user()
    with freeze_time("2026-10-06 10:00:00"):
        token = create_access_token(member.id, "member")

    with freeze_time("2026-10-06 11:01:00"):
        response = protected_client.get("/me", headers=bearer(token))

    assert response.status_code == 401


def test_token_of_a_deactivated_user_returns_401(protected_client, make_user, db):
    member = make_user()
    token = create_access_token(member.id, "member")
    member.is_active = False
    db.commit()

    response = protected_client.get("/me", headers=bearer(token))

    assert response.status_code == 401


def test_member_on_an_admin_route_gets_403(protected_client, auth_headers):
    response = protected_client.get("/admin-only", headers=auth_headers(RoleName.MEMBER))

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


@pytest.mark.parametrize("role", [RoleName.ADMIN, RoleName.SUPERADMIN])
def test_allowed_roles_get_200(protected_client, auth_headers, role):
    response = protected_client.get("/admin-only", headers=auth_headers(role))

    assert response.status_code == 200


def test_role_is_read_from_the_database_not_from_the_token(protected_client, make_user):
    member = make_user(RoleName.MEMBER)
    token = create_access_token(member.id, "admin")

    response = protected_client.get("/admin-only", headers=bearer(token))

    assert response.status_code == 403