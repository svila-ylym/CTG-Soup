from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.models.database import get_db, Post, User, Like, Collection, Comment
from app.schemas import PostCreate, PostUpdate, PostResponse, PageResponse
from app.api.auth import get_current_active_user, get_current_user

router = APIRouter()


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发布帖子"""
    db_post = Post(
        author_id=current_user.id,
        title=post_data.title,
        content=post_data.content,
        section=post_data.section,
        post_type=post_data.post_type,
        tags=post_data.tags,
        vote_config=post_data.vote_config,
        status="published",
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    return db_post


@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取帖子详情"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在")
    
    if post.status != "published":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="帖子不可见")
    
    post.view_count += 1
    db.commit()
    
    return post


@router.get("")
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    section: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("created_at"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取帖子列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Post).filter(Post.status == "published")
    
    if section:
        query = query.filter(Post.section == section)
    if tag:
        query = query.filter(Post.tags.contains([tag]))
    
    if sort_by == "like_count":
        query = query.order_by(Post.like_count.desc())
    elif sort_by == "comment_count":
        query = query.order_by(Post.comment_count.desc())
    else:
        query = query.order_by(Post.created_at.desc())
    
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
            "author_id": post.author_id,
            "author_username": post.author.username,
            "author_nickname": post.author.nickname,
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
