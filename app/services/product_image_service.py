import logging
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.cache import invalidate_products_cache
from app.core.exceptions import ValidationAppError
from app.core.media import product_images_dir
from app.models import Product
from app.services.shop_service import get_product

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 2 * 1024 * 1024

INVALID_IMAGE = "La foto tiene que ser una imagen JPEG, PNG o WebP."
IMAGE_TOO_LARGE = "La foto no puede pesar más de 2 MB."


class InvalidImageError(ValidationAppError):
    code = "invalid_image"


class ImageTooLargeError(ValidationAppError):
    code = "image_too_large"


def detect_image_extension(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _read_image(stream: BinaryIO) -> tuple[bytes, str]:
    data = stream.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(IMAGE_TOO_LARGE)
    extension = detect_image_extension(data)
    if extension is None:
        raise InvalidImageError(INVALID_IMAGE)
    return data, extension


def _delete_file(file_name: str | None) -> None:
    if file_name is None:
        return
    path = product_images_dir() / Path(file_name).name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not delete product photo %s", file_name, exc_info=True)


def set_product_image(db: Session, product_id: int, stream: BinaryIO) -> Product:
    product = get_product(db, product_id)
    data, extension = _read_image(stream)

    folder = product_images_dir()
    folder.mkdir(parents=True, exist_ok=True)
    new_name = f"{uuid4().hex}.{extension}"
    new_path = folder / new_name
    new_path.write_bytes(data)

    old_name = product.image_path
    product.image_path = new_name
    try:
        db.commit()
    except Exception:
        db.rollback()
        new_path.unlink(missing_ok=True)
        raise
    db.refresh(product)

    _delete_file(old_name)
    invalidate_products_cache()
    logger.info(
        "Set photo of product %s (%s, %s bytes)", product.id, extension, len(data)
    )
    return product


def remove_product_image(db: Session, product_id: int) -> Product:
    product = get_product(db, product_id)
    old_name = product.image_path
    if old_name is None:
        return product

    product.image_path = None
    db.commit()
    db.refresh(product)

    _delete_file(old_name)
    invalidate_products_cache()
    logger.info("Removed photo of product %s", product.id)
    return product