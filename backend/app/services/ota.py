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

# Tag pattern: aawbbx where aa=year(2 digits), w=fixed, bb=week(01-53), x=submission(a-z)
_TAG_PATTERN = re.compile(r"^(?P<year>\d{2})w(?P<week>[0-5]\d)(?P<submission>[a-z])$")

_TASK_LOCK = threading.Lock()
_TASKS: dict[str, dict[str, Any]] = {}


def _parse_semantic_version(value: str) -> tuple[int, int, int, tuple[int, Any]] | None:
    """Parse semantic version (e.g., 1.4.1, 1.4.10, 1.101.0)."""
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


def _parse_tag_version(value: str) -> tuple[int, int, int, str] | None:
    """Parse tag version (e.g., 24w52c): year, week, submission order."""
    match = _TAG_PATTERN.fullmatch(value.strip().lower())
    if match is None:
        return None
    year = int(match.group("year"))
    week = int(match.group("week"))
    submission = match.group("submission")
    # Convert submission letter to numeric value (a=0, b=1, ..., z=25)
    submission_val = ord(submission) - ord('a')
    return (year, week, submission_val, submission)


def repository_root(settings: Settings | None = None) -> Path:
    configured = (settings or get_settings()).UPDATE_REPOSITORY_PATH
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[3]


def _version_parts(value: str) -> tuple[int, ...] | None:
    """Parse version supporting both semantic (1.4.1) and tag (24w52c) formats."""
    # Try semantic version first (e.g., 1.4.1, 1.4.10, 1.101.0)
    semantic_result = _parse_semantic_version(value)
    if semantic_result is not None:
        # Return as (999, major, minor, patch) - semantic versions sort after tag versions
        major, minor, patch, _ = semantic_result
        return (999, major, minor, patch)
    
    # Try tag version (e.g., 24w52c)
    tag_result = _parse_tag_version(value)
    if tag_result is not None:
        year, week, submission_val, _ = tag_result
        # Return as (year, week, submission_val) - tag versions use actual year
        return (year, week, submission_val)
    
    return None


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
        # Always force refresh when OTA_UPDATE_MODE changes to ensure correct tag filtering
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
            # Clear cache on mode switch to re-scan for appropriate tags
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
        
        # Determine which tag format to accept based on OTA_UPDATE_MODE
        ota_mode = self.settings.OTA_UPDATE_MODE  # "Latest" or "Dev"
        
        try:
            # Fetch all releases to find the appropriate one based on mode
            releases_url = f"{self.settings.GITHUB_API_URL.rstrip('/')}/repos/{self.settings.GITHUB_REPOSITORY.strip('/')}/releases"
            async with httpx.AsyncClient(timeout=self.settings.GITHUB_API_TIMEOUT_SECONDS, follow_redirects=True) as client:
                response = await client.get(releases_url, headers=headers)
            response.raise_for_status()
            all_releases = response.json()
            
            if not all_releases:
                return LatestReleaseResult(
                    current_version=self.settings.APP_VERSION,
                    latest_version=None,
                    tag_name=None,
                    release_name=None,
                    published_at=None,
                    html_url=None,
                    status="no_release",
                    update_available=False,
                    checked_at=checked_at,
                    error=None,
                )
            
            # Filter releases based on OTA mode
            filtered_releases = []
            for release in all_releases:
                tag = str(release.get("tag_name") or "").strip()
                if not tag:
                    continue
                
                is_semantic = bool(re.fullmatch(r"[vV]?\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", tag))
                is_tag = bool(re.fullmatch(r"\d{2}w[0-5]\d[a-z]", tag.lower()))
                
                if ota_mode == "Latest" and is_semantic:
                    filtered_releases.append((release, tag, True))  # True = semantic
                elif ota_mode == "Dev" and is_tag:
                    filtered_releases.append((release, tag, False))  # False = tag
            
            if not filtered_releases:
                return LatestReleaseResult(
                    current_version=self.settings.APP_VERSION,
                    latest_version=None,
                    tag_name=None,
                    release_name=None,
                    published_at=None,
                    html_url=None,
                    status="no_release",
                    update_available=False,
                    checked_at=checked_at,
                    error=None,
                )
            
            # Sort by version to find the latest
            def sort_key(item):
                _, tag, is_sem = item
                parts = _version_parts(tag)
                return parts if parts else (0, 0, 0)
            
            filtered_releases.sort(key=sort_key, reverse=True)
            best_release, tag_name, _ = filtered_releases[0]
            
            latest_version = normalize_version(tag_name) if tag_name else None
            status_value = compare_versions(self.settings.APP_VERSION, latest_version or "")
            return LatestReleaseResult(
                current_version=self.settings.APP_VERSION,
                latest_version=latest_version,
                tag_name=tag_name or None,
                release_name=str(best_release.get("name") or tag_name or "") or None,
                published_at=best_release.get("published_at"),
                html_url=best_release.get("html_url"),
                status=status_value,
                update_available=status_value == "update_available",
                checked_at=checked_at,
                error=None if status_value not in {"invalid_latest_version", "unknown_current_version"} else "GitHub Release tag 不是有效版本号",
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return LatestReleaseResult(
                    current_version=self.settings.APP_VERSION,
                    latest_version=None,
                    tag_name=None,
                    release_name=None,
                    published_at=None,
                    html_url=None,
                    status="no_release",
                    update_available=False,
                    checked_at=checked_at,
                    error=None,
                )
            logger.warning("GitHub Latest Release check failed: HTTPStatusError")
            return self._error_result(checked_at)
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("GitHub Latest Release check failed: %s", type(exc).__name__)
            return self._error_result(checked_at)

    def _error_result(self, checked_at: str) -> LatestReleaseResult:
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
    # Support both semantic versions (1.4.1) and tag versions (24w52c)
    is_semantic = re.fullmatch(r"[vV]?\d+(?:\.\d+){0,2}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", tag_name)
    is_tag = re.fullmatch(r"\d{2}w[0-5]\d[a-z]", tag_name.lower())
    if not (is_semantic or is_tag):
        raise ValueError("Latest Release tag 格式不受支持 (支持语义版本如 1.4.1 或标签版本如 24w52c)")
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
