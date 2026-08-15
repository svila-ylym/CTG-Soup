from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import update
from sqlmodel import Session, select

from app.api.auth import get_current_active_user
from app.models.database import Notification, User, get_db
from app.schemas.community import (
    NotificationPageResponse,
    NotificationReadAllResponse,
    NotificationResponse,
)

router = APIRouter()


@router.get("", response_model=NotificationPageResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    query = select(Notification).where(Notification.recipient_uid == current_user.uid)
    if unread_only:
        query = query.where(Notification.is_read == False)
    total = len(db.exec(query).all())
    rows = db.exec(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.put("/read-all", response_model=NotificationReadAllResponse)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    result = db.exec(
        update(Notification)
        .where(
            Notification.recipient_uid == current_user.uid,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    db.commit()
    return {"updated_count": max(result.rowcount or 0, 0)}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    notification = db.exec(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_uid == current_user.uid,
        )
    ).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="通知不存在")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification
