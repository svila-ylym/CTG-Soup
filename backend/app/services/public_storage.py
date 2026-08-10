"""Storage providers for public user-uploaded assets."""

from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Protocol
from urllib.parse import quote

import boto3

from app.core.config import Settings, get_settings


class PublicStorageError(RuntimeError):
    """Raised when a public object cannot be written or removed."""


class PublicStorage(Protocol):
    name: str

    def put(self, key: str, content: bytes | BinaryIO, content_type: str) -> None:
        """Store one public object."""

    def delete(self, key: str) -> None:
        """Delete one public object."""

    def public_url(self, key: str) -> str:
        """Return the browser URL for one public object."""


def _read_content(content: bytes | BinaryIO) -> bytes:
    if isinstance(content, bytes):
        return content
    return content.read()


class LocalPublicStorage:
    name = "local"

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def put(self, key: str, content: bytes | BinaryIO, content_type: str) -> None:
        del content_type
        destination = self.root / key
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_read_content(content))
        except (OSError, ValueError) as exc:
            raise PublicStorageError("local public object write failed") from exc

    def delete(self, key: str) -> None:
        destination = self.root / key
        try:
            destination.unlink(missing_ok=True)
        except (OSError, ValueError) as exc:
            raise PublicStorageError("local public object delete failed") from exc

    def public_url(self, key: str) -> str:
        return "/storage/" + quote(key, safe="/")


class R2PublicStorage:
    name = "r2"

    def __init__(self, settings: Settings, client=None, client_factory=boto3.client):
        self.bucket = settings.R2_BUCKET_NAME
        self.public_base_url = settings.r2_public_base_url
        self.endpoint_url = settings.R2_ENDPOINT_URL
        self.region = settings.R2_REGION
        self.access_key_id = settings.R2_ACCESS_KEY_ID
        self.secret_access_key = settings.r2_secret_access_key
        self._client = client
        self._client_factory = client_factory

    def _get_client(self):
        if self._client is None:
            self._client = self._client_factory(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
            )
        return self._client

    def put(self, key: str, content: bytes | BinaryIO, content_type: str) -> None:
        try:
            self._get_client().put_object(
                Bucket=self.bucket,
                Key=key,
                Body=_read_content(content),
                ContentType=content_type,
                CacheControl="public, max-age=31536000, immutable",
            )
        except Exception as exc:
            raise PublicStorageError("R2 public object write failed") from exc

    def delete(self, key: str) -> None:
        try:
            self._get_client().delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            raise PublicStorageError("R2 public object delete failed") from exc

    def public_url(self, key: str) -> str:
        return f"{self.public_base_url}/{quote(key, safe='/')}"


@lru_cache(maxsize=1)
def get_public_storage() -> PublicStorage:
    settings = get_settings()
    if settings.PUBLIC_STORAGE_BACKEND == "r2":
        return R2PublicStorage(settings)

    root = Path(settings.LOCAL_STORAGE_DIR)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    return LocalPublicStorage(root)
