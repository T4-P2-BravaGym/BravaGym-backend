from pathlib import Path

from app.core.config import get_settings

MEDIA_URL_PREFIX = "/media"
PRODUCT_IMAGES_DIR = "products"


def product_images_dir() -> Path:
    return get_settings().media_root / PRODUCT_IMAGES_DIR


def product_image_url(file_name: str | None) -> str | None:
    if file_name is None:
        return None
    return f"{MEDIA_URL_PREFIX}/{PRODUCT_IMAGES_DIR}/{file_name}"
