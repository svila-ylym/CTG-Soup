import asyncio
from io import BytesIO
from types import SimpleNamespace

from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
import pytest
from sqlalchemy.exc import SQLAlchemyError
from starlette.datastructures import Headers

import app.services.public_storage as public_storage
from app.api.uploads import upload_image
from app.core.config import Settings
from app.services.public_storage import (
    LocalPublicStorage,
    PublicStorageError,
    R2PublicStorage,
)


def _r2_settings(**overrides):
    values = {
        "_env_file": None,
        "PUBLIC_STORAGE_BACKEND": "r2",
        "R2_ENDPOINT_URL": "https://account-id.r2.cloudflarestorage.com",
        "R2_BUCKET_NAME": "ctg-public",
        "R2_REGION": "auto",
        "R2_ACCESS_KEY_ID": "test-access-key",
        "R2_SECRET_ACCESS_KEY": "test-secret-key",
        "R2_PUBLIC_BASE_URL": "https://assets.example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_settings_local_storage_does_not_require_r2_credentials():
    settings = Settings(_env_file=None, PUBLIC_STORAGE_BACKEND="local")

    assert settings.PUBLIC_STORAGE_BACKEND == "local"


def test_settings_r2_storage_requires_all_environment_values():
    with pytest.raises(ValidationError, match="R2_SECRET_ACCESS_KEY"):
        _r2_settings(R2_SECRET_ACCESS_KEY=None)


def test_settings_validation_error_never_contains_r2_secret(monkeypatch):
    sentinel_secret = "sentinel-secret-must-not-appear"
    environment = {
        "PUBLIC_STORAGE_BACKEND": "r2",
        "R2_ENDPOINT_URL": "https://account-id.r2.cloudflarestorage.com",
        "R2_BUCKET_NAME": "ctg-public",
        "R2_REGION": "auto",
        "R2_ACCESS_KEY_ID": "test-access-key",
        "R2_SECRET_ACCESS_KEY": sentinel_secret,
    }
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("R2_PUBLIC_BASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)

    assert sentinel_secret not in str(exc_info.value)


def test_settings_representation_never_contains_r2_secret():
    sentinel_secret = "sentinel-secret-must-not-appear"

    settings = _r2_settings(R2_SECRET_ACCESS_KEY=sentinel_secret)

    assert sentinel_secret not in repr(settings)


def test_settings_r2_endpoint_must_be_account_origin_without_bucket_path():
    with pytest.raises(ValidationError, match="R2_ENDPOINT_URL"):
        _r2_settings(R2_ENDPOINT_URL="https://account-id.r2.cloudflarestorage.com/ctg-public")


def test_settings_r2_public_url_must_be_https_origin():
    with pytest.raises(ValidationError, match="R2_PUBLIC_BASE_URL"):
        _r2_settings(R2_PUBLIC_BASE_URL="http://assets.example.com/images")


@pytest.mark.parametrize("overrides,error_field", [
    ({"R2_PUBLIC_BASE_URL": "https://assets.example.com?"}, "R2_PUBLIC_BASE_URL"),
    ({"R2_PUBLIC_BASE_URL": "https://assets.example.com#"}, "R2_PUBLIC_BASE_URL"),
    ({"R2_PUBLIC_BASE_URL": "https://assets.example.com:not-a-port"}, "R2_PUBLIC_BASE_URL"),
    ({"R2_ENDPOINT_URL": "https://account-id.r2.cloudflarestorage.com?"}, "R2_ENDPOINT_URL"),
])
def test_settings_r2_origins_reject_delimiters_and_invalid_ports(overrides, error_field):
    with pytest.raises(ValidationError, match=error_field):
        _r2_settings(**overrides)


def test_settings_r2_public_url_is_normalized_without_trailing_slash():
    settings = _r2_settings(R2_PUBLIC_BASE_URL="https://assets.example.com/")

    assert settings.r2_public_base_url == "https://assets.example.com"


def test_local_storage_writes_and_deletes_object(tmp_path):
    storage = LocalPublicStorage(tmp_path)

    storage.put("images/7/avatar.png", b"png-bytes", "image/png")

    stored_file = tmp_path / "images/7/avatar.png"
    assert stored_file.read_bytes() == b"png-bytes"
    assert storage.public_url("images/7/avatar.png") == "/storage/images/7/avatar.png"

    storage.delete("images/7/avatar.png")
    assert not stored_file.exists()


def test_local_storage_defers_directory_creation_until_write(tmp_path):
    root = tmp_path / "public"

    storage = LocalPublicStorage(root)

    assert not root.exists()
    storage.put("images/7/avatar.png", b"png-bytes", "image/png")
    assert root.exists()


class _FakeS3Client:
    def __init__(self):
        self.put_calls = []
        self.delete_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)

    def delete_object(self, **kwargs):
        self.delete_calls.append(kwargs)


def test_r2_storage_uses_bucket_and_public_domain_without_acl():
    settings = _r2_settings()
    client = _FakeS3Client()
    storage = R2PublicStorage(settings, client=client)

    storage.put("images/7/avatar.png", b"png-bytes", "image/png")
    storage.delete("images/7/avatar.png")

    assert client.put_calls == [{
        "Bucket": "ctg-public",
        "Key": "images/7/avatar.png",
        "Body": b"png-bytes",
        "ContentType": "image/png",
        "CacheControl": "public, max-age=31536000, immutable",
    }]
    assert client.delete_calls == [{
        "Bucket": "ctg-public",
        "Key": "images/7/avatar.png",
    }]
    assert storage.public_url("images/7/avatar.png") == "https://assets.example.com/images/7/avatar.png"


def test_r2_storage_wraps_client_construction_failure_on_write():
    def fail_client_factory(*_args, **_kwargs):
        raise RuntimeError("client unavailable")

    storage = R2PublicStorage(_r2_settings(), client_factory=fail_client_factory)

    with pytest.raises(PublicStorageError, match="write failed"):
        storage.put("images/7/avatar.png", b"png-bytes", "image/png")


def test_public_storage_factory_reuses_provider(monkeypatch, tmp_path):
    settings = Settings(
        _env_file=None,
        PUBLIC_STORAGE_BACKEND="local",
        LOCAL_STORAGE_DIR=str(tmp_path),
    )
    monkeypatch.setattr(public_storage, "get_settings", lambda: settings)
    public_storage.get_public_storage.cache_clear()

    try:
        assert public_storage.get_public_storage() is public_storage.get_public_storage()
    finally:
        public_storage.get_public_storage.cache_clear()


def _image_upload():
    return UploadFile(
        filename="avatar.png",
        file=BytesIO(b"png-bytes"),
        headers=Headers({"content-type": "image/png"}),
    )


class _RecordingStorage:
    name = "r2"

    def __init__(self, fail_put=False):
        self.fail_put = fail_put
        self.put_calls = []
        self.deleted_keys = []

    def put(self, key, content, content_type):
        if self.fail_put:
            raise PublicStorageError("unavailable")
        self.put_calls.append((key, content, content_type))

    def delete(self, key):
        self.deleted_keys.append(key)

    def public_url(self, key):
        return f"https://assets.example.com/{key}"


class _RecordingSession:
    def __init__(self, fail_commit=False, fail_refresh=False, fail_rollback=False):
        self.fail_commit = fail_commit
        self.fail_refresh = fail_refresh
        self.fail_rollback = fail_rollback
        self.added = []
        self.commit_called = False
        self.flush_called = False
        self.rollback_called = False

    def add(self, value):
        self.added.append(value)

    def flush(self):
        self.flush_called = True
        self.added[0].id = 41

    def commit(self):
        self.commit_called = True
        if self.fail_commit:
            raise SQLAlchemyError("commit failed")

    def refresh(self, value):
        if self.fail_refresh:
            raise SQLAlchemyError("refresh failed")

    def rollback(self):
        self.rollback_called = True
        if self.fail_rollback:
            raise SQLAlchemyError("rollback failed")


def test_upload_stores_public_url_and_provider_name():
    storage = _RecordingStorage()
    session = _RecordingSession()

    result = asyncio.run(upload_image(
        file=_image_upload(),
        current_user=SimpleNamespace(uid=7),
        db=session,
        storage=storage,
    ))

    key, content, content_type = storage.put_calls[0]
    assert key.startswith("images/7/")
    assert key.endswith(".png")
    assert content == b"png-bytes"
    assert content_type == "image/png"
    assert session.added[0].public_url == f"https://assets.example.com/{key}"
    assert result["storage"] == "r2"
    assert result["url"] == f"https://assets.example.com/{key}"


def test_upload_storage_failure_returns_503_without_database_row():
    storage = _RecordingStorage(fail_put=True)
    session = _RecordingSession()

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(upload_image(
            file=_image_upload(),
            current_user=SimpleNamespace(uid=7),
            db=session,
            storage=storage,
        ))

    assert exc_info.value.status_code == 503
    assert session.added == []


def test_upload_database_failure_deletes_new_object():
    storage = _RecordingStorage()
    session = _RecordingSession(fail_commit=True)

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        asyncio.run(upload_image(
            file=_image_upload(),
            current_user=SimpleNamespace(uid=7),
            db=session,
            storage=storage,
        ))

    assert session.rollback_called is True
    assert storage.deleted_keys == [storage.put_calls[0][0]]


def test_upload_refresh_failure_happens_before_commit_and_deletes_object():
    storage = _RecordingStorage()
    session = _RecordingSession(fail_refresh=True)

    with pytest.raises(SQLAlchemyError, match="refresh failed"):
        asyncio.run(upload_image(
            file=_image_upload(),
            current_user=SimpleNamespace(uid=7),
            db=session,
            storage=storage,
        ))

    assert session.flush_called is True
    assert session.commit_called is False
    assert storage.deleted_keys == [storage.put_calls[0][0]]


def test_upload_rollback_failure_does_not_skip_cleanup_or_replace_commit_error():
    storage = _RecordingStorage()
    session = _RecordingSession(fail_commit=True, fail_rollback=True)

    with pytest.raises(SQLAlchemyError, match="commit failed"):
        asyncio.run(upload_image(
            file=_image_upload(),
            current_user=SimpleNamespace(uid=7),
            db=session,
            storage=storage,
        ))

    assert storage.deleted_keys == [storage.put_calls[0][0]]
