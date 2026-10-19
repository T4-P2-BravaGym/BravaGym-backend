from pathlib import Path

from app.core.config import get_settings

MEDIA_URL_PREFIX = "/media"
PRODUCT_IMAGES_DIR = "products"
TRAINER_PHOTOS_DIR = "trainers"  # T-291


def _media_url(folder: str, file_name: str | None) -> str | None:
    if file_name is None:
        return None
    return f"{MEDIA_URL_PREFIX}/{folder}/{file_name}"


def product_images_dir() -> Path:
    return get_settings().media_root / PRODUCT_IMAGES_DIR


def product_image_url(file_name: str | None) -> str | None:
    return _media_url(PRODUCT_IMAGES_DIR, file_name)


def trainer_photos_dir() -> Path:
    return get_settings().media_root / TRAINER_PHOTOS_DIR


def trainer_photo_url(file_name: str | None) -> str | None:
    return _media_url(TRAINER_PHOTOS_DIR, file_name)
