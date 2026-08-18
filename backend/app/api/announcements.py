from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_admin_user
from app.models.database import Announcement, AnnouncementStatus, User, get_db
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementPageResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)

router = APIRouter()


def _expire_stale(db: Session) -> None:
    now = datetime.utcnow()
    rows = db.exec(
        select(Announcement).where(
            Announcement.status == AnnouncementStatus.PUBLISHED,
            Announcement.expires_at.is_not(None),
            Announcement.expires_at < now,
        )
    ).all()
    if rows:
        for item in rows:
            item.status = AnnouncementStatus.EXPIRED
        db.commit()


@router.get("", response_model=AnnouncementPageResponse)
def list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _expire_stale(db)
    query = select(Announcement).where(Announcement.status == AnnouncementStatus.PUBLISHED)
    total = len(db.exec(query).all())
    items = db.exec(
        query.order_by(Announcement.priority.desc(), Announcement.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    if announcement.status != AnnouncementStatus.PUBLISHED:
        raise HTTPException(404, "公告不存在或未发布")
    return announcement


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    data: AnnouncementCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = Announcement(author_uid=current_user.uid, **data.model_dump())
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.put("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(announcement, key, value)
    announcement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(announcement)
    return announcement


@router.post("/{announcement_id}/publish", response_model=AnnouncementResponse)
def publish_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.published_at = datetime.utcnow()
    announcement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(announcement)
    return announcement


@router.put("/{announcement_id}/publish", response_model=AnnouncementResponse)
def publish_announcement_put(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return publish_announcement(announcement_id, current_user, db)


@router.post("/{announcement_id}/withdraw", response_model=AnnouncementResponse)
def withdraw_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    announcement.status = AnnouncementStatus.DRAFT
    announcement.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    db.delete(announcement)
    db.commit()
