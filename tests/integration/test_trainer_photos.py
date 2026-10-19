"""T-291: a trainer uploads and removes her own photo; the public list shows it."""

import pytest
from app.core.config import get_settings
from app.models.enums import RoleName
from app.services.image_files import IMAGE_TOO_LARGE, INVALID_IMAGE, MAX_IMAGE_BYTES

from tests.conftest import auth_header_for
from tests.image_samples import JPEG, PDF, PNG, SVG

PHOTO_URL = "/api/v1/trainers/me/photo"
URL_PREFIX = "/media/trainers/"


@pytest.fixture(autouse=True)
def photos_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_root", tmp_path)
    return tmp_path / "trainers"


def upload(client, user, data, filename="foto.jpg", content_type="image/jpeg"):
    return client.put(
        PHOTO_URL,
        headers=auth_header_for(user),
        files={"file": (filename, data, content_type)},
    )


def stored(photos_dir):
    return sorted(path.name for path in photos_dir.glob("*"))


def public_photo(client, trainer):
    cards = client.get("/api/v1/trainers").json()
    return next(card["photo_url"] for card in cards if card["id"] == trainer.id)


def test_a_trainer_uploads_her_photo_and_the_list_shows_it(
    client, make_user, photos_dir
):
    trainer = make_user(RoleName.TRAINER)

    response = upload(client, trainer, JPEG)

    assert response.status_code == 200
    photo_url = response.json()["photo_url"]
    assert photo_url.startswith(URL_PREFIX) and photo_url.endswith(".jpg")
    assert stored(photos_dir) == [photo_url.removeprefix(URL_PREFIX)]
    assert public_photo(client, trainer) == photo_url


def test_a_new_photo_replaces_the_old_file(client, make_user, photos_dir):
    trainer = make_user(RoleName.TRAINER)
    upload(client, trainer, JPEG)

    response = upload(client, trainer, PNG, "otra.png", "image/png")

    new_name = response.json()["photo_url"].removeprefix(URL_PREFIX)
    assert new_name.endswith(".png")
    assert stored(photos_dir) == [new_name]


def test_removing_the_photo_goes_back_to_the_initials(client, make_user, photos_dir):
    trainer = make_user(RoleName.TRAINER)
    upload(client, trainer, JPEG)

    response = client.delete(PHOTO_URL, headers=auth_header_for(trainer))

    assert response.status_code == 200
    assert response.json()["photo_url"] is None
    assert stored(photos_dir) == []
    assert public_photo(client, trainer) is None


def test_removing_without_a_photo_changes_nothing(client, make_user):
    trainer = make_user(RoleName.TRAINER)

    response = client.delete(PHOTO_URL, headers=auth_header_for(trainer))

    assert response.status_code == 200
    assert response.json()["photo_url"] is None


@pytest.mark.parametrize(
    ("data", "filename"), [(PDF, "foto.jpg"), (SVG, "foto.svg"), (b"", "vacia.jpg")]
)
def test_a_file_that_is_not_an_image_returns_422(
    client, make_user, photos_dir, data, filename
):
    trainer = make_user(RoleName.TRAINER)

    response = upload(client, trainer, data, filename)

    assert response.status_code == 422
    assert response.json() == {"detail": INVALID_IMAGE, "code": "invalid_image"}
    assert stored(photos_dir) == []


def test_a_photo_over_2_mb_returns_422(client, make_user, photos_dir):
    trainer = make_user(RoleName.TRAINER)
    data = JPEG + bytes(MAX_IMAGE_BYTES - len(JPEG) + 1)

    response = upload(client, trainer, data)

    assert response.status_code == 422
    assert response.json() == {"detail": IMAGE_TOO_LARGE, "code": "image_too_large"}
    assert stored(photos_dir) == []


def test_a_member_cannot_upload_a_trainer_photo(client, make_user):
    member = make_user(RoleName.MEMBER)

    assert upload(client, member, JPEG).status_code == 403


def test_uploading_without_a_token_returns_401(client):
    response = client.put(PHOTO_URL, files={"file": ("foto.jpg", JPEG, "image/jpeg")})

    assert response.status_code == 401
