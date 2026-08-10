from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.auth import get_current_active_user
from app.models.database import Blacklist, Follow, User, get_db
from app.schemas.community import (
    BlacklistResponse,
    FollowResponse,
    TargetUserAction,
    UserPageResponse,
)
from app.services.levels import level_band, level_progress

router = APIRouter()


def _target(db: Session, current_user: User, target_uid: int) -> User:
    if target_uid == current_user.uid:
        raise HTTPException(status_code=400, detail="不能对自己执行此操作")
    target = db.get(User, target_uid)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return target


def _user_payload(user: User) -> dict:
    progress = level_progress(user.points)
    return {
        "uid": user.uid,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": progress.level,
        "level_band": level_band(progress.level),
    }


@router.post("/follow", response_model=FollowResponse)
def follow_user(data: TargetUserAction, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _target(db, current_user, data.target_uid)
    existing = db.exec(select(Follow).where(Follow.follower_uid == current_user.uid, Follow.followed_uid == data.target_uid)).first()
    if existing is None:
        db.add(Follow(follower_uid=current_user.uid, followed_uid=data.target_uid))
        db.commit()
    return {"follower_uid": current_user.uid, "followed_uid": data.target_uid, "active": True}


@router.delete("/follow/{target_uid}", response_model=FollowResponse)
def unfollow_user(target_uid: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    existing = db.exec(select(Follow).where(Follow.follower_uid == current_user.uid, Follow.followed_uid == target_uid)).first()
    if existing is not None:
        db.delete(existing)
        db.commit()
    return {"follower_uid": current_user.uid, "followed_uid": target_uid, "active": False}


def _user_page(db: Session, uids: list[int], page: int, page_size: int) -> dict:
    total = len(uids)
    selected = uids[(page - 1) * page_size : page * page_size]
    users = [db.get(User, uid) for uid in selected]
    return {
        "items": [_user_payload(user) for user in users if user],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/followers", response_model=UserPageResponse)
def get_followers(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    uids = db.exec(select(Follow.follower_uid).where(Follow.followed_uid == current_user.uid).order_by(Follow.created_at.desc())).all()
    return _user_page(db, uids, page, page_size)


@router.get("/following", response_model=UserPageResponse)
def get_following(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    uids = db.exec(select(Follow.followed_uid).where(Follow.follower_uid == current_user.uid).order_by(Follow.created_at.desc())).all()
    return _user_page(db, uids, page, page_size)


@router.post("/blacklist", response_model=BlacklistResponse)
def blacklist_user(data: TargetUserAction, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _target(db, current_user, data.target_uid)
    existing = db.exec(select(Blacklist).where(Blacklist.blocker_uid == current_user.uid, Blacklist.blocked_uid == data.target_uid)).first()
    if existing is None:
        db.add(Blacklist(blocker_uid=current_user.uid, blocked_uid=data.target_uid))
        following = db.exec(select(Follow).where(Follow.follower_uid == current_user.uid, Follow.followed_uid == data.target_uid)).first()
        if following is not None:
            db.delete(following)
        db.commit()
    return {"blocker_uid": current_user.uid, "blocked_uid": data.target_uid, "active": True}


@router.delete("/blacklist/{target_uid}", response_model=BlacklistResponse)
def unblacklist_user(target_uid: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    existing = db.exec(select(Blacklist).where(Blacklist.blocker_uid == current_user.uid, Blacklist.blocked_uid == target_uid)).first()
    if existing is not None:
        db.delete(existing)
        db.commit()
    return {"blocker_uid": current_user.uid, "blocked_uid": target_uid, "active": False}
