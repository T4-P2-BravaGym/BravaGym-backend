"""HU-17.1: exercise catalog CRUD for trainers."""

import pytest
from app.models.enums import RoleName

EXERCISES_URL = "/api/v1/exercises"
SQUAT = {"name": "Sentadilla trasera", "muscle_group": "Piernas"}


def test_trainer_creates_an_exercise(client, auth_headers):
    response = client.post(
        EXERCISES_URL, json=SQUAT, headers=auth_headers(RoleName.TRAINER)
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Sentadilla trasera"


def test_duplicated_exercise_name_returns_409(client, auth_headers):
    headers = auth_headers(RoleName.TRAINER)
    client.post(EXERCISES_URL, json=SQUAT, headers=headers)

    response = client.post(
        EXERCISES_URL, json=SQUAT, headers=headers
    )  # same name again

    assert response.status_code == 409


def test_trainer_lists_and_updates_an_exercise(client, auth_headers):
    headers = auth_headers(RoleName.TRAINER)
    exercise_id = client.post(EXERCISES_URL, json=SQUAT, headers=headers).json()["id"]

    response = client.patch(
        f"{EXERCISES_URL}/{exercise_id}",
        json={"muscle_group": "Glúteos"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["muscle_group"] == "Glúteos"
    assert response.json()["name"] == "Sentadilla trasera"  # not sent, not changed
    assert len(client.get(EXERCISES_URL, headers=headers).json()) == 1


def test_trainer_deletes_an_unused_exercise(client, auth_headers):
    headers = auth_headers(RoleName.TRAINER)
    exercise_id = client.post(EXERCISES_URL, json=SQUAT, headers=headers).json()["id"]

    assert (
        client.delete(f"{EXERCISES_URL}/{exercise_id}", headers=headers).status_code
        == 204
    )
    assert (
        client.get(f"{EXERCISES_URL}/{exercise_id}", headers=headers).status_code == 404
    )


def test_exercise_with_empty_name_returns_422(client, auth_headers):
    response = client.post(
        EXERCISES_URL,
        json={"name": "", "muscle_group": "Piernas"},
        headers=auth_headers(RoleName.TRAINER),
    )

    assert response.status_code == 422


def test_exercises_without_token_returns_401(client):
    assert client.get(EXERCISES_URL).status_code == 401


# parametrize runs the same test once per role
@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.ADMIN])
def test_only_trainers_manage_exercises(client, auth_headers, role):
    response = client.post(EXERCISES_URL, json=SQUAT, headers=auth_headers(role))

    assert response.status_code == 403
