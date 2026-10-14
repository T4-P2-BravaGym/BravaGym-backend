"""HU-17.2: trainers create routines with lines for a member."""
import pytest
from sqlalchemy import select

from app.models import Exercise, Routine
from app.models.enums import RoleName
from tests.conftest import auth_header_for

ROUTINES_URL = "/api/v1/routines"


@pytest.fixture
def exercises(db):
    """Two exercises in the catalog (criterion 1: 'given the exercise catalog')."""
    squat = Exercise(name="Sentadilla", muscle_group="Piernas")
    row = Exercise(name="Remo", muscle_group="Espalda")
    db.add_all([squat, row])
    db.commit()
    return squat, row


def routine_body(member_id, exercises, name="Fuerza base"):
    """A valid request body with two lines on day 1. Each test changes what it needs."""
    squat, row = exercises
    return {
        "member_id": member_id,
        "name": name,
        "start_date": "2026-10-13",
        "lines": [
            {"exercise_id": squat.id, "day_number": 1, "position": 1, "sets": 4, "reps": 6, "rest_seconds": 150},
            {"exercise_id": row.id, "day_number": 1, "position": 2, "sets": 3, "reps": 10},
        ],
    }


# ---------- Criterion 1: the routine is saved with its lines ----------

def test_trainer_creates_a_routine_with_its_lines(client, make_user, exercises):
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)

    response = client.post(ROUTINES_URL, json=routine_body(member.id, exercises), headers=auth_header_for(trainer))

    assert response.status_code == 201
    body = response.json()
    assert body["member_id"] == member.id
    assert body["is_active"] is True
    assert body["trainer_name"] == f"{trainer.first_name} {trainer.last_name}"
    lines = body["days"][0]["lines"]
    assert [line["exercise_name"] for line in lines] == ["Sentadilla", "Remo"]
    assert lines[1]["rest_seconds"] == 60  # default rest when not sent


# ---------- Criterion 2: same day and position returns 409 ----------

def test_two_lines_with_same_day_and_position_return_409(client, make_user, exercises, db):
    member = make_user(RoleName.MEMBER)
    body = routine_body(member.id, exercises)
    body["lines"][1]["position"] = 1  # same day 1, position 1 as the first line

    response = client.post(ROUTINES_URL, json=body, headers=auth_header_for(make_user(RoleName.TRAINER)))

    assert response.status_code == 409
    assert db.scalar(select(Routine)) is None  # nothing was saved


def test_adding_a_line_in_a_taken_slot_returns_409(client, make_user, exercises):
    headers = auth_header_for(make_user(RoleName.TRAINER))
    member = make_user(RoleName.MEMBER)
    routine_id = client.post(ROUTINES_URL, json=routine_body(member.id, exercises), headers=headers).json()["id"]
    line = {"exercise_id": exercises[0].id, "day_number": 1, "position": 2, "sets": 3, "reps": 8}  # slot taken

    response = client.post(f"{ROUTINES_URL}/{routine_id}/exercises", json=line, headers=headers)

    assert response.status_code == 409


# ---------- Criterion 3: a new routine deactivates the previous one ----------

def test_new_routine_deactivates_the_previous_one(client, make_user, exercises, db):
    headers = auth_header_for(make_user(RoleName.TRAINER))
    member = make_user(RoleName.MEMBER)
    old_id = client.post(ROUTINES_URL, json=routine_body(member.id, exercises, "Antigua"), headers=headers).json()["id"]

    client.post(ROUTINES_URL, json=routine_body(member.id, exercises, "Nueva"), headers=headers)

    routines = client.get(ROUTINES_URL, params={"member_id": member.id}, headers=headers).json()
    active = {routine["name"]: routine["is_active"] for routine in routines}
    assert active == {"Antigua": False, "Nueva": True}
    assert db.get(Routine, old_id).is_active is False


def test_new_routine_does_not_touch_other_members(client, make_user, exercises):
    """Deactivating must only affect the same member."""
    headers = auth_header_for(make_user(RoleName.TRAINER))
    member_a = make_user(RoleName.MEMBER)
    member_b = make_user(RoleName.MEMBER)
    client.post(ROUTINES_URL, json=routine_body(member_a.id, exercises), headers=headers)

    client.post(ROUTINES_URL, json=routine_body(member_b.id, exercises), headers=headers)

    routines_a = client.get(ROUTINES_URL, params={"member_id": member_a.id}, headers=headers).json()
    assert routines_a[0]["is_active"] is True


# ---------- Rest of the CRUD ----------

def test_trainer_adds_and_removes_a_line(client, make_user, exercises):
    headers = auth_header_for(make_user(RoleName.TRAINER))
    member = make_user(RoleName.MEMBER)
    routine_id = client.post(ROUTINES_URL, json=routine_body(member.id, exercises), headers=headers).json()["id"]
    line = {"exercise_id": exercises[1].id, "day_number": 2, "position": 1, "sets": 3, "reps": 12}

    added = client.post(f"{ROUTINES_URL}/{routine_id}/exercises", json=line, headers=headers)
    new_line_id = added.json()["days"][1]["lines"][0]["id"]  # days[1] = day 2
    removed = client.delete(f"{ROUTINES_URL}/{routine_id}/exercises/{new_line_id}", headers=headers)

    assert added.status_code == 201
    assert removed.status_code == 204
    assert len(client.get(f"{ROUTINES_URL}/{routine_id}", headers=headers).json()["days"]) == 1


def test_delete_routine_only_deactivates_it(client, make_user, exercises, db):
    headers = auth_header_for(make_user(RoleName.TRAINER))
    member = make_user(RoleName.MEMBER)
    routine_id = client.post(ROUTINES_URL, json=routine_body(member.id, exercises), headers=headers).json()["id"]

    response = client.delete(f"{ROUTINES_URL}/{routine_id}", headers=headers)

    assert response.status_code == 204
    assert db.get(Routine, routine_id).is_active is False  # still in the database


# ---------- Error paths ----------

def test_routine_for_a_non_member_returns_404(client, make_user, exercises):
    trainer = make_user(RoleName.TRAINER)

    # The trainer tries to assign a routine to herself
    response = client.post(ROUTINES_URL, json=routine_body(trainer.id, exercises), headers=auth_header_for(trainer))

    assert response.status_code == 404


def test_routine_with_unknown_exercise_returns_404(client, make_user, exercises):
    member = make_user(RoleName.MEMBER)
    body = routine_body(member.id, exercises)
    body["lines"][0]["exercise_id"] = 999

    response = client.post(ROUTINES_URL, json=body, headers=auth_header_for(make_user(RoleName.TRAINER)))

    assert response.status_code == 404


def test_routine_with_day_8_returns_422(client, make_user, exercises):
    member = make_user(RoleName.MEMBER)
    body = routine_body(member.id, exercises)
    body["lines"][0]["day_number"] = 8  # the week has 7 days

    response = client.post(ROUTINES_URL, json=body, headers=auth_header_for(make_user(RoleName.TRAINER)))

    assert response.status_code == 422


# ---------- Security ----------

def test_trainer_cannot_be_impersonated_from_the_body(client, make_user, exercises):
    """trainer_id comes from the token: an extra field in the body is ignored."""
    trainer = make_user(RoleName.TRAINER)
    other_trainer = make_user(RoleName.TRAINER)
    member = make_user(RoleName.MEMBER)
    body = routine_body(member.id, exercises) | {"trainer_id": other_trainer.id}  # | merges two dicts

    response = client.post(ROUTINES_URL, json=body, headers=auth_header_for(trainer))

    assert response.json()["trainer_name"] == f"{trainer.first_name} {trainer.last_name}"


def test_routines_without_token_returns_401(client):
    assert client.post(ROUTINES_URL, json={}).status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.ADMIN])
def test_only_trainers_create_routines(client, make_user, exercises, role):
    member = make_user(RoleName.MEMBER)

    response = client.post(ROUTINES_URL, json=routine_body(member.id, exercises), headers=auth_header_for(make_user(role)))

    assert response.status_code == 403