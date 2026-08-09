"""Punishment lifecycle and derived user-status helpers."""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.database import (
    EmailVerification,
    Punishment,
    PunishmentType,
    User,
    UserRole,
    UserStatus,
)
from app.services.governance_rules import status_from_active_punishments
from app.services.moderation_locks import lock_user_punishments


STATUS_PUNISHMENT_TYPES = {PunishmentType.BAN, PunishmentType.SILENCE}


def active_punishment_types(
    db: Session,
    target_uid: int,
    now: datetime | None = None,
    *,
    exclude_id: int | None = None,
) -> set[str]:
    current_time = now or datetime.utcnow()
    query = db.query(Punishment).filter(
        Punishment.target_uid == target_uid,
        Punishment.punishment_type.in_(STATUS_PUNISHMENT_TYPES),
        Punishment.is_revoked == False,
        or_(Punishment.end_time.is_(None), Punishment.end_time > current_time),
    )
    if exclude_id is not None:
        query = query.filter(Punishment.id != exclude_id)
    return {item.punishment_type.value for item in query.all()}


def effective_user_status(
    db: Session,
    user: User,
    active_types: set[str],
) -> UserStatus:
    """Derive punishment status without bypassing pending email verification."""
    punishment_status = UserStatus(status_from_active_punishments(active_types))
    if punishment_status != UserStatus.ACTIVE:
        return punishment_status

    pending_verification = db.query(EmailVerification.id).filter(
        EmailVerification.user_uid == user.uid,
        EmailVerification.used_at.is_(None),
    ).first()
    if pending_verification is not None:
        return UserStatus.PENDING_EMAIL
    return UserStatus.ACTIVE


def sync_user_punishment_status(
    db: Session,
    user: User,
    now: datetime | None = None,
) -> bool:
    """Apply active punishment priority and release statuses after expiry."""
    if user.role == UserRole.ROOT or user.status not in {
        UserStatus.BANNED,
        UserStatus.SILENCED,
    }:
        return False
    current_time = now or datetime.utcnow()
    lock_user_punishments(db, user.uid)
    db.refresh(user)
    lifecycle_rows = db.query(Punishment).filter(
        Punishment.target_uid == user.uid,
        Punishment.punishment_type.in_(STATUS_PUNISHMENT_TYPES),
        Punishment.is_revoked == False,
    ).all()
    if not lifecycle_rows:
        return False

    active_types = {
        item.punishment_type.value
        for item in lifecycle_rows
        if item.end_time is None or item.end_time > current_time
    }
    desired = effective_user_status(db, user, active_types)
    if user.status == desired:
        return False
    if desired in {UserStatus.BANNED, UserStatus.SILENCED}:
        user.token_version += 1
    user.status = desired
    return True
