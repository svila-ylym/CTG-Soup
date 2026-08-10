"""Create in-app notifications and mirror important notices by email."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from sqlmodel import Session

from app.models.database import Notification, NotificationType, User
from app.utils.email import get_smtp_service

logger = logging.getLogger(__name__)


def notify_user(
    db: Session,
    user: User | None,
    notification_type: NotificationType,
    title: str,
    content: str,
    *,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
    send_email: bool = True,
) -> Notification | None:
    """Queue a notification for one user and best-effort mirror it by email."""
    if user is None:
        return None
    notification = Notification(
        recipient_uid=user.uid,
        notification_type=notification_type,
        title=title,
        content=content,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(notification)
    if send_email and user.email:
        try:
            get_smtp_service().send_notification_email(
                user.email,
                user.username,
                notification_type.value,
                title,
                content,
            )
        except Exception:
            logger.warning("Notification email failed uid=%s type=%s", user.uid, notification_type.value, exc_info=True)
    return notification


def notify_users(
    db: Session,
    users: Iterable[User],
    notification_type: NotificationType,
    title: str,
    content: str,
    *,
    related_entity_type: str | None = None,
    related_entity_id: int | None = None,
) -> list[Notification]:
    return [
        notification
        for user in users
        if (notification := notify_user(
            db,
            user,
            notification_type,
            title,
            content,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )) is not None
    ]
