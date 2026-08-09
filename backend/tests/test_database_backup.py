import hashlib
import subprocess
from pathlib import Path

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
    assert args[0] == "pg_dump"
    assert "--format=custom" in args
    assert "--no-owner" in args
    assert "secret" not in " ".join(str(value) for value in args)
    assert kwargs["env"]["PGPASSWORD"] == "secret"
    assert kwargs["check"] is True
    assert result.path.parent == tmp_path
    assert result.sha256 == hashlib.sha256(b"pgdump").hexdigest()
    assert "secret" not in repr(result)
