from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.models.database import (
    Collection,
    Blacklist,
    Comment,
    Follow,
    FeaturedSoup,
    Like,
    Post,
    TurtleSoup,
    UploadedAsset,
    User,
    SigninRecord,
    get_db,
)
from app.schemas import (
    CommentResponse,
    PageResponse,
    PostResponse,
    TurtleSoupResponse,
    UserPreferencesUpdate,
    UserResponse,
    UserUpdate,
)
from app.api.auth import get_current_active_user, get_optional_current_user
from app.schemas.community import UserSummary
from app.schemas.profiles import (
    FeaturedSoupInput,
    ProfileSoupSummary,
    PublicProfileResponse,
)
from app.services.levels import level_band, level_progress
from app.services import levels
from app.services.competition_entries import competition_colors_for_soups
from app.schemas.levels import SigninStatusResponse
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


PUBLIC_SOUP_STATUSES = ("published", "revealed")


@router.get("/uid/{uid}", response_model=UserSummary)
async def get_user_by_uid(uid: int, db: Session = Depends(get_db)):
    """通过UID获取用户"""
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    progress = level_progress(user.points)
    return {
        "uid": user.uid,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": progress.level,
        "level_band": level_band(progress.level),
    }


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
    if "avatar_asset_id" in user_data.model_fields_set:
        if user_data.avatar_asset_id is None:
            current_user.avatar_asset_id = None
            current_user.avatar_url = None
        else:
            asset = db.query(UploadedAsset).filter(
                UploadedAsset.id == user_data.avatar_asset_id,
                UploadedAsset.kind == "image",
            ).first()
            if asset is None or asset.owner_uid != current_user.uid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "AVATAR_NOT_OWNED",
                        "message": "只能选择自己上传的头像",
                    },
                )
            current_user.avatar_asset_id = asset.id
            current_user.avatar_url = asset.public_url
    if "profile_background_asset_id" in user_data.model_fields_set:
        preferences = dict(current_user.notification_prefs or {})
        if user_data.profile_background_asset_id is None:
            preferences.pop("profile_background_asset_id", None)
            preferences.pop("profile_background_url", None)
        else:
            asset = db.query(UploadedAsset).filter(
                UploadedAsset.id == user_data.profile_background_asset_id,
                UploadedAsset.kind == "image",
            ).first()
            if asset is None or asset.owner_uid != current_user.uid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "BACKGROUND_NOT_OWNED",
                        "message": "只能选择自己上传的背景图片",
                    },
                )
            preferences["profile_background_asset_id"] = asset.id
            preferences["profile_background_url"] = asset.public_url
        current_user.notification_prefs = preferences
    if user_data.bio is not None:
        current_user.bio = user_data.bio
    if user_data.notice_preferences is not None:
        preferences = dict(user_data.notice_preferences)
        existing_preferences = dict(current_user.notification_prefs or {})
        for key in ("profile_background_asset_id", "profile_background_url", "registration_date"):
            if key in existing_preferences:
                preferences[key] = existing_preferences[key]
        current_user.notification_prefs = preferences
    
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.put("/me/featured-soups", response_model=list[ProfileSoupSummary])
async def update_featured_soups(
    data: FeaturedSoupInput,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    soups = db.query(TurtleSoup).filter(
        TurtleSoup.id.in_(data.soup_ids),
    ).all() if data.soup_ids else []
    soups_by_id = {soup.id: soup for soup in soups}
    invalid_ids = [
        soup_id
        for soup_id in data.soup_ids
        if soup_id not in soups_by_id
        or soups_by_id[soup_id].author_uid != current_user.uid
        or soups_by_id[soup_id].status not in PUBLIC_SOUP_STATUSES
    ]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "FEATURED_SOUP_INVALID",
                "message": "代表作必须是本人已发布的海龟汤",
            },
        )

    db.query(FeaturedSoup).filter(
        FeaturedSoup.user_uid == current_user.uid,
    ).delete(synchronize_session=False)
    for position, soup_id in enumerate(data.soup_ids):
        db.add(
            FeaturedSoup(
                user_uid=current_user.uid,
                soup_id=soup_id,
                position=position,
            )
        )
    db.commit()
    colors_by_soup = competition_colors_for_soups(db, data.soup_ids)
    return [
        _profile_soup_payload(
            soups_by_id[soup_id],
            colors_by_soup.get(soup_id, []),
        )
        for soup_id in data.soup_ids
    ]


@router.put("/me/preferences", response_model=UserResponse)
async def update_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if preferences.allow_bulk_email is not None:
        current_user.allow_bulk_email = preferences.allow_bulk_email
    if preferences.theme_preference is not None:
        current_user.theme_preference = preferences.theme_preference
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Return the authenticated user's complete public profile."""
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
        items.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "section": post.section,
            "post_type": post.post_type,
            "tags": post.tags,
            "author_id": post.author_uid,
            "author_username": current_user.username,
            "author_nickname": current_user.nickname,
            "status": post.status,
            "like_count": post.like_count,
            "collect_count": post.collect_count,
            "comment_count": post.comment_count,
            "view_count": post.view_count,
            "is_pinned": post.is_pinned,
            "is_featured": post.is_featured,
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
            "average_score": soup.average_score,
            "rating_count": soup.rating_count,
            "like_count": soup.like_count,
            "collect_count": soup.collect_count,
            "view_count": soup.view_count,
            "is_revealed": soup.is_revealed,
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


def _signin_payload(user: User, business_day, signed_in: bool, gained: int) -> dict:
    progress = level_progress(user.points)
    return {
        "signed_in": signed_in,
        "signin_day": business_day,
        "consecutive_days": user.consecutive_signin_days,
        "experience_points": progress.experience_points,
        "experience_gained": gained,
        "level": progress.level,
        "level_start": progress.level_start,
        "next_level_start": progress.next_level_start,
    }


@router.get("/me/signin", response_model=SigninStatusResponse)
async def get_signin_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    business_day = levels.signin_day(levels.utc_now(), settings.SIGNIN_TIMEZONE)
    record = db.query(SigninRecord).filter(
        SigninRecord.user_uid == current_user.uid,
        SigninRecord.signin_day == business_day,
    ).first()
    return _signin_payload(
        current_user,
        business_day,
        signed_in=record is not None,
        gained=record.points_earned if record else 0,
    )


@router.post("/me/signin", response_model=SigninStatusResponse)
async def daily_signin(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    business_day = levels.signin_day(levels.utc_now(), settings.SIGNIN_TIMEZONE)
    locked_user = db.query(User).filter(User.uid == current_user.uid).with_for_update().one()
    existing = db.query(SigninRecord).filter(
        SigninRecord.user_uid == locked_user.uid,
        SigninRecord.signin_day == business_day,
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_SIGNED_IN", "message": "今天已经签到"},
        )

    if locked_user.last_signin:
        last_day = levels.signin_day(
            locked_user.last_signin,
            settings.SIGNIN_TIMEZONE,
        )
        if (business_day - last_day).days == 1:
            locked_user.consecutive_signin_days += 1
        else:
            locked_user.consecutive_signin_days = 1
    else:
        locked_user.consecutive_signin_days = 1

    gained = levels.signin_reward(locked_user.consecutive_signin_days)
    locked_user.points += gained
    locked_user.last_signin = levels.utc_now()
    db.add(
        SigninRecord(
            user_uid=locked_user.uid,
            signin_day=business_day,
            points_earned=gained,
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "ALREADY_SIGNED_IN", "message": "今天已经签到"},
        ) from exc
    db.refresh(locked_user)
    return _signin_payload(locked_user, business_day, signed_in=True, gained=gained)


def _profile_soup_payload(
    soup: TurtleSoup,
    competition_colors: list[str] | None = None,
) -> dict:
    return {
        "id": soup.id,
        "title": soup.title,
        "puzzle_excerpt": soup.puzzle[:200],
        "genre": soup.genre,
        "soup_color": soup.soup_color,
        "average_score": soup.avg_rating,
        "rating_count": soup.rating_count,
        "like_count": soup.like_count,
        "favorite_count": soup.favorite_count,
        "competition_colors": competition_colors or [],
        "created_at": soup.created_at,
    }


@router.get("/{uid}/profile", response_model=PublicProfileResponse)
async def get_user_profile(
    uid: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.uid == uid).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    soup_query = db.query(TurtleSoup).filter(
        TurtleSoup.author_uid == uid,
        TurtleSoup.status.in_(PUBLIC_SOUP_STATUSES),
    )
    soup_total = soup_query.count()
    soups = soup_query.order_by(
        TurtleSoup.created_at.desc(),
        TurtleSoup.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size).all()

    featured = db.query(TurtleSoup).join(
        FeaturedSoup,
        FeaturedSoup.soup_id == TurtleSoup.id,
    ).filter(
        FeaturedSoup.user_uid == uid,
        TurtleSoup.author_uid == uid,
        TurtleSoup.status.in_(PUBLIC_SOUP_STATUSES),
    ).order_by(FeaturedSoup.position.asc()).all()
    profile_soup_ids = list(dict.fromkeys([
        *[soup.id for soup in featured],
        *[soup.id for soup in soups],
    ]))
    colors_by_soup = competition_colors_for_soups(db, profile_soup_ids)

    post_count = db.query(Post).filter(
        Post.author_uid == uid,
        Post.status == "published",
    ).count()
    follower_count = db.query(Follow).filter(Follow.followed_uid == uid).count()
    following_count = db.query(Follow).filter(Follow.follower_uid == uid).count()
    post_likes = db.query(func.coalesce(func.sum(Post.like_count), 0)).filter(
        Post.author_uid == uid,
        Post.status == "published",
    ).scalar()
    soup_likes = db.query(func.coalesce(func.sum(TurtleSoup.like_count), 0)).filter(
        TurtleSoup.author_uid == uid,
        TurtleSoup.status.in_(PUBLIC_SOUP_STATUSES),
    ).scalar()

    is_self = current_user is not None and current_user.uid == uid
    is_following = False
    is_friend = False
    is_blocked = False
    if current_user is not None and not is_self:
        is_following = db.query(Follow).filter(
            Follow.follower_uid == current_user.uid,
            Follow.followed_uid == uid,
        ).first() is not None
        is_friend = is_following and db.query(Follow).filter(
            Follow.follower_uid == uid,
            Follow.followed_uid == current_user.uid,
        ).first() is not None
        is_blocked = db.query(Blacklist).filter(
            (
                (Blacklist.blocker_uid == current_user.uid)
                & (Blacklist.blocked_uid == uid)
            )
            | (
                (Blacklist.blocker_uid == uid)
                & (Blacklist.blocked_uid == current_user.uid)
            )
        ).first() is not None

    progress = level_progress(user.points)
    return {
        "user": {
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "profile_background_url": user.profile_background_url,
            "bio": user.bio,
            "role": user.role,
            "level": progress.level,
            "level_band": level_band(progress.level),
            "experience_points": progress.experience_points,
            "level_start": progress.level_start,
            "next_level_start": progress.next_level_start,
            "registration_date": user.registration_date,
            "created_at": user.created_at,
        },
        "stats": {
            "post_count": post_count,
            "soup_count": soup_total,
            "follower_count": follower_count,
            "following_count": following_count,
            "like_received": int(post_likes or 0) + int(soup_likes or 0),
        },
        "relation": {
            "is_self": is_self,
            "is_following": is_following,
            "is_friend": is_friend,
            "is_blocked": is_blocked,
        },
        "featured_soups": [
            _profile_soup_payload(soup, colors_by_soup.get(soup.id, []))
            for soup in featured
        ],
        "soups": {
            "items": [
                _profile_soup_payload(soup, colors_by_soup.get(soup.id, []))
                for soup in soups
            ],
            "total": soup_total,
            "page": page,
            "page_size": page_size,
            "total_pages": (soup_total + page_size - 1) // page_size,
        },
    }
