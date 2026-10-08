"""Integration tests for POST/GET cancellation-requests (HU-19, RN-12)."""

import pytest
from sqlalchemy import func, select

from app.main import app
from app.models import CancellationRequest
from app.models.enums import CancellationStatus, RoleName, SubscriptionStatus
from tests.conftest import auth_header_for

CANCEL_URL = "/api/v1/cancellation-requests"
MY_CANCEL_URL = "/api/v1/cancellation-requests/me"


def count_rows(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_rn12_member_with_active_subscription_creates_pending_and_stays_active(
        client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    headers = auth_header_for(member)

    response = client.post(CANCEL_URL, json={"reason": "Me mudo de ciudad"}, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["subscription_id"] == subscription.id
    assert body["reason"] == "Me mudo de ciudad"
    assert body["reviewed_at"] is None
    assert body["admin_notes"] is None
    assert "id" in body
    assert "requested_at" in body

    db.refresh(member)
    assert member.is_active is True
    assert member.deactivated_at is None
    assert count_rows(db, CancellationRequest) == 1


def test_rn12_second_pending_returns_409(client, db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())
    headers = auth_header_for(member)
    first = client.post(CANCEL_URL, json={"reason": "Primera"}, headers=headers)

    second = client.post(CANCEL_URL, json={"reason": "Segunda"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {
        "detail": "Ya tienes una solicitud de baja pendiente.",
        "code": "conflict",
    }
    assert count_rows(db, CancellationRequest) == 1


def test_rn12_no_endpoint_lets_a_member_delete_herself(client, make_user):
    member = make_user()
    headers = auth_header_for(member)

    for method, path in [
        ("delete", "/api/v1/users/me"),
        ("delete", f"/api/v1/users/{member.id}"),
        ("delete", "/api/v1/users"),
        ("post", "/api/v1/users/me/delete"),
        ("post", "/api/v1/auth/delete"),
    ]:
        response = getattr(client, method)(path, headers=headers)
        assert response.status_code == 405 or response.status_code == 404, (
            f"{method.upper()} {path} unexpectedly returned {response.status_code}"
        )

    delete_routes = [
        (route.path, sorted(route.methods or []))
        for route in app.routes
        if getattr(route, "methods", None) and "DELETE" in route.methods
        and str(route.path).startswith("/api/v1/users")
    ]
    assert delete_routes == []


def test_get_me_returns_latest_request(client, db, make_user, make_plan, make_subscription):
    member = make_user()
    subscription = make_subscription(member, make_plan())
    headers = auth_header_for(member)
    created = client.post(CANCEL_URL, json={"reason": "Viajo"}, headers=headers)
    assert created.status_code == 201

    response = client.get(MY_CANCEL_URL, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created.json()["id"]
    assert body["status"] == CancellationStatus.PENDING
    assert body["reason"] == "Viajo"
    assert body["subscription_id"] == subscription.id


def test_get_me_without_request_returns_404(client, make_user):
    member = make_user()

    response = client.get(MY_CANCEL_URL, headers=auth_header_for(member))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_create_without_active_subscription_returns_404(
        client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan(), status=SubscriptionStatus.EXPIRED)

    response = client.post(
        CANCEL_URL, json={"reason": "Quiero irme"}, headers=auth_header_for(member)
    )

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert count_rows(db, CancellationRequest) == 0


def test_create_without_token_returns_401(client):
    response = client.post(CANCEL_URL, json={"reason": "Sin token"})

    assert response.status_code == 401


def test_get_me_without_token_returns_401(client):
    response = client.get(MY_CANCEL_URL)

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_create(client, db, auth_headers, make_plan, make_subscription, make_user, role):
    user = make_user(role)
    # Non-members typically have no subscription; still must be rejected by role first.
    response = client.post(
        CANCEL_URL, json={"reason": "No debería"}, headers=auth_header_for(user)
    )

    assert response.status_code == 403
    assert count_rows(db, CancellationRequest) == 0


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_read_me(client, make_user, role):
    response = client.get(MY_CANCEL_URL, headers=auth_header_for(make_user(role)))

    assert response.status_code == 403


@pytest.mark.parametrize(
    "body",
    [{}, {"reason": ""}, {"reason": "x" * 2001}, {"reason": 123}, {"reason": "ok", "status": "approved"}],
)
def test_malformed_body_returns_422(client, auth_headers, make_plan, make_subscription, make_user, body):
    member = make_user()
    make_subscription(member, make_plan())

    response = client.post(CANCEL_URL, json=body, headers=auth_header_for(member))

    assert response.status_code == 422


def test_member_a_cannot_see_member_b_request_via_me(
        client, db, make_user, make_plan, make_subscription
):
    alice = make_user()
    bob = make_user()
    make_subscription(alice, make_plan())
    make_subscription(bob, make_plan())
    created = client.post(
        CANCEL_URL, json={"reason": "De Alice"}, headers=auth_header_for(alice)
    )
    assert created.status_code == 201

    response = client.get(MY_CANCEL_URL, headers=auth_header_for(bob))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert count_rows(db, CancellationRequest) == 1
    assert db.get(CancellationRequest, created.json()["id"]).subscription.user_id == alice.id
