import pytest

from app.services.upload_rules import validate_upload


def test_accepts_supported_image():
    assert validate_upload("image/png", "avatar.png", 1024) == ".png"


@pytest.mark.parametrize("content_type,filename,size", [
    ("application/pdf", "x.pdf", 10),
    ("image/png", "x.exe", 10),
    ("image/png", "x.png", 6 * 1024 * 1024),
])
def test_rejects_unsafe_uploads(content_type, filename, size):
    with pytest.raises(ValueError):
        validate_upload(content_type, filename, size)
