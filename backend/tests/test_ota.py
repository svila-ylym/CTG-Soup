from pathlib import Path
import stat

import pytest
from fastapi import Request, Response

from app import main
from app.core.config import Settings
from app.services import ota


def _settings(tmp_path: Path, **values) -> Settings:
    return Settings(
        SECRET_KEY="x" * 32,
        DATABASE_URL="postgresql://postgres:postgres@localhost/test",
        APP_VERSION_OVERRIDE="1.2.3",
        UPDATE_REPOSITORY_PATH=str(tmp_path),
        **values,
    )


def test_version_comparison_handles_release_prefixes_and_prereleases():
    assert ota.normalize_version("v1.2.3") == "1.2.3"
    assert ota.compare_versions("1.2.3", "1.2.4") == "update_available"
    assert ota.compare_versions("1.2.3", "v1.2.3") == "up_to_date"
    assert ota.compare_versions("1.2.4", "1.2.3") == "ahead"
    assert ota.compare_versions("1.2.3", "release-1") == "invalid_latest_version"


@pytest.mark.asyncio
async def test_latest_release_service_reads_only_latest_and_caches(monkeypatch, tmp_path):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "v1.3.0",
                "name": "CTG 1.3.0",
                "published_at": "2026-08-11T00:00:00Z",
                "html_url": "https://github.com/svila-ylym/CTG-Soup/releases/tag/v1.3.0",
            }

    class Client:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url, headers):
            calls.append((url, headers))
            return Response()

    monkeypatch.setattr(ota.httpx, "AsyncClient", Client)
    service = ota.LatestReleaseService(_settings(tmp_path))

    first = await service.check()
    second = await service.check()

    assert first.update_available is True
    assert first.latest_version == "1.3.0"
    assert second == first
    assert len(calls) == 1
    assert calls[0][0].endswith("/repos/svila-ylym/CTG-Soup/releases/latest")


def test_update_script_is_fixed_to_repository_root(tmp_path):
    script = tmp_path / "Update.sh"
    script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    script.chmod(0o755)
    settings = _settings(tmp_path)

    assert ota._update_script(settings) == script

    outside = tmp_path.parent / "Update.sh"
    outside.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    outside.chmod(0o755)
    settings = _settings(tmp_path, UPDATE_SCRIPT_PATH=str(outside))
    with pytest.raises(ValueError):
        ota._update_script(settings)


def test_update_task_ids_cannot_escape_log_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(ota, "get_settings", lambda: _settings(tmp_path))

    assert ota.get_task("../../outside") is None
    with pytest.raises(ValueError):
        ota._task_state_path("../../outside", _settings(tmp_path))


def test_update_task_state_is_written_with_private_permissions(tmp_path):
    settings = _settings(tmp_path)
    task = {"task_id": "a" * 32, "status": "queued"}

    ota._write_task_state(task, settings)

    path = ota._task_state_path(task["task_id"], settings)
    assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.asyncio
async def test_maintenance_marker_blocks_business_requests(tmp_path, monkeypatch):
    marker = tmp_path / ".ota-maintenance"
    marker.write_text("maintenance", encoding="utf-8")
    monkeypatch.setattr(main, "maintenance_state_path", lambda: marker)

    async def call_next(_request):
        return Response("ok")

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/turtle-soups",
        "raw_path": b"/api/turtle-soups",
        "query_string": b"",
        "headers": [],
        "client": ("test", 123),
        "server": ("testserver", 80),
    }
    response = await main.ota_maintenance_mode(Request(scope), call_next)

    assert response.status_code == 503
    assert response.headers["retry-after"] == "60"


@pytest.mark.asyncio
async def test_maintenance_marker_allows_update_task_polling(tmp_path, monkeypatch):
    marker = tmp_path / ".ota-maintenance"
    marker.write_text("maintenance", encoding="utf-8")
    monkeypatch.setattr(main, "maintenance_state_path", lambda: marker)

    async def call_next(_request):
        return Response("ok", status_code=204)

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/admin/update/tasks/" + "a" * 32,
        "raw_path": b"/api/admin/update/tasks/",
        "query_string": b"",
        "headers": [],
        "client": ("test", 123),
        "server": ("testserver", 80),
    }
    response = await main.ota_maintenance_mode(Request(scope), call_next)

    assert response.status_code == 204
