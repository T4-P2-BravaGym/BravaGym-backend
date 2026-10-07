"""Integration tests for POST /sessions/{id}/bookings and GET /bookings/me (HU-12)."""

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import func, select

from app.models import Booking, ClassSession, ClassType, Payment
from app.models.enums import PaymentStatus, RoleName, SessionStatus
from tests.conftest import auth_header_for

BOOK_URL = "/api/v1/sessions/{session_id}/bookings"
MY_BOOKINGS_URL = "/api/v1/bookings/me"


def _seed_session(
    db,
    make_user,
    *,
    capacity: int = 2,
    starts_at: datetime | None = None,
    status: SessionStatus = SessionStatus.SCHEDULED,
    extra_price_cents: int = 0,
    name: str = "Fuerza total",
) -> ClassSession:
    trainer = make_user(RoleName.TRAINER)
    class_type = ClassType(
        name=name,
        description="Clase de integración.",
        extra_price_cents=extra_price_cents,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=starts_at or (datetime(2026, 10, 10, 17, 30, tzinfo=timezone.utc)),
        capacity=capacity,
        status=status,
    )
    db.add(session)
    db.commit()
    return session


def test_rn02_member_with_spots_gets_confirmed_booking(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _seed_session(db, make_user, capacity=3, name="Confirmada API")

    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["waitlist_position"] is None
    assert body["class_session"]["id"] == session.id
    assert body["class_session"]["class_type"]["name"] == "Confirmada API"
    assert db.scalar(select(func.count()).select_from(Booking)) == 1


def test_rn02_full_class_returns_waitlisted_with_position(
    client, db, make_user, make_plan, make_subscription
):
    session = _seed_session(db, make_user, capacity=1, name="Lista espera API")
    plan = make_plan()

    first = make_user()
    make_subscription(first, plan)
    first_response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(first),
    )
    assert first_response.status_code == 201
    assert first_response.json()["status"] == "confirmed"

    second = make_user()
    make_subscription(second, plan)
    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(second),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "waitlisted"
    assert body["waitlist_position"] == 1


def test_rn03_duplicate_booking_returns_409(
    client, make_user, make_plan, make_subscription, db
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _seed_session(db, make_user, name="Duplicada API")
    headers = auth_header_for(member)
    assert client.post(BOOK_URL.format(session_id=session.id), headers=headers).status_code == 201

    response = client.post(BOOK_URL.format(session_id=session.id), headers=headers)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Ya tienes una reserva en esta clase.",
        "code": "conflict",
    }


def test_rn01_no_active_subscription_returns_403(
    client, db, make_user, make_plan
):
    member = make_user()
    session = _seed_session(db, make_user, name="Sin sub API")

    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Necesitas una suscripción activa para reservar.",
        "code": "forbidden",
    }
    assert db.scalar(select(func.count()).select_from(Booking)) == 0


def test_rn07_extra_price_creates_pending_payment_on_confirm(
    client, db, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _seed_session(
        db, make_user, capacity=2, extra_price_cents=1200, name="Extra API"
    )

    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )

    assert response.status_code == 201
    booking_id = response.json()["id"]
    payment = db.scalar(select(Payment).where(Payment.booking_id == booking_id))
    assert payment is not None
    assert payment.status == PaymentStatus.PENDING
    assert payment.base_amount_cents == 1200
    assert payment.final_amount_cents == 1200


@freeze_time("2026-10-07 12:00:00")
def test_rn04_past_session_returns_409(
    client, make_user, make_plan, make_subscription, db
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _seed_session(
        db,
        make_user,
        starts_at=datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc),
        name="Pasada API",
    )

    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


def test_book_missing_session_returns_404(
    client, make_user, make_plan, make_subscription
):
    member = make_user()
    make_subscription(member, make_plan())

    response = client.post(
        BOOK_URL.format(session_id=9999),
        headers=auth_header_for(member),
    )

    assert response.status_code == 404


def test_book_without_token_returns_401(client, db, make_user):
    session = _seed_session(db, make_user, name="Sin token")

    response = client.post(BOOK_URL.format(session_id=session.id))

    assert response.status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_can_book(client, db, auth_headers, make_user, role):
    session = _seed_session(db, make_user, name=f"Rol {role}")

    response = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_headers(role),
    )

    assert response.status_code == 403
    assert db.scalar(select(func.count()).select_from(Booking)) == 0


def test_get_my_bookings_returns_page_shape(
    client, make_user, make_plan, make_subscription, db
):
    member = make_user()
    make_subscription(member, make_plan())
    session = _seed_session(db, make_user, name="Mis reservas")
    client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )

    response = client.get(MY_BOOKINGS_URL, headers=auth_header_for(member))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["total"] == 1
    assert body["items"][0]["class_session"]["id"] == session.id


def test_get_my_bookings_filters_status_and_hides_others(
    client, make_user, make_plan, make_subscription, db
):
    plan = make_plan()
    session = _seed_session(db, make_user, capacity=1, name="Filtro status")
    member = make_user()
    other = make_user()
    make_subscription(member, plan)
    make_subscription(other, plan)

    client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(other),
    )
    waitlisted = client.post(
        BOOK_URL.format(session_id=session.id),
        headers=auth_header_for(member),
    )
    assert waitlisted.json()["status"] == "waitlisted"

    response = client.get(
        MY_BOOKINGS_URL,
        params={"status": "waitlisted"},
        headers=auth_header_for(member),
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "waitlisted"
    assert body["items"][0]["waitlist_position"] == 1


@freeze_time("2026-10-07 12:00:00")
def test_get_my_bookings_filters_upcoming(
    client, make_user, make_plan, make_subscription, db
):
    member = make_user()
    make_subscription(member, make_plan())
    past = _seed_session(
        db,
        make_user,
        starts_at=datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc),
        name="Futura filtro",
    )
    # Book future session while frozen "now" is before it
    client.post(
        BOOK_URL.format(session_id=past.id),
        headers=auth_header_for(member),
    )

    upcoming = client.get(
        MY_BOOKINGS_URL,
        params={"upcoming": True},
        headers=auth_header_for(member),
    )
    past_only = client.get(
        MY_BOOKINGS_URL,
        params={"upcoming": False},
        headers=auth_header_for(member),
    )

    assert upcoming.json()["total"] == 1
    assert past_only.json()["total"] == 0


def test_my_bookings_without_token_returns_401(client):
    assert client.get(MY_BOOKINGS_URL).status_code == 401


@pytest.mark.parametrize("role", [RoleName.TRAINER, RoleName.ADMIN, RoleName.SUPERADMIN])
def test_only_members_list_my_bookings(client, auth_headers, role):
    response = client.get(MY_BOOKINGS_URL, headers=auth_headers(role))
    assert response.status_code == 403
