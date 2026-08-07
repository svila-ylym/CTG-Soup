from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db, User, Follow, Blacklist, Like, Collection, Post, TurtleSoup, Comment
from app.schemas import FollowAction, BlacklistAction, PageResponse
from app.api.auth import get_current_active_user

router = APIRouter()


@router.post("/follow")
async def follow_user(
    action: FollowAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """关注用户"""
    if action.target_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能关注自己")
    
    target_user = db.query(User).filter(User.id == action.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    existing = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.followee_id == action.target_user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已关注")
    
    new_follow = Follow(
        follower_id=current_user.id,
        followee_id=action.target_user_id,
    )
    db.add(new_follow)
    db.commit()
    
    return {"message": "关注成功"}


@router.delete("/follow/{target_user_id}")
async def unfollow_user(
    target_user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """取消关注"""
    existing = db.query(Follow).filter(
        Follow.follower_id == current_user.id,
        Follow.followee_id == target_user_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未关注")
    
    db.delete(existing)
    db.commit()
    
    return {"message": "已取消关注"}


@router.get("/followers", response_model=PageResponse)
async def get_followers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的粉丝列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Follow).filter(Follow.followee_id == current_user.id)
    total = query.count()
    follows = query.offset(offset).limit(page_size).all()
    
    items = []
    for follow in follows:
        user = db.query(User).filter(User.id == follow.follower_id).first()
        items.append({
            "id": user.id,
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/following", response_model=PageResponse)
async def get_following(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我关注的用户列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Follow).filter(Follow.follower_id == current_user.id)
    total = query.count()
    follows = query.offset(offset).limit(page_size).all()
    
    items = []
    for follow in follows:
        user = db.query(User).filter(User.id == follow.followee_id).first()
        items.append({
            "id": user.id,
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/blacklist")
async def blacklist_user(
    action: BlacklistAction,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """拉黑用户"""
    if action.target_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能拉黑自己")
    
    target_user = db.query(User).filter(User.id == action.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    existing = db.query(Blacklist).filter(
        Blacklist.blocker_id == current_user.id,
        Blacklist.blocked_id == action.target_user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已拉黑")
    
    new_blacklist = Blacklist(
        blocker_id=current_user.id,
        blocked_id=action.target_user_id,
    )
    db.add(new_blacklist)
    db.commit()
    
    return {"message": "拉黑成功"}


@router.delete("/blacklist/{target_user_id}")
async def unblacklist_user(
    target_user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """解除拉黑"""
    existing = db.query(Blacklist).filter(
        Blacklist.blocker_id == current_user.id,
        Blacklist.blocked_id == target_user_id
    ).first()
    
    if not existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未拉黑")
    
    db.delete(existing)
    db.commit()
    
    return {"message": "已解除拉黑"}
