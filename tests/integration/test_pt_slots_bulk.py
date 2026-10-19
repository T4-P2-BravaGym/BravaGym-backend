from datetime import UTC, datetime

import pytest
from app.models import ClassSession, ClassType
from app.models.enums import RoleName, SessionStatus
from app.services import session_service

from tests.conftest import auth_header_for

BULK_URL = "/api/v1/sessions/personal-training/bulk"

MONDAY = "2026-10-19"


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    monkeypatch.setattr(
        session_service, "utc_now", lambda: datetime(2026, 10, 18, 10, 0)
    )


def _pt_type(db, name="Entrenamiento personal bulk"):
    pt_type = ClassType(name=name, description="Individual.", is_personal_training=True)
    db.add(pt_type)
    db.commit()
    return pt_type


def _body(**overrides):
    body = {"weekdays": [0, 2, 4], "times": ["11:00"], "start_date": MONDAY, "weeks": 2}
    body.update(overrides)
    return body


def _pt_sessions(db, trainer):
    return db.query(ClassSession).filter(ClassSession.trainer_id == trainer.id).all()


def test_trainer_opens_weekly_slots(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)

    response = client.post(BULK_URL, headers=auth_header_for(trainer), json=_body())

    assert response.status_code == 201
    body = response.json()
    assert body["skipped"] == []
    assert len(body["created"]) == 6
    for slot in body["created"]:
        assert slot["capacity"] == 1
        assert slot["duration_minutes"] == 60
        assert slot["free_spots"] == 1
        assert slot["trainer_id"] == trainer.id
        assert slot["class_type"]["is_personal_training"] is True
    starts = [slot["starts_at"] for slot in body["created"]]
    assert starts == sorted(starts)
    assert len(_pt_sessions(db, trainer)) == 6


def test_slots_keep_madrid_hour_across_dst_change(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)

    response = client.post(
        BULK_URL, headers=auth_header_for(trainer), json=_body(weekdays=[0])
    )

    assert response.status_code == 201
    starts = [slot["starts_at"] for slot in response.json()["created"]]
    assert starts[0].startswith("2026-10-19T09:00:00")
    assert starts[1].startswith("2026-10-26T10:00:00")


def test_overlapping_slot_is_skipped_and_the_rest_created(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)
    group = ClassType(name="Fuerza bulk", description="Grupo.")
    db.add(group)
    db.flush()
    db.add(
        ClassSession(
            class_type=group,
            trainer=trainer,
            starts_at=datetime(2026, 10, 21, 9, 30, tzinfo=UTC),
            duration_minutes=60,
            capacity=8,
        )
    )
    db.commit()

    response = client.post(BULK_URL, headers=auth_header_for(trainer), json=_body())

    assert response.status_code == 201
    body = response.json()
    assert len(body["created"]) == 5
    assert len(body["skipped"]) == 1
    assert body["skipped"][0]["reason"] == "overlap"
    assert body["skipped"][0]["starts_at"].startswith("2026-10-21T09:00:00")


def test_cancelled_session_does_not_block_a_slot(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)
    group = ClassType(name="Fuerza cancelada", description="Grupo.")
    db.add(group)
    db.flush()
    db.add(
        ClassSession(
            class_type=group,
            trainer=trainer,
            starts_at=datetime(2026, 10, 19, 9, 0, tzinfo=UTC),
            duration_minutes=60,
            capacity=8,
            status=SessionStatus.CANCELLED,
        )
    )
    db.commit()

    response = client.post(
        BULK_URL, headers=auth_header_for(trainer), json=_body(weekdays=[0], weeks=1)
    )

    assert response.status_code == 201
    assert len(response.json()["created"]) == 1


def test_slots_in_the_same_batch_cannot_overlap(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)

    response = client.post(
        BULK_URL,
        headers=auth_header_for(trainer),
        json=_body(weekdays=[0], times=["11:00", "11:30"], weeks=1),
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["created"]) == 1
    assert body["skipped"][0]["reason"] == "overlap"
    assert body["skipped"][0]["starts_at"].startswith("2026-10-19T09:30:00")


def test_past_slots_are_skipped(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)

    response = client.post(
        BULK_URL,
        headers=auth_header_for(trainer),
        json=_body(weekdays=[4], start_date="2026-10-16"),
    )

    assert response.status_code == 201
    body = response.json()
    assert [slot["reason"] for slot in body["skipped"]] == ["past"]
    assert body["skipped"][0]["starts_at"].startswith("2026-10-16T09:00:00")
    assert len(body["created"]) == 1
    assert body["created"][0]["starts_at"].startswith("2026-10-23T09:00:00")


def test_bulk_requires_token(client, db):
    _pt_type(db)

    response = client.post(BULK_URL, json=_body())

    assert response.status_code == 401


def test_member_cannot_open_bulk_slots(client, db, make_user):
    member = make_user()
    _pt_type(db)

    response = client.post(BULK_URL, headers=auth_header_for(member), json=_body())

    assert response.status_code == 403
    assert db.query(ClassSession).count() == 0


def test_bulk_without_active_pt_type_returns_404(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)

    response = client.post(BULK_URL, headers=auth_header_for(trainer), json=_body())

    assert response.status_code == 404
    assert _pt_sessions(db, trainer) == []


def test_bulk_with_non_pt_class_type_returns_422(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    group = ClassType(name="Grupo no PT", description="Grupo.")
    db.add(group)
    db.commit()

    response = client.post(
        BULK_URL, headers=auth_header_for(trainer), json=_body(class_type_id=group.id)
    )

    assert response.status_code == 422
    assert _pt_sessions(db, trainer) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"weekdays": []},
        {"weekdays": [7]},
        {"times": []},
        {"times": ["08:00", "09:00", "10:00", "11:00", "12:00"]},
        {"weeks": 0},
        {"weeks": 9},
        {"start_date": "not-a-date"},
    ],
)
def test_bulk_rejects_invalid_body(client, db, make_user, overrides):
    trainer = make_user(RoleName.TRAINER)
    _pt_type(db)

    response = client.post(
        BULK_URL, headers=auth_header_for(trainer), json=_body(**overrides)
    )

    assert response.status_code == 422
    assert _pt_sessions(db, trainer) == []
