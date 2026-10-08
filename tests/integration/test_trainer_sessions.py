"""Integration tests for trainer session management (HU-11.3 / HU-11.4)."""

from datetime import datetime, timedelta, timezone

from app.models import Booking, ClassSession, ClassType, Payment
from app.models.enums import BookingStatus, PaymentStatus, RoleName, SessionStatus
from tests.conftest import auth_header_for

SESSIONS_URL = "/api/v1/sessions"


def _seed_type(db, name: str = "Fuerza trainer") -> ClassType:
    class_type = ClassType(name=name, description="Tipo de integración.")
    db.add(class_type)
    db.commit()
    return class_type


def test_post_session_without_token_returns_401(client, db):
    class_type = _seed_type(db)
    response = client.post(
        SESSIONS_URL,
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-08T17:30:00Z",
            "duration_minutes": 60,
            "capacity": 12,
        },
    )
    assert response.status_code == 401


def test_post_session_member_returns_403(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    class_type = _seed_type(db, name="Member bloqueado")
    response = client.post(
        SESSIONS_URL,
        headers=auth_header_for(member),
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-08T17:30:00Z",
            "duration_minutes": 60,
            "capacity": 12,
        },
    )
    assert response.status_code == 403


def test_trainer_creates_session_201(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = _seed_type(db, name="Crear sesión")

    response = client.post(
        SESSIONS_URL,
        headers=auth_header_for(trainer),
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-08T17:30:00Z",
            "duration_minutes": 60,
            "capacity": 12,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["trainer_id"] == trainer.id
    assert body["capacity"] == 12
    assert body["status"] == "scheduled"
    assert body["free_spots"] == 12
    assert body["class_type"]["id"] == class_type.id


def test_rn09_overlap_returns_409_spanish(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    class_type = _seed_type(db, name="Solape API")
    headers = auth_header_for(trainer)
    starts = "2026-10-08T10:00:00Z"

    first = client.post(
        SESSIONS_URL,
        headers=headers,
        json={
            "class_type_id": class_type.id,
            "starts_at": starts,
            "duration_minutes": 60,
            "capacity": 10,
        },
    )
    assert first.status_code == 201

    overlap = client.post(
        SESSIONS_URL,
        headers=headers,
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-08T10:30:00Z",
            "duration_minutes": 60,
            "capacity": 8,
        },
    )
    assert overlap.status_code == 409
    body = overlap.json()
    assert body["code"] == "conflict"
    assert "solapa" in body["detail"].lower()


def test_rn10_other_trainer_patch_returns_403(client, db, make_user):
    owner = make_user(RoleName.TRAINER)
    other = make_user(RoleName.TRAINER)
    class_type = _seed_type(db, name="Propiedad API")

    created = client.post(
        SESSIONS_URL,
        headers=auth_header_for(owner),
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-09T09:00:00Z",
            "duration_minutes": 60,
            "capacity": 8,
        },
    )
    assert created.status_code == 201
    session_id = created.json()["id"]

    response = client.patch(
        f"{SESSIONS_URL}/{session_id}",
        headers=auth_header_for(other),
        json={"capacity": 6},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_rn10_superadmin_can_patch_and_cancel(client, db, make_user):
    owner = make_user(RoleName.TRAINER)
    superadmin = make_user(RoleName.SUPERADMIN)
    class_type = _seed_type(db, name="Superadmin API")

    created = client.post(
        SESSIONS_URL,
        headers=auth_header_for(owner),
        json={
            "class_type_id": class_type.id,
            "starts_at": "2026-10-09T11:00:00Z",
            "duration_minutes": 60,
            "capacity": 8,
        },
    )
    session_id = created.json()["id"]

    patched = client.patch(
        f"{SESSIONS_URL}/{session_id}",
        headers=auth_header_for(superadmin),
        json={"capacity": 5},
    )
    assert patched.status_code == 200
    assert patched.json()["capacity"] == 5

    cancelled = client.post(
        f"{SESSIONS_URL}/{session_id}/cancel",
        headers=auth_header_for(superadmin),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_cancel_session_cancels_bookings(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    member = make_user(RoleName.MEMBER)
    class_type = ClassType(
        name="Cancelar con reservas",
        description="Con pago extra.",
        extra_price_cents=1200,
    )
    db.add(class_type)
    db.flush()
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=datetime(2026, 10, 11, 18, 0, tzinfo=timezone.utc),
        capacity=4,
    )
    db.add(session)
    db.flush()
    booking = Booking(
        user=member,
        class_session=session,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.flush()
    payment = Payment(
        user_id=member.id,
        booking_id=booking.id,
        base_amount_cents=1200,
        final_amount_cents=1200,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()

    response = client.post(
        f"{SESSIONS_URL}/{session.id}/cancel",
        headers=auth_header_for(trainer),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    db.refresh(booking)
    db.refresh(payment)
    db.refresh(session)
    assert session.status == SessionStatus.CANCELLED
    assert booking.status == BookingStatus.CANCELLED
    assert payment.status == PaymentStatus.REFUNDED


def test_get_session_bookings_trainer_and_permissions(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    other = make_user(RoleName.TRAINER)
    admin = make_user(RoleName.ADMIN)
    member = make_user(RoleName.MEMBER)
    class_type = _seed_type(db, name="Roster")
    session = ClassSession(
        class_type=class_type,
        trainer=trainer,
        starts_at=datetime.now(timezone.utc) + timedelta(days=2),
        capacity=4,
    )
    db.add(session)
    db.flush()
    db.add(
        Booking(
            user=member,
            class_session=session,
            status=BookingStatus.CONFIRMED,
        )
    )
    db.commit()

    own = client.get(
        f"{SESSIONS_URL}/{session.id}/bookings",
        headers=auth_header_for(trainer),
    )
    assert own.status_code == 200
    assert len(own.json()) == 1
    assert own.json()[0]["user"]["id"] == member.id
    assert own.json()[0]["status"] == "confirmed"

    admin_view = client.get(
        f"{SESSIONS_URL}/{session.id}/bookings",
        headers=auth_header_for(admin),
    )
    assert admin_view.status_code == 200

    forbidden = client.get(
        f"{SESSIONS_URL}/{session.id}/bookings",
        headers=auth_header_for(other),
    )
    assert forbidden.status_code == 403

    member_view = client.get(
        f"{SESSIONS_URL}/{session.id}/bookings",
        headers=auth_header_for(member),
    )
    assert member_view.status_code == 403

    anonymous = client.get(f"{SESSIONS_URL}/{session.id}/bookings")
    assert anonymous.status_code == 401
