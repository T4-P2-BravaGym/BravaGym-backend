import pytest

from app.core.config import get_settings
from app.models.enums import RoleName
from app.services.product_image_service import (
    IMAGE_TOO_LARGE,
    INVALID_IMAGE,
    MAX_IMAGE_BYTES,
)
from tests.image_samples import EXE, JPEG, PDF, PNG, SVG, WEBP

PRODUCTS_URL = "/api/v1/products"
URL_PREFIX = "/media/products/"


@pytest.fixture(autouse=True)
def images_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "media_root", tmp_path)
    return tmp_path / "products"


@pytest.fixture
def admin_headers(auth_headers):
    return auth_headers(RoleName.ADMIN)


@pytest.fixture
def product(make_product):
    return make_product(name="Proteína whey 1 kg", stock=20)


def _image_endpoint(product_id: int) -> str:
    return f"{PRODUCTS_URL}/{product_id}/image"


def _upload(
    client, product_id, data, headers, filename="foto.jpg", content_type="image/jpeg"
):
    return client.put(
        _image_endpoint(product_id),
        headers=headers,
        files={"file": (filename, data, content_type)},
    )


def _call(client, method: str, product_id: int, headers: dict):
    if method == "put":
        return _upload(client, product_id, JPEG, headers)
    return client.delete(_image_endpoint(product_id), headers=headers)


def _file_name(response) -> str:
    return response.json()["image_url"].removeprefix(URL_PREFIX)


def _stored(images_dir) -> list[str]:
    return sorted(path.name for path in images_dir.glob("*"))


def _shop_image_url(client) -> str | None:
    return client.get(PRODUCTS_URL).json()["items"][0]["image_url"]


@pytest.mark.parametrize(
    ("data", "extension"), [(JPEG, "jpg"), (PNG, "png"), (WEBP, "webp")]
)
def test_admin_uploads_a_photo_and_the_type_comes_from_its_bytes(
    client, admin_headers, product, images_dir, data, extension
):
    # Always sent as "foto.jpg" with image/jpeg: only the bytes decide the type.
    response = _upload(client, product.id, data, admin_headers)

    assert response.status_code == 200
    assert response.json()["image_url"].startswith(URL_PREFIX)
    file_name = _file_name(response)
    assert file_name.endswith(f".{extension}")
    assert (images_dir / file_name).read_bytes() == data


def test_superadmin_can_upload_a_photo(client, auth_headers, product):
    response = _upload(client, product.id, JPEG, auth_headers(RoleName.SUPERADMIN))

    assert response.status_code == 200


def test_the_original_file_name_is_never_used(
    client, admin_headers, product, images_dir
):
    response = _upload(
        client, product.id, JPEG, admin_headers, filename="../../brava.jpg"
    )

    file_name = _file_name(response)
    assert "brava" not in file_name
    assert len(file_name.removesuffix(".jpg")) == 32
    assert _stored(images_dir) == [file_name]


def test_the_shop_shows_the_new_photo_right_away(client, admin_headers, product):
    assert _shop_image_url(client) is None  # this request fills the cache (HU-28)

    response = _upload(client, product.id, JPEG, admin_headers)

    assert _shop_image_url(client) == response.json()["image_url"]


@pytest.mark.parametrize(
    ("data", "filename", "content_type"),
    [
        (SVG, "logo.svg", "image/svg+xml"),
        (PDF, "factura.pdf", "application/pdf"),
        (EXE, "foto.jpg", "image/jpeg"),
        (b"", "vacia.jpg", "image/jpeg"),
    ],
)
def test_a_file_that_is_not_a_real_image_returns_422(
    client, admin_headers, product, images_dir, db, data, filename, content_type
):
    response = _upload(client, product.id, data, admin_headers, filename, content_type)

    assert response.status_code == 422
    assert response.json() == {"detail": INVALID_IMAGE, "code": "invalid_image"}
    assert _stored(images_dir) == []
    db.refresh(product)
    assert product.image_path is None


def test_a_photo_of_exactly_2_mb_is_accepted(client, admin_headers, product):
    data = JPEG + bytes(MAX_IMAGE_BYTES - len(JPEG))

    response = _upload(client, product.id, data, admin_headers)

    assert response.status_code == 200


def test_a_photo_over_2_mb_returns_422(client, admin_headers, product, images_dir):
    data = JPEG + bytes(MAX_IMAGE_BYTES - len(JPEG) + 1)

    response = _upload(client, product.id, data, admin_headers)

    assert response.status_code == 422
    assert response.json() == {"detail": IMAGE_TOO_LARGE, "code": "image_too_large"}
    assert _stored(images_dir) == []


def test_a_rejected_upload_keeps_the_previous_photo(
    client, admin_headers, product, images_dir
):
    first = _upload(client, product.id, JPEG, admin_headers)

    response = _upload(
        client, product.id, SVG, admin_headers, "logo.svg", "image/svg+xml"
    )

    assert response.status_code == 422
    assert _shop_image_url(client) == first.json()["image_url"]
    assert _stored(images_dir) == [_file_name(first)]


def test_a_new_photo_replaces_the_old_one_and_deletes_its_file(
    client, admin_headers, product, images_dir
):
    first = _upload(client, product.id, JPEG, admin_headers)

    second = _upload(client, product.id, PNG, admin_headers)

    assert second.status_code == 200
    assert _file_name(first) != _file_name(second)
    assert _stored(images_dir) == [_file_name(second)]


def test_replacing_works_when_the_old_file_is_already_gone(
    client, admin_headers, product, images_dir, db
):
    product.image_path = "deleted-by-hand.jpg"
    db.commit()

    response = _upload(client, product.id, JPEG, admin_headers)

    assert response.status_code == 200
    assert _stored(images_dir) == [_file_name(response)]


def test_admin_removes_the_photo(client, admin_headers, product, images_dir):
    _upload(client, product.id, JPEG, admin_headers)
    assert _shop_image_url(client) is not None  # fills the cache

    response = client.delete(_image_endpoint(product.id), headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["image_url"] is None
    assert _stored(images_dir) == []
    assert _shop_image_url(client) is None


def test_removing_when_there_is_no_photo_changes_nothing(
    client, admin_headers, product
):
    response = client.delete(_image_endpoint(product.id), headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["image_url"] is None


def test_an_inactive_product_can_get_a_photo(client, admin_headers, make_product):
    product = make_product(is_active=False)

    response = _upload(client, product.id, JPEG, admin_headers)

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.parametrize("method", ["put", "delete"])
def test_unknown_product_returns_404(client, admin_headers, method):
    response = _call(client, method, 999, admin_headers)

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["put", "delete"])
@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_members_and_trainers_get_403(
    client, auth_headers, product, images_dir, method, role
):
    response = _call(client, method, product.id, auth_headers(role))

    assert response.status_code == 403
    assert _stored(images_dir) == []


@pytest.mark.parametrize("method", ["put", "delete"])
def test_without_token_returns_401(client, product, images_dir, method):
    response = _call(client, method, product.id, {})

    assert response.status_code == 401
    assert _stored(images_dir) == []


def test_a_failed_save_leaves_no_file_behind(
    client, admin_headers, product, images_dir, db, monkeypatch
):
    def broken_commit():
        raise RuntimeError("database is down")

    monkeypatch.setattr(db, "commit", broken_commit)

    with pytest.raises(RuntimeError):
        _upload(client, product.id, JPEG, admin_headers)

    assert _stored(images_dir) == []


def test_an_unknown_media_file_returns_404(client):
    assert client.get(f"{URL_PREFIX}nada.jpg").status_code == 404
