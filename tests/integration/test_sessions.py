"""Integration tests for GET /sessions (HU-10.2 / HU-10.3)."""

from datetime import datetime, timedelta, timezone

from app.models import Booking, ClassSession, ClassType
from app.models.enums import BookingStatus, RoleName, SessionStatus
from tests.conftest import auth_header_for

SESSIONS_URL = "/api/v1/sessions"


def _seed_week(db, make_user):
    trainer = make_user(RoleName.TRAINER)
    strength = ClassType(name="Fuerza total", description="Sentadilla y peso muerto.")
    olympic = ClassType(
        name="Taller de halterofilia",
        description="Técnica de arrancada.",
        extra_price_cents=1200,
    )
    db.add_all([strength, olympic])
    db.flush()

    monday = datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc)
    open_session = ClassSession(
        class_type=strength,
        trainer=trainer,
        starts_at=monday,
        capacity=3,
    )
    full_session = ClassSession(
        class_type=strength,
        trainer=trainer,
        starts_at=monday + timedelta(hours=10),
        capacity=1,
    )
    priced_session = ClassSession(
        class_type=olympic,
        trainer=trainer,
        starts_at=monday + timedelta(days=1, hours=10, minutes=30),
        capacity=8,
    )
    cancelled = ClassSession(
        class_type=strength,
        trainer=trainer,
        starts_at=monday + timedelta(days=3),
        capacity=10,
        status=SessionStatus.CANCELLED,
    )
    db.add_all([open_session, full_session, priced_session, cancelled])
    db.flush()

    member = make_user(RoleName.MEMBER)
    db.add(Booking(user=member, class_session=full_session, status=BookingStatus.CONFIRMED))
    db.commit()

    return {
        "trainer": trainer,
        "strength": strength,
        "olympic": olympic,
        "open_session": open_session,
        "full_session": full_session,
        "priced_session": priced_session,
        "cancelled": cancelled,
        "monday": monday,
    }


def test_get_sessions_is_public_and_returns_page_shape(client, db, make_user):
    data = _seed_week(db, make_user)

    response = client.get(SESSIONS_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "size"}
    assert body["page"] == 1
    assert body["size"] == 20
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert data["cancelled"].id not in {item["id"] for item in body["items"]}


def test_get_sessions_filters_from_to_and_shows_free_spots(client, db, make_user):
    data = _seed_week(db, make_user)
    monday = data["monday"]

    response = client.get(
        SESSIONS_URL,
        params={
            "from": monday.isoformat().replace("+00:00", "Z"),
            "to": (monday + timedelta(hours=12)).isoformat().replace("+00:00", "Z"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    by_id = {item["id"]: item for item in body["items"]}

    open_item = by_id[data["open_session"].id]
    assert open_item["free_spots"] == 3
    assert open_item["capacity"] == 3
    assert open_item["class_type"]["extra_price_cents"] == 0

    full_item = by_id[data["full_session"].id]
    assert full_item["free_spots"] == 0


def test_get_sessions_only_available_excludes_full(client, db, make_user):
    data = _seed_week(db, make_user)

    response = client.get(SESSIONS_URL, params={"only_available": True})

    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert data["full_session"].id not in ids
    assert data["open_session"].id in ids
    assert data["priced_session"].id in ids
    assert body["total"] == 2


def test_get_sessions_shows_extra_price_when_present(client, db, make_user):
    data = _seed_week(db, make_user)

    response = client.get(
        SESSIONS_URL,
        params={"class_type_id": data["olympic"].id},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == data["priced_session"].id
    assert item["class_type"]["name"] == "Taller de halterofilia"
    assert item["class_type"]["extra_price_cents"] == 1200
    assert item["free_spots"] == 8


def test_get_sessions_paginates(client, db, make_user):
    _seed_week(db, make_user)

    first = client.get(SESSIONS_URL, params={"page": 1, "size": 2})
    second = client.get(SESSIONS_URL, params={"page": 2, "size": 2})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["total"] == 3
    assert len(first.json()["items"]) == 2
    assert len(second.json()["items"]) == 1
    assert first.json()["items"][0]["id"] != second.json()["items"][0]["id"]


def test_get_sessions_inverted_range_returns_422_in_spanish(client, db, make_user):
    _seed_week(db, make_user)

    response = client.get(
        SESSIONS_URL,
        params={
            "from": "2026-10-10T00:00:00Z",
            "to": "2026-10-01T00:00:00Z",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert "from" in body["detail"]
    assert "to" in body["detail"]


def test_get_sessions_still_works_with_auth_header(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    _seed_week(db, make_user)

    response = client.get(SESSIONS_URL, headers=auth_header_for(member))

    assert response.status_code == 200
    assert response.json()["total"] >= 1
