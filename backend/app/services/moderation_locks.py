"""Transaction-scoped locks for moderation operations."""
import hashlib

from sqlalchemy import text
from sqlmodel import Session


def _lock(db: Session, scope: str, *parts: object) -> None:
    if db.get_bind().dialect.name != "postgresql":
        return
    payload = ":".join([scope, *(str(part) for part in parts)]).encode("utf-8")
    lock_id = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=True)
    db.exec(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        params={"lock_id": lock_id},
    )


def lock_report_submission(
    db: Session,
    reporter_uid: int,
    target_type: str,
    target_id: int,
) -> None:
    _lock(db, "report", reporter_uid, target_type, target_id)


def lock_user_punishments(db: Session, target_uid: int) -> None:
    _lock(db, "punishment", target_uid)


def lock_role_management(db: Session) -> None:
    _lock(db, "role-management")
