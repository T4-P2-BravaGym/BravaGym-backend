from sqlalchemy import select

from app.core.security import verify_password
from app.models import User

URL = "/api/v1/auth/register"


def valid_payload(**overrides) -> dict:
    """A correct body; each test changes only what it needs."""
    payload = {
        "email": "lucia@example.com",
        "password": "BravaDemo2026!",
        "first_name": "Lucía",
        "last_name": "Gil",
    }
    return {**payload, **overrides}


def test_register_new_email_returns_201_active_member(client, roles):
    response = client.post(URL, json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "member"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_register_existing_email_returns_409(client, roles):
    client.post(URL, json=valid_payload())

    response = client.post(URL, json=valid_payload())

    assert response.status_code == 409


def test_register_same_email_different_case_returns_409(client, roles):
    client.post(URL, json=valid_payload(email="Lucia@example.com"))

    response = client.post(URL, json=valid_payload(email="LUCIA@EXAMPLE.COM"))

    assert response.status_code == 409


def test_register_stores_password_hashed_with_bcrypt(client, db, roles):
    client.post(URL, json=valid_payload())

    user = db.scalar(select(User).where(User.email == "lucia@example.com"))
    assert user.password_hash != "BravaDemo2026!"
    assert user.password_hash.startswith("$2b$")
    assert verify_password("BravaDemo2026!", user.password_hash)


def test_register_ignores_role_sent_by_client(client, roles):
    response = client.post(URL, json=valid_payload(role="admin", is_active=False))

    assert response.json()["role"] == "member"
    assert response.json()["is_active"] is True


def test_register_short_password_returns_422(client, roles):
    response = client.post(URL, json=valid_payload(password="1234567"))

    assert response.status_code == 422


def test_register_password_over_72_bytes_returns_422(client, roles):
    response = client.post(URL, json=valid_payload(password="ñ" * 37))

    assert response.status_code == 422


def test_register_invalid_email_returns_422(client, roles):
    response = client.post(URL, json=valid_payload(email="no-es-un-email"))

    assert response.status_code == 422

def test_register_name_with_digits_returns_422(client):
    body = {
        "email": "nueva@example.com",
        "password": "BravaDemo2026!",
        "first_name": "Ana3",
        "last_name": "Torres",
    }

    response = client.post("/api/v1/auth/register", json=body)

    assert response.status_code == 422
