import pytest
from app.services.product_image_service import detect_image_extension

from tests.image_samples import EXE, JPEG, PDF, PNG, SVG, WEBP


@pytest.mark.parametrize(
    ("data", "extension"), [(JPEG, "jpg"), (PNG, "png"), (WEBP, "webp")]
)
def test_detects_jpeg_png_and_webp_by_signature(data, extension):
    assert detect_image_extension(data) == extension


@pytest.mark.parametrize(
    "data",
    [
        b"",
        SVG,
        PDF,
        EXE,
        b"GIF89a" + bytes(16),
        b"RIFF\x24\x00\x00\x00WAVEfmt " + bytes(16),
        b"\xff\xd8",
    ],
)
def test_anything_else_is_not_an_image(data):
    assert detect_image_extension(data) is None
