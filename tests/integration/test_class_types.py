"""Integration tests for /class-types CRUD (HU-11.1)."""

from app.models.enums import RoleName
from tests.conftest import auth_header_for

CLASS_TYPES_URL = "/api/v1/class-types"


def test_get_class_types_is_public(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    create = client.post(
        CLASS_TYPES_URL,
        headers=auth_header_for(trainer),
        json={
            "name": "Fuerza pública",
            "description": "Visible sin token.",
            "extra_price_cents": 0,
        },
    )
    assert create.status_code == 201

    response = client.get(CLASS_TYPES_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["total"] >= 1
    assert any(item["name"] == "Fuerza pública" for item in body["items"])


def test_post_class_type_requires_auth(client):
    response = client.post(
        CLASS_TYPES_URL,
        json={"name": "Sin token", "extra_price_cents": 0},
    )
    assert response.status_code == 401


def test_post_class_type_member_gets_403(client, make_user):
    member = make_user(RoleName.MEMBER)
    response = client.post(
        CLASS_TYPES_URL,
        headers=auth_header_for(member),
        json={"name": "Solo member", "extra_price_cents": 0},
    )
    assert response.status_code == 403


def test_trainer_can_create_update_and_deactivate(client, make_user):
    trainer = make_user(RoleName.TRAINER)
    headers = auth_header_for(trainer)

    created = client.post(
        CLASS_TYPES_URL,
        headers=headers,
        json={
            "name": "Movilidad",
            "description": "Core y movilidad.",
            "extra_price_cents": 500,
            "is_personal_training": False,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "Movilidad"
    assert body["extra_price_cents"] == 500
    assert body["is_active"] is True
    class_type_id = body["id"]

    updated = client.patch(
        f"{CLASS_TYPES_URL}/{class_type_id}",
        headers=headers,
        json={"description": "Actualizado.", "extra_price_cents": 800},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Actualizado."
    assert updated.json()["extra_price_cents"] == 800

    deleted = client.delete(
        f"{CLASS_TYPES_URL}/{class_type_id}",
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False

    listed = client.get(CLASS_TYPES_URL)
    assert all(item["id"] != class_type_id for item in listed.json()["items"])


def test_duplicate_class_type_name_returns_409(client, make_user):
    trainer = make_user(RoleName.TRAINER)
    headers = auth_header_for(trainer)
    payload = {"name": "Duplicado", "extra_price_cents": 0}

    first = client.post(CLASS_TYPES_URL, headers=headers, json=payload)
    second = client.post(CLASS_TYPES_URL, headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"
