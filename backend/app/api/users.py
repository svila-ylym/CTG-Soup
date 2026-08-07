from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.models.database import get_db, User, Post, Comment, Soup as TurtleSoup, Like, Favorite as Collection, Follow
from app.schemas import UserUpdate, UserResponse, PostResponse, CommentResponse, TurtleSoupResponse, PageResponse
from app.api.auth import get_current_active_user, get_current_user
from app.core.enums import AccountStatus

router = APIRouter()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.get("/uid/{uid}", response_model=UserResponse)
async def get_user_by_uid(uid: str, db: Session = Depends(get_db)):
    """通过UID获取用户"""
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    # 检查邮箱是否已被其他用户使用
    if user_data.email and user_data.email != current_user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被使用")
        current_user.email = user_data.email
    
    if user_data.nickname:
        current_user.nickname = user_data.nickname
    if user_data.avatar_url:
        current_user.avatar_url = user_data.avatar_url
    if user_data.bio is not None:
        current_user.bio = user_data.bio
    if user_data.notice_preferences is not None:
        current_user.notice_preferences = user_data.notice_preferences
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/me/posts", response_model=PageResponse)
async def get_my_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的帖子"""
    offset = (page - 1) * page_size
    
    query = db.query(Post).filter(
        Post.author_uid == current_user.uid,
        Post.status == "published"
    ).order_by(Post.created_at.desc())
    
    total = query.count()
    posts = query.offset(offset).limit(page_size).all()
    
    items = []
    for post in posts:
        author = db.query(User).filter(User.uid == post.author_uid).first()
        items.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "section": post.section,
            "post_type": post.post_type,
            "tags": post.tags,
            "author_id": post.author_uid,
            "author_username": author.username if author else "Unknown",
            "author_nickname": author.nickname if author else "Unknown",
            "status": post.status,
            "like_count": post.like_count,
            "collect_count": post.favorite_count,
            "comment_count": post.comment_count,
            "view_count": post.view_count,
            "is_pinned": getattr(post, 'is_pinned', False),
            "is_featured": getattr(post, 'is_featured', False),
            "created_at": post.created_at,
            "updated_at": post.updated_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/me/turtle-soups", response_model=PageResponse)
async def get_my_turtle_soups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的海龟汤"""
    offset = (page - 1) * page_size
    
    query = db.query(TurtleSoup).filter(
        TurtleSoup.author_uid == current_user.uid,
        TurtleSoup.status == "published"
    ).order_by(TurtleSoup.created_at.desc())
    
    total = query.count()
    soups = query.offset(offset).limit(page_size).all()
    
    items = []
    for soup in soups:
        items.append({
            "id": soup.id,
            "title": soup.title,
            "puzzle": soup.puzzle,
            "solution": soup.solution,
            "tags": soup.tags,
            "author_id": soup.author_uid,
            "author_username": current_user.username,
            "author_nickname": current_user.nickname,
            "average_score": soup.avg_rating,
            "rating_count": soup.rating_count,
            "like_count": soup.like_count,
            "collect_count": soup.favorite_count,
            "view_count": soup.view_count,
            "is_revealed": getattr(soup, 'is_revealed', False),
            "status": soup.status,
            "created_at": soup.created_at,
            "updated_at": soup.updated_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/me/collections", response_model=PageResponse)
async def get_my_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    target_type: Optional[str] = Query(None, description="目标类型：post或turtle_soup"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的收藏"""
    offset = (page - 1) * page_size
    
    query = db.query(Collection).filter(Collection.user_uid == current_user.uid)
    
    if target_type:
        query = query.filter(Collection.target_type == target_type)
    
    query = query.order_by(Collection.created_at.desc())
    
    total = query.count()
    collections = query.offset(offset).limit(page_size).all()
    
    items = []
    for collection in collections:
        item_type = collection.target_type
        item_id = collection.target_id
        
        items.append({
            "id": collection.id,
            "target_type": item_type,
            "target_id": item_id,
            "created_at": collection.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/signin", response_model=dict)
async def daily_signin(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """每日签到"""
    today = datetime.utcnow().date()
    
    if current_user.last_signin_date and current_user.last_signin_date.date() == today:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="今日已签到")
    
    # 计算连续签到天数
    if current_user.last_signin_date:
        last_date = current_user.last_signin_date.date()
        days_diff = (today - last_date).days
        if days_diff == 1:
            current_user.consecutive_signin_days += 1
        else:
            current_user.consecutive_signin_days = 1
    else:
        current_user.consecutive_signin_days = 1
    
    # 计算积分奖励（基础10分 + 连续签到奖励）
    base_score = 10
    bonus_score = min(current_user.consecutive_signin_days, 7)  # 最多7天奖励
    total_score = base_score + bonus_score
    
    current_user.score += total_score
    current_user.last_signin_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "签到成功",
        "score_gained": total_score,
        "consecutive_days": current_user.consecutive_signin_days,
        "total_score": current_user.score
    }


@router.get("/{user_id}/profile")
async def get_user_profile(
    user_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户主页信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    # 统计信息
    post_count = db.query(Post).filter(Post.author_id == user_id, Post.status == "published").count()
    soup_count = db.query(TurtleSoup).filter(TurtleSoup.author_id == user_id, TurtleSoup.status == "published").count()
    follower_count = db.query(Follow).filter(Follow.followee_id == user_id).count()
    followee_count = db.query(Follow).filter(Follow.follower_id == user_id).count()
    like_received = db.query(Like).join(Post, Like.post_id == Post.id).filter(Post.author_id == user_id).count()
    
    # 检查是否是好友（互相关注）
    is_friend = False
    is_following = False
    is_blocked = False
    
    if current_user:
        is_following = db.query(Follow).filter(
            Follow.follower_id == current_user.id,
            Follow.followee_id == user_id
        ).first() is not None
        
        is_friend = is_following and db.query(Follow).filter(
            Follow.follower_id == user_id,
            Follow.followee_id == current_user.id
        ).first() is not None
        
        is_blocked = db.query(Follow).filter(
            (Follow.follower_id == current_user.id) | (Follow.follower_id == user_id),
            (Follow.followee_id == current_user.id) | (Follow.followee_id == user_id)
        ).first() is not None  # 简化判断，实际应该查黑名单表
    
    return {
        "user": {
            "id": user.id,
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "bio": user.bio,
            "role": user.role,
            "created_at": user.created_at,
        },
        "stats": {
            "post_count": post_count,
            "soup_count": soup_count,
            "follower_count": follower_count,
            "followee_count": followee_count,
            "like_received": like_received,
        },
        "relation": {
            "is_friend": is_friend,
            "is_following": is_following,
            "is_blocked": is_blocked,
        }
    }
