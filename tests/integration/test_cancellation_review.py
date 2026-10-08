"""Integration tests for admin cancellation review (HU-20 / RN-13)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Booking, CancellationRequest, ClassSession, ClassType
from app.models.enums import (
    BookingStatus,
    CancellationStatus,
    RoleName,
    SessionStatus,
    SubscriptionStatus,
)
from app.services import booking_service
from tests.conftest import TEST_PASSWORD, auth_header_for

CANCEL_URL = "/api/v1/cancellation-requests"
LOGIN_URL = "/api/v1/auth/login"


def _pending_via_api(client, member, reason: str = "Me mudo") -> dict:
    response = client.post(
        CANCEL_URL, json={"reason": reason}, headers=auth_header_for(member)
    )
    assert response.status_code == 201
    return response.json()


def _make_class_session(
    db,
    make_user,
    *,
    capacity: int = 2,
    starts_at: datetime | None = None,
    name: str = "Clase admin baja",
) -> ClassSession:
    trainer = make_user(RoleName.TRAINER)
    class_type = ClassType(
        name=name,
        description="Sesión de prueba HU-20.",
        extra_price_cents=0,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts_at or (datetime.now(timezone.utc) + timedelta(days=3)),
        capacity=capacity,
        status=SessionStatus.SCHEDULED,
    )
    db.add(session)
    db.commit()
    return session


def test_rn13_admin_approves_pending_request_chain_effect(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    waiter = make_user()
    plan = make_plan()
    make_subscription(member, plan)
    make_subscription(waiter, plan)
    admin = make_user(RoleName.ADMIN)
    created = _pending_via_api(client, member)

    future = _make_class_session(db, make_user, capacity=1, name="Aprobar futura")
    booking_service.book_session(db, user_id=member.id, class_session_id=future.id)
    waitlisted = booking_service.book_session(
        db, user_id=waiter.id, class_session_id=future.id
    )
    assert waitlisted.booking.status == BookingStatus.WAITLISTED

    response = client.post(
        f"{CANCEL_URL}/{created['id']}/approve",
        json={"admin_notes": "Baja confirmada tras la revisión."},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["reviewed_at"] is not None
    assert body["admin_notes"] == "Baja confirmada tras la revisión."
    assert body["member_name"] == f"{member.first_name} {member.last_name}".strip()
    assert body["member_email"] == member.email
    assert body["plan_name"] == plan.name

    db.refresh(member)
    request_row = db.get(CancellationRequest, created["id"])
    assert request_row is not None
    from app.models import Subscription

    sub = db.get(Subscription, request_row.subscription_id)
    assert sub is not None
    assert sub.status == SubscriptionStatus.CANCELLED
    assert member.is_active is False
    assert member.deactivated_at is not None

    member_booking = db.scalar(
        select(Booking).where(
            Booking.user_id == member.id, Booking.class_session_id == future.id
        )
    )
    db.refresh(waitlisted.booking)
    assert member_booking.status == BookingStatus.CANCELLED
    assert waitlisted.booking.status == BookingStatus.CONFIRMED

    login = client.post(
        LOGIN_URL, data={"username": member.email, "password": TEST_PASSWORD}
    )
    assert login.status_code == 401


def test_rn13_reject_without_admin_notes_returns_422(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    created = _pending_via_api(client, member)

    missing = client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={},
        headers=auth_header_for(admin),
    )
    empty = client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={"admin_notes": ""},
        headers=auth_header_for(admin),
    )

    assert missing.status_code == 422
    assert empty.status_code == 422
    request = db.get(CancellationRequest, created["id"])
    assert request is not None
    assert request.status == CancellationStatus.PENDING


def test_rn13_reject_with_notes_keeps_member_active(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    created = _pending_via_api(client, member)

    response = client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={"admin_notes": "Hablemos antes de irte"},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["admin_notes"] == "Hablemos antes de irte"
    db.refresh(member)
    assert member.is_active is True
    assert member.deactivated_at is None


def test_list_cancellation_requests_filters_and_paginates(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    first = _pending_via_api(client, member, reason="Primera")
    client.post(
        f"{CANCEL_URL}/{first['id']}/reject",
        json={"admin_notes": "Espera"},
        headers=auth_header_for(admin),
    )
    second = _pending_via_api(client, member, reason="Segunda")

    all_resp = client.get(CANCEL_URL, headers=auth_header_for(admin))
    pending_resp = client.get(
        CANCEL_URL, params={"status": "pending"}, headers=auth_header_for(admin)
    )
    page_resp = client.get(
        CANCEL_URL, params={"page": 1, "size": 1}, headers=auth_header_for(admin)
    )

    assert all_resp.status_code == 200
    assert all_resp.json()["total"] == 2
    assert pending_resp.status_code == 200
    assert pending_resp.json()["total"] == 1
    pending_item = pending_resp.json()["items"][0]
    assert pending_item["id"] == second["id"]
    assert pending_item["member_name"] == f"{member.first_name} {member.last_name}".strip()
    assert pending_item["member_email"] == member.email
    assert pending_item["plan_name"]
    assert page_resp.json()["size"] == 1
    assert len(page_resp.json()["items"]) == 1


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_admin_endpoints_forbid_non_admin_roles(
    client, db, make_user, make_plan, make_subscription, role
):
    member = make_user()
    make_subscription(member, make_plan())
    created = _pending_via_api(client, member)
    actor = make_user(role)
    headers = auth_header_for(actor)

    assert client.get(CANCEL_URL, headers=headers).status_code == 403
    assert client.post(
        f"{CANCEL_URL}/{created['id']}/approve", headers=headers
    ).status_code == 403
    assert client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={"admin_notes": "No"},
        headers=headers,
    ).status_code == 403


def test_admin_endpoints_without_token_return_401(client, db, make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())
    created = _pending_via_api(client, member)

    assert client.get(CANCEL_URL).status_code == 401
    assert client.post(f"{CANCEL_URL}/{created['id']}/approve").status_code == 401
    assert client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={"admin_notes": "No"},
    ).status_code == 401


def test_approve_unknown_and_non_pending_statuses(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    admin = make_user(RoleName.ADMIN)
    created = _pending_via_api(client, member)
    client.post(
        f"{CANCEL_URL}/{created['id']}/reject",
        json={"admin_notes": "No ahora"},
        headers=auth_header_for(admin),
    )

    missing = client.post(
        f"{CANCEL_URL}/99999/approve", headers=auth_header_for(admin)
    )
    again = client.post(
        f"{CANCEL_URL}/{created['id']}/approve", headers=auth_header_for(admin)
    )

    assert missing.status_code == 404
    assert again.status_code == 409


@pytest.mark.parametrize("role", [RoleName.ADMIN, RoleName.SUPERADMIN])
def test_admin_and_superadmin_can_approve(
    client, db, make_user, make_plan, make_subscription, role
):
    member = make_user()
    make_subscription(member, make_plan())
    reviewer = make_user(role)
    created = _pending_via_api(client, member)

    response = client.post(
        f"{CANCEL_URL}/{created['id']}/approve",
        headers=auth_header_for(reviewer),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"
