import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from app.services.database_backup import create_database_backup


def test_backup_uses_custom_format_and_writes_checksum(tmp_path):
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        Path(args[args.index("--file") + 1]).write_bytes(b"pgdump")
        return subprocess.CompletedProcess(args, 0)

    result = create_database_backup(
        "postgresql://user:secret@localhost/app",
        tmp_path,
        runner=runner,
    )

    args, kwargs = calls[0]
    assert Path(args[0]).name == "pg_dump"
    assert "--format=custom" in args
    assert "--no-owner" in args
    assert "secret" not in " ".join(str(value) for value in args)
    assert kwargs["env"]["PGPASSWORD"] == "secret"
    assert kwargs["check"] is True
    assert result.path.parent == tmp_path
    assert result.sha256 == hashlib.sha256(b"pgdump").hexdigest()
    assert "secret" not in repr(result)


def test_backup_uses_explicit_pg_dump_binary(tmp_path):
    calls = []

    def runner(args, **kwargs):
        calls.append(args)
        Path(args[args.index("--file") + 1]).write_bytes(b"pgdump")
        return subprocess.CompletedProcess(args, 0)

    create_database_backup(
        "postgresql://user:secret@localhost/app",
        tmp_path,
        runner=runner,
        pg_dump_binary=sys.executable,
    )

    assert calls[0][0] == sys.executable


def test_backup_surfaces_pg_dump_stderr_without_connection_url(tmp_path):
    def runner(args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            args,
            stderr="pg_dump: error: server version mismatch for postgresql://user:secret@localhost/app",
        )

    with pytest.raises(RuntimeError, match="server version mismatch") as error:
        create_database_backup(
            "postgresql://user:secret@localhost/app",
            tmp_path,
            runner=runner,
            pg_dump_binary=sys.executable,
        )

    assert "user:secret@localhost/app" not in str(error.value)
    assert "postgresql://[redacted]" in str(error.value)
