"""Create verifiable PostgreSQL backups without exposing credentials."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from sqlalchemy.engine import URL, make_url


@dataclass(frozen=True)
class BackupResult:
    path: Path
    sha256: str
    created_at: datetime


Runner = Callable[..., subprocess.CompletedProcess[str]]


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
) -> BackupResult:
    """Run ``pg_dump`` and return the backup path and SHA-256 digest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    path = output_dir / f"ctg-{created_at:%Y%m%dT%H%M%S%fZ}.dump"
    safe_url, password = _safe_database_url(database_url)
    environment = os.environ.copy()
    if password is not None:
        environment["PGPASSWORD"] = password

    runner(
        [
            "pg_dump",
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
    result = create_database_backup(
        get_settings().DATABASE_URL,
        args.output_dir,
    )
    payload = asdict(result)
    payload["path"] = str(result.path)
    payload["created_at"] = result.created_at.isoformat()
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
