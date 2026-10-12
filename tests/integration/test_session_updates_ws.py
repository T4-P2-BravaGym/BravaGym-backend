"""Live free spots over websockets (HU-16)."""
from datetime import datetime, timezone

from app.core.realtime import session_updates
from app.models import ClassSession, ClassType
from app.models.enums import RoleName
from tests.conftest import auth_header_for

WS_URL = "/api/v1/ws/sessions/{session_id}"
BOOK_URL = "/api/v1/sessions/{session_id}/bookings"
CANCEL_URL = "/api/v1/bookings/{booking_id}/cancel"


def add_session(db, make_user, *, capacity=2, name="Fuerza en directo"):
    class_type = ClassType(name=name, extra_price_cents=0)
    session = ClassSession(
        class_type=class_type,
        trainer=make_user(RoleName.TRAINER),
        starts_at=datetime(2030, 1, 7, 18, 0, tzinfo=timezone.utc),
        capacity=capacity,
    )
    db.add(session)
    db.commit()
    return session


def member_with_plan(make_user, make_plan, make_subscription):
    member = make_user()
    make_subscription(member, make_plan())
    return member


def test_watchers_hear_when_someone_books(client, db, make_user, make_plan, make_subscription):
    session = add_session(db, make_user)
    member = member_with_plan(make_user, make_plan, make_subscription)

    with client.websocket_connect(WS_URL.format(session_id=session.id)) as websocket:
        client.post(BOOK_URL.format(session_id=session.id), headers=auth_header_for(member))
        message = websocket.receive_json()

    assert message == {"type": "session_updated", "session_id": session.id}


def test_watchers_hear_when_someone_cancels(client, db, make_user, make_plan, make_subscription):
    session = add_session(db, make_user)
    member = member_with_plan(make_user, make_plan, make_subscription)
    booking = client.post(BOOK_URL.format(session_id=session.id), headers=auth_header_for(member)).json()

    with client.websocket_connect(WS_URL.format(session_id=session.id)) as websocket:
        client.post(CANCEL_URL.format(booking_id=booking["id"]), headers=auth_header_for(member))
        message = websocket.receive_json()

    assert message == {"type": "session_updated", "session_id": session.id}


def test_waitlist_promotion_is_also_announced(client, db, make_user, make_plan, make_subscription):
    session = add_session(db, make_user, capacity=1)
    first = member_with_plan(make_user, make_plan, make_subscription)
    second = member_with_plan(make_user, make_plan, make_subscription)
    booking = client.post(BOOK_URL.format(session_id=session.id), headers=auth_header_for(first)).json()
    client.post(BOOK_URL.format(session_id=session.id), headers=auth_header_for(second))  # waitlisted

    with client.websocket_connect(WS_URL.format(session_id=session.id)) as websocket:
        client.post(CANCEL_URL.format(booking_id=booking["id"]), headers=auth_header_for(first))
        message = websocket.receive_json()

    assert message["session_id"] == session.id


def test_websocket_is_public_and_forgets_the_client_when_it_leaves(client, db, make_user):
    session = add_session(db, make_user)

    with client.websocket_connect(WS_URL.format(session_id=session.id)):
        assert session_updates.watchers(session.id) == 1

    assert session_updates.watchers(session.id) == 0


def test_a_booking_only_reaches_watchers_of_that_session(client, db, make_user, make_plan, make_subscription):
    watched = add_session(db, make_user, name="Vista")
    other = add_session(db, make_user, name="Otra")
    member = member_with_plan(make_user, make_plan, make_subscription)

    with client.websocket_connect(WS_URL.format(session_id=watched.id)) as websocket:
        client.post(BOOK_URL.format(session_id=other.id), headers=auth_header_for(member))
        client.post(BOOK_URL.format(session_id=watched.id), headers=auth_header_for(member))
        message = websocket.receive_json()

     # The first message is about the watched session, not the other one
    assert message["session_id"] == watched.id

    