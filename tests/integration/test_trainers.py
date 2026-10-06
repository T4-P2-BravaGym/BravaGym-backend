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
    