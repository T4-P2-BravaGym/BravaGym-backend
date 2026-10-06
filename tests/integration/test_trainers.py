from app.core.security import create_access_token
from app.models import TrainerProfile
from app.models.enums import RoleName

TRAINERS_URL = "/api/v1/trainers"


def test_list_trainers_shows_the_public_profile_without_contact_data(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    trainer.trainer_profile = TrainerProfile(bio="Fuerza desde cero.", specialty="Powerlifting")
    db.commit()

    response = client.get(TRAINERS_URL)

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": trainer.id,
            "name": f"{trainer.first_name} {trainer.last_name}",
            "specialty": "Powerlifting",
            "bio": "Fuerza desde cero.",
        }
    ]


def test_list_trainers_hides_inactive_trainers_and_other_roles(client, make_user):
    active_trainer = make_user(RoleName.TRAINER)
    make_user(RoleName.TRAINER, is_active=False)
    make_user(RoleName.MEMBER)
    make_user(RoleName.ADMIN)

    response = client.get(TRAINERS_URL)

    assert [trainer["id"] for trainer in response.json()] == [active_trainer.id]


def test_list_trainers_works_for_a_trainer_without_profile(client, make_user):
    make_user(RoleName.TRAINER)

    response = client.get(TRAINERS_URL)

    assert response.status_code == 200
    assert response.json()[0]["specialty"] is None
    assert response.json()[0]["bio"] is None


MY_PROFILE_URL = "/api/v1/trainers/me/profile"   


def test_trainer_updates_her_specialty_and_bio(client, make_user):
    trainer = make_user(RoleName.TRAINER)
    headers = {"Authorization": f"Bearer {create_access_token(trainer.id, trainer.role.name)}"}

    response = client.patch(MY_PROFILE_URL, json={"specialty": "Halterofilia", "bio": "Técnica olímpica."}, headers=headers)

    assert response.status_code == 200
    assert response.json()["specialty"] == "Halterofilia"
    assert response.json()["bio"] == "Técnica olímpica."
    assert client.get(TRAINERS_URL).json()[0]["bio"] == "Técnica olímpica."


def test_trainer_can_change_only_her_bio(client, db, make_user):
    trainer = make_user(RoleName.TRAINER)
    trainer.trainer_profile = TrainerProfile(bio="Antes.", specialty="Powerlifting")
    db.commit()
    headers = {"Authorization": f"Bearer {create_access_token(trainer.id, trainer.role.name)}"}

    response = client.patch(MY_PROFILE_URL, json={"bio": "Después."}, headers=headers)

    assert response.json()["bio"] == "Después."
    assert response.json()["specialty"] == "Powerlifting"


def test_update_profile_without_token_returns_401(client):
    response = client.patch(MY_PROFILE_URL, json={"bio": "x"})

    assert response.status_code == 401


def test_member_cannot_update_a_trainer_profile_returns_403(client, auth_headers):
    response = client.patch(MY_PROFILE_URL, json={"bio": "x"}, headers=auth_headers(RoleName.MEMBER))

    assert response.status_code == 403


def test_specialty_longer_than_120_characters_returns_422(client, auth_headers):
    response = client.patch(MY_PROFILE_URL, json={"specialty": "a" * 121}, headers=auth_headers(RoleName.TRAINER))

    assert response.status_code == 422

