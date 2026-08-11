"""GitHub Latest Release checks and controlled Update.sh execution."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_VERSION_PATTERN = re.compile(
    r"^[vV]?(?P<major>0|[1-9]\d*)"
    r"(?:\.(?P<minor>0|[1-9]\d*))?"
    r"(?:\.(?P<patch>0|[1-9]\d*))?"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)
_TASK_LOCK = threading.Lock()
_TASKS: dict[str, dict[str, Any]] = {}


def repository_root(settings: Settings | None = None) -> Path:
    configured = (settings or get_settings()).UPDATE_REPOSITORY_PATH
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[3]


def _version_parts(value: str) -> tuple[int, int, int, tuple[int, Any]] | None:
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    prerelease = match.group("prerelease")
    if prerelease is None:
        pre_key: tuple[int, Any] = (1, ())
    else:
        identifiers: list[Any] = []
        for identifier in prerelease.split("."):
            identifiers.append((0, int(identifier)) if identifier.isdigit() else (1, identifier))
        pre_key = (0, tuple(identifiers))
    return (
        int(match.group("major")),
        int(match.group("minor") or 0),
        int(match.group("patch") or 0),
        pre_key,
    )


def normalize_version(value: str) -> str:
    """Normalize a release tag for display while preserving prerelease text."""
    return value.strip().lstrip("vV")


def compare_versions(current: str, latest: str) -> str:
    current_parts = _version_parts(current)
    latest_parts = _version_parts(latest)
    if latest_parts is None:
        return "invalid_latest_version"
    if current_parts is None:
        return "unknown_current_version"
    if latest_parts > current_parts:
        return "update_available"
    if latest_parts == current_parts:
        return "up_to_date"
    return "ahead"


@dataclass(frozen=True)
class LatestReleaseResult:
    current_version: str
    latest_version: str | None
    tag_name: str | None
    release_name: str | None
    published_at: str | None
    html_url: str | None
    status: str
    update_available: bool
    checked_at: str
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "tag_name": self.tag_name,
            "release_name": self.release_name,
            "published_at": self.published_at,
            "html_url": self.html_url,
            "status": self.status,
            "update_available": self.update_available,
            "checked_at": self.checked_at,
            "error": self.error,
        }


class LatestReleaseService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._cached: LatestReleaseResult | None = None
        self._cached_at: float = 0
        self._lock = asyncio.Lock()

    @property
    def endpoint(self) -> str:
        return (
            f"{self.settings.GITHUB_API_URL.rstrip('/')}/repos/"
            f"{self.settings.GITHUB_REPOSITORY.strip('/')}/releases/latest"
        )

    async def check(self, force: bool = False) -> LatestReleaseResult:
        now = asyncio.get_running_loop().time()
        if (
            not force
            and self._cached is not None
            and now - self._cached_at < self.settings.GITHUB_RELEASE_CACHE_SECONDS
        ):
            return self._cached

        async with self._lock:
            now = asyncio.get_running_loop().time()
            if (
                not force
                and self._cached is not None
                and now - self._cached_at < self.settings.GITHUB_RELEASE_CACHE_SECONDS
            ):
                return self._cached
            result = await self._fetch_latest()
            self._cached = result
            self._cached_at = asyncio.get_running_loop().time()
            return result

    async def _fetch_latest(self) -> LatestReleaseResult:
        checked_at = datetime.now(timezone.utc).isoformat()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "CTG-Soup-OTA",
        }
        if self.settings.GITHUB_API_TOKEN:
            headers["Authorization"] = f"Bearer {self.settings.GITHUB_API_TOKEN.get_secret_value()}"
        try:
            async with httpx.AsyncClient(timeout=self.settings.GITHUB_API_TIMEOUT_SECONDS, follow_redirects=True) as client:
                response = await client.get(self.endpoint, headers=headers)
            response.raise_for_status()
            payload = response.json()
            tag_name = str(payload.get("tag_name") or "").strip()
            latest_version = normalize_version(tag_name) if tag_name else None
            status_value = compare_versions(self.settings.APP_VERSION, latest_version or "")
            return LatestReleaseResult(
                current_version=self.settings.APP_VERSION,
                latest_version=latest_version,
                tag_name=tag_name or None,
                release_name=str(payload.get("name") or tag_name or "") or None,
                published_at=payload.get("published_at"),
                html_url=payload.get("html_url"),
                status=status_value,
                update_available=status_value == "update_available",
                checked_at=checked_at,
                error=None if status_value not in {"invalid_latest_version", "unknown_current_version"} else "GitHub Release tag 不是有效版本号",
            )
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("GitHub Latest Release check failed: %s", type(exc).__name__)
            return LatestReleaseResult(
                current_version=self.settings.APP_VERSION,
                latest_version=None,
                tag_name=None,
                release_name=None,
                published_at=None,
                html_url=None,
                status="error",
                update_available=False,
                checked_at=checked_at,
                error="无法读取 GitHub Latest Release",
            )


latest_release_service = LatestReleaseService()


def maintenance_state_path(settings: Settings | None = None) -> Path:
    return repository_root(settings) / "private-storage" / ".ota-maintenance"


def _update_script(settings: Settings) -> Path:
    configured = settings.UPDATE_SCRIPT_PATH
    path = Path(configured).expanduser().resolve() if configured else repository_root(settings) / "Update.sh"
    root = repository_root(settings)
    if path.parent != root or path.name != "Update.sh":
        raise ValueError("UPDATE_SCRIPT_PATH must point to the repository Update.sh")
    if not path.is_file() or not path.stat().st_mode & 0o111:
        raise ValueError("Update.sh 不存在或不可执行")
    return path


def _task_state_path(task_id: str, settings: Settings | None = None) -> Path:
    if re.fullmatch(r"[0-9a-f]{32}", task_id) is None:
        raise ValueError("invalid update task id")
    settings = settings or get_settings()
    root = repository_root(settings)
    log_dir = Path(settings.UPDATE_LOG_DIR).expanduser()
    if not log_dir.is_absolute():
        log_dir = root / log_dir
    return log_dir / f"update-{task_id}.json"


def _write_task_state(task: dict[str, Any], settings: Settings | None = None) -> None:
    path = _task_state_path(task["task_id"], settings)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(task, ensure_ascii=False), encoding="utf-8")
    temporary.chmod(0o600)
    temporary.replace(path)


def get_task(task_id: str) -> dict[str, Any] | None:
    with _TASK_LOCK:
        item = _TASKS.get(task_id)
        if item:
            return dict(item)
    try:
        path = _task_state_path(task_id)
    except ValueError:
        return None
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return item if isinstance(item, dict) and item.get("task_id") == task_id else None


def start_update_task(tag_name: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    script = _update_script(settings)
    if not re.fullmatch(r"[vV]?\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", tag_name):
        raise ValueError("Latest Release tag 格式不受支持")
    with _TASK_LOCK:
        if any(item["status"] in {"queued", "running"} for item in _TASKS.values()):
            raise RuntimeError("已有升级任务正在执行")
        task_id = uuid.uuid4().hex
        _TASKS[task_id] = {
            "task_id": task_id,
            "status": "queued",
            "tag_name": tag_name,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "log_path": None,
            "error": None,
        }
        _write_task_state(_TASKS[task_id], settings)
    asyncio.create_task(_run_update_task(task_id, script, tag_name, settings))
    return get_task(task_id) or {}


async def _run_update_task(task_id: str, script: Path, tag_name: str, settings: Settings) -> None:
    root = repository_root(settings)
    log_dir = Path(settings.UPDATE_LOG_DIR).expanduser()
    if not log_dir.is_absolute():
        log_dir = root / log_dir
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    log_dir.chmod(0o700)
    log_path = log_dir / f"update-{task_id}.log"
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        display_log_path = str(log_path.relative_to(root))
    except ValueError:
        display_log_path = str(log_path)
    with _TASK_LOCK:
        _TASKS[task_id].update({"status": "running", "started_at": started_at, "log_path": display_log_path})
        _write_task_state(_TASKS[task_id], settings)
    try:
        process = await asyncio.create_subprocess_exec(
            str(script),
            "--tag",
            tag_name,
            cwd=str(root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={
                **__import__("os").environ,
                "CTG_UPDATE_TASK_ID": task_id,
                "CTG_RESTART_COMMAND": settings.UPDATE_RESTART_COMMAND or "",
                "CTG_HEALTH_URL": settings.UPDATE_HEALTH_URL,
                "CTG_UPDATE_STATE_FILE": str(_task_state_path(task_id, settings)),
                "CTG_UPDATE_STARTED_AT": started_at,
                "CTG_UPDATE_LOG_PATH": display_log_path,
            },
            start_new_session=True,
        )
        output, _ = await process.communicate()
        log_path.write_bytes(output[-200_000:])
        log_path.chmod(0o600)
        status_value = "succeeded" if process.returncode == 0 else "failed"
        script_error = None
        if process.returncode != 0:
            try:
                script_state = json.loads(
                    _task_state_path(task_id, settings).read_text(encoding="utf-8")
                )
                script_error = script_state.get("error")
            except (OSError, json.JSONDecodeError, AttributeError):
                pass
        with _TASK_LOCK:
            _TASKS[task_id].update({
                "status": status_value,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": process.returncode,
                "error": None if process.returncode == 0 else script_error or "Update.sh 执行失败",
            })
            _write_task_state(_TASKS[task_id], settings)
    except Exception as exc:
        logger.exception("OTA task failed before completion")
        log_path.write_text(f"OTA task failed: {type(exc).__name__}\n", encoding="utf-8")
        log_path.chmod(0o600)
        with _TASK_LOCK:
            _TASKS[task_id].update({
                "status": "failed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "exit_code": None,
                "error": "无法启动 Update.sh",
            })
            _write_task_state(_TASKS[task_id], settings)
