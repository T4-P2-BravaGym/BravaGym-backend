"""Photo files on disk, shared by product photos (HU-30) and trainer photos (T-291).

The type is read from the first bytes, never from the file name, and the name on disk is
always generated here, so a user can never choose a path.
"""

import logging
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.exceptions import ValidationAppError

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


def read_image(stream: BinaryIO) -> tuple[bytes, str]:
    """The bytes and the extension of an upload. 422 if it is too big or not an image."""
    data = stream.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageTooLargeError(IMAGE_TOO_LARGE)
    extension = detect_image_extension(data)
    if extension is None:
        raise InvalidImageError(INVALID_IMAGE)
    return data, extension


def save_image(folder: Path, data: bytes, extension: str) -> str:
    """Write the photo with a random name and return that name."""
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.{extension}"
    (folder / name).write_bytes(data)
    return name


def delete_image(folder: Path, file_name: str | None) -> None:
    """Delete an old photo. A file that cannot be deleted is logged, never an error."""
    if file_name is None:
        return
    path = folder / Path(file_name).name
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not delete photo %s", file_name, exc_info=True)
