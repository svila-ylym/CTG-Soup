from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.database import get_db, User, Post, TurtleSoup, Comment
from app.schemas import PageResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/users")
async def search_users(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """搜索用户"""
    offset = (page - 1) * page_size
    
    # 支持用户名、昵称、UID搜索
    query = db.query(User).filter(
        (User.username.ilike(f"%{q}%")) |
        (User.nickname.ilike(f"%{q}%")) |
        (User.uid.ilike(f"%{q}%"))
    )
    
    total = query.count()
    users = query.offset(offset).limit(page_size).all()
    
    items = []
    for user in users:
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


@router.get("/posts")
async def search_posts(
    q: str = Query(..., min_length=1),
    section: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """搜索帖子"""
    offset = (page - 1) * page_size
    
    query = db.query(Post).filter(
        (Post.title.ilike(f"%{q}%")) |
        (Post.content.ilike(f"%{q}%")),
        Post.status == "published"
    )
    
    if section:
        query = query.filter(Post.section == section)
    
    query = query.order_by(Post.created_at.desc())
    
    total = query.count()
    posts = query.offset(offset).limit(page_size).all()
    
    items = []
    for post in posts:
        items.append({
            "id": post.id,
            "title": post.title,
            "content": post.content[:200] + "..." if len(post.content) > 200 else post.content,
            "section": post.section,
            "author_username": post.author.username,
            "created_at": post.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/turtle-soups")
async def search_turtle_soups(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """搜索海龟汤"""
    offset = (page - 1) * page_size
    
    query = db.query(TurtleSoup).filter(
        (TurtleSoup.title.ilike(f"%{q}%")) |
        (TurtleSoup.puzzle.ilike(f"%{q}%")),
        TurtleSoup.status == "published"
    )
    
    query = query.order_by(TurtleSoup.average_score.desc())
    
    total = query.count()
    soups = query.offset(offset).limit(page_size).all()
    
    items = []
    for soup in soups:
        items.append({
            "id": soup.id,
            "title": soup.title,
            "puzzle": soup.puzzle[:200] + "..." if len(soup.puzzle) > 200 else soup.puzzle,
            "tags": soup.tags,
            "average_score": soup.average_score,
            "author_username": soup.author.username,
            "created_at": soup.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
