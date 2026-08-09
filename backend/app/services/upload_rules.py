from pathlib import PurePath

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def validate_upload(content_type: str, filename: str, size: int) -> str:
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("仅支持 JPG、PNG、WebP 或 GIF 图片")
    if size <= 0 or size > MAX_IMAGE_BYTES:
        raise ValueError("图片大小必须在 1B 至 5MB 之间")
    suffix = PurePath(filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise ValueError("图片扩展名不受支持")
    return suffix
