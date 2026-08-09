"""Pending-account expiry and deterministic UID reuse."""

from datetime import datetime, timedelta

from sqlalchemy import func, text
from sqlmodel import Session, select

from app.models.database import (
    EmailVerification,
    ReusableUserUid,
    User,
    UserStatus,
    UserUidAllocator,
)


UID_LOCK_KEY = 1129596757
PENDING_ACCOUNT_LIFETIME = timedelta(minutes=30)


def lock_uid_allocation(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": UID_LOCK_KEY},
        )


def allocate_user_uid(db: Session) -> int:
    """Advance the normal allocation and prefer the smallest released UID."""
    lock_uid_allocation(db)
    allocator = db.exec(
        select(UserUidAllocator)
        .where(UserUidAllocator.id == 1)
        .with_for_update()
    ).first()
    max_uid = db.exec(select(func.max(User.uid))).one() or 0
    if allocator is None:
        allocator = UserUidAllocator(id=1, next_uid=max_uid + 1)
        db.add(allocator)
        db.flush()

    normal_uid = max(allocator.next_uid, max_uid + 1)
    allocator.next_uid = normal_uid + 1
    released = db.exec(
        select(ReusableUserUid)
        .order_by(ReusableUserUid.uid)
        .with_for_update()
    ).first()
    if released is None:
        return normal_uid

    uid = released.uid
    db.delete(released)
    return uid


def cleanup_expired_pending_users(
    db: Session,
    now: datetime | None = None,
) -> list[int]:
    """Delete pending accounts older than 30 minutes and release their UIDs."""
    current_time = now or datetime.utcnow()
    cutoff = current_time - PENDING_ACCOUNT_LIFETIME
    lock_uid_allocation(db)
    candidate_uids = db.exec(
        select(User.uid).where(
            User.status == UserStatus.PENDING_EMAIL,
            User.created_at <= cutoff,
        )
    ).all()
    deleted_uids: list[int] = []
    try:
        for uid in candidate_uids:
            verifications = db.exec(
                select(EmailVerification)
                .where(EmailVerification.user_uid == uid)
                .with_for_update()
            ).all()
            user = db.exec(
                select(User).where(User.uid == uid).with_for_update()
            ).first()
            if (
                user is None
                or user.status != UserStatus.PENDING_EMAIL
                or user.created_at > cutoff
            ):
                continue
            for verification in verifications:
                db.delete(verification)
            if db.get(ReusableUserUid, uid) is None:
                db.add(ReusableUserUid(uid=uid, released_at=current_time))
            db.delete(user)
            deleted_uids.append(uid)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return deleted_uids
