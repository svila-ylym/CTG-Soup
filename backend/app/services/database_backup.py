"""Create verifiable PostgreSQL backups without exposing credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from sqlalchemy.engine import URL, make_url


logger = logging.getLogger(__name__)

# BaoTa installs the PostgreSQL server and its matching client outside PATH.
# Keep this as a fallback only; PG_DUMP_BIN remains the portable override.
_KNOWN_PG_DUMP_PATHS = ("/www/server/pgsql/bin/pg_dump",)


@dataclass(frozen=True)
class BackupResult:
    path: Path
    sha256: str
    created_at: datetime


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _resolve_pg_dump_binary(binary: str | None = None) -> str:
    """Resolve a pg_dump executable, preferring a configured matching client."""
    configured = binary or os.environ.get("PG_DUMP_BIN")
    if configured:
        resolved = shutil.which(configured) if "/" not in configured else configured
        if not resolved or not os.access(resolved, os.X_OK):
            raise FileNotFoundError(f"PG_DUMP_BIN 不可执行或不存在: {configured}")
        return resolved

    for candidate in _KNOWN_PG_DUMP_PATHS:
        if os.access(candidate, os.X_OK):
            return candidate
    if shutil.which("pg_dump"):
        return "pg_dump"
    raise FileNotFoundError("找不到 pg_dump，请安装 PostgreSQL 客户端或配置 PG_DUMP_BIN")


def _format_process_error(error: subprocess.CalledProcessError) -> str:
    detail = str(error.stderr or "").strip()
    if detail:
        # pg_dump normally reports safe operational details, but never echo a
        # URL in case a driver adds connection context to stderr.
        detail = re.sub(r"(?i)(postgres(?:ql)?://)[^\s]+", r"\1[redacted]", detail)
        return f"pg_dump 失败（退出码 {error.returncode}）：{detail}"
    return f"pg_dump 失败（退出码 {error.returncode}），未返回错误详情"


def _safe_database_url(database_url: str) -> tuple[str, str | None]:
    url = make_url(database_url)
    if not url.drivername.startswith("postgresql"):
        raise ValueError("database backup requires a PostgreSQL URL")
    safe_url = URL.create(
        drivername="postgresql",
        username=url.username,
        host=url.host,
        port=url.port,
        database=url.database,
        query=url.query,
    ).render_as_string(hide_password=False)
    return safe_url, url.password


def create_database_backup(
    database_url: str,
    output_dir: Path,
    runner: Runner = subprocess.run,
    *,
    pg_dump_binary: str | None = None,
) -> BackupResult:
    """Run ``pg_dump`` and return the backup path and SHA-256 digest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    path = output_dir / f"ctg-{created_at:%Y%m%dT%H%M%S%fZ}.dump"
    safe_url, password = _safe_database_url(database_url)
    pg_dump = _resolve_pg_dump_binary(pg_dump_binary)
    environment = os.environ.copy()
    if password is not None:
        environment["PGPASSWORD"] = password

    try:
        runner(
            [
                pg_dump,
                "--format=custom",
                "--no-owner",
                "--file",
                str(path),
                "--dbname",
                safe_url,
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
    except subprocess.CalledProcessError as exc:
        message = _format_process_error(exc)
        logger.error(message)
        raise RuntimeError(message) from exc
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return BackupResult(path=path, sha256=digest, created_at=created_at)


def main(argv: Sequence[str] | None = None) -> None:
    from app.core.config import get_settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "backups",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    result = create_database_backup(
        settings.DATABASE_URL,
        args.output_dir,
        pg_dump_binary=settings.PG_DUMP_BIN,
    )
    payload = asdict(result)
    payload["path"] = str(result.path)
    payload["created_at"] = result.created_at.isoformat()
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
