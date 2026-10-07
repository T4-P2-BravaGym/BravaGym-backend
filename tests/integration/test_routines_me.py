from datetime import date

from sqlalchemy import select

from app.core.security import create_access_token
from app.models import Exercise, Routine, RoutineExercise
from app.models.enums import RoleName

MY_ROUTINE_URL = "/api/v1/routines/me"


def headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


def add_routine(db, member, trainer, *, is_active=True, name="Fuerza base"):
    """A routine with day 2 first and day 1 out of order, to check the API sorts it."""
    squat = db.scalar(select(Exercise).where(Exercise.name == "Sentadilla")) or Exercise(name="Sentadilla", muscle_group="Piernas")
    row = db.scalar(select(Exercise).where(Exercise.name == "Remo")) or Exercise(name="Remo", muscle_group="Espalda")
    routine = Routine(
        member=member,
        trainer=trainer,
        name=name,
        start_date=date(2026, 10, 5),
        is_active=is_active,
        items=[
            RoutineExercise(exercise=row, day_number=2, position=1, sets=3, reps=10, rest_seconds=90),
            RoutineExercise(exercise=squat, day_number=1, position=2, sets=4, reps=8, rest_seconds=120),
            RoutineExercise(exercise=row, day_number=1, position=1, sets=3, reps=12, rest_seconds=60),
        ],
    )
    db.add(routine)
    db.commit()
    return routine


def test_member_sees_her_routine_grouped_by_day_and_in_order(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)
    add_routine(db, member, trainer)

    response = client.get(MY_ROUTINE_URL, headers=headers_for(member))

    assert response.status_code == 200
    body = response.json()
    assert body["trainer_name"] == f"{trainer.first_name} {trainer.last_name}"
    assert [day["day_number"] for day in body["days"]] == [1, 2]
    assert [line["position"] for line in body["days"][0]["lines"]] == [1, 2]
    assert body["days"][0]["lines"][0] == {
        "position": 1,
        "exercise_name": "Remo",
        "sets": 3,
        "reps": 12,
        "rest_seconds": 60,
    }


def test_member_sees_only_her_active_routine(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)
    add_routine(db, member, trainer, is_active=False, name="Antigua")
    add_routine(db, member, trainer, name="Nueva")

    response = client.get(MY_ROUTINE_URL, headers=headers_for(member))

    assert response.json()["name"] == "Nueva"


def test_member_without_routine_gets_404_with_a_friendly_message(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.get(MY_ROUTINE_URL, headers=headers_for(member))

    assert response.status_code == 404
    assert response.json()["detail"].startswith("Todavía no tienes una rutina")


def test_member_never_sees_another_members_routine(client, db, make_user):
    member_a = make_user(RoleName.MEMBER)
    member_b = make_user(RoleName.MEMBER)
    add_routine(db, member_b, make_user(RoleName.TRAINER))

    response = client.get(MY_ROUTINE_URL, headers=headers_for(member_a))

    assert response.status_code == 404


def test_my_routine_without_token_returns_401(client):
    response = client.get(MY_ROUTINE_URL)

    assert response.status_code == 401


def test_trainer_cannot_use_my_routine_returns_403(client, auth_headers):
    response = client.get(MY_ROUTINE_URL, headers=auth_headers(RoleName.TRAINER))

    assert response.status_code == 403
    