from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.database import Post, Soup, User, get_db
from app.schemas.community import (
    SearchPostPageResponse,
    SearchSoupPageResponse,
    UserPageResponse,
    UserSummary,
)

router = APIRouter()


def _page_payload(items: list[dict], total: int, page: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/users", response_model=UserPageResponse)
def search_users(
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    term = q.strip()
    filters = (
        User.username.ilike(f"%{term}%")
        | User.nickname.ilike(f"%{term}%")
    )
    total = db.exec(
        select(func.count()).select_from(User).where(filters)
    ).one()
    rows = db.exec(
        select(User)
        .where(filters)
        .order_by(User.uid.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        UserSummary(
            uid=row.uid,
            username=row.username,
            nickname=row.nickname,
            avatar_url=row.avatar_url,
        ).model_dump()
        for row in rows
    ]
    return _page_payload(items, total, page, page_size)


@router.get("/posts", response_model=SearchPostPageResponse)
def search_posts(
    q: str = Query(min_length=1, max_length=100),
    section: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    term = q.strip()
    filters = [
        Post.status == "published",
        Post.title.ilike(f"%{term}%") | Post.content.ilike(f"%{term}%"),
    ]
    if section:
        filters.append(Post.section == section)

    total = db.exec(
        select(func.count()).select_from(Post).where(*filters)
    ).one()
    rows = db.exec(
        select(Post)
        .where(*filters)
        .order_by(Post.created_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": row.id,
            "author_uid": row.author_uid,
            "title": row.title,
            "excerpt": row.content[:200],
            "section": row.section,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return _page_payload(items, total, page, page_size)


@router.get("/turtle-soups", response_model=SearchSoupPageResponse)
def search_soups(
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    term = q.strip()
    filters = (
        Soup.status.in_(["published", "revealed"]),
        Soup.title.ilike(f"%{term}%") | Soup.puzzle.ilike(f"%{term}%"),
    )
    total = db.exec(
        select(func.count()).select_from(Soup).where(*filters)
    ).one()
    rows = db.exec(
        select(Soup)
        .where(*filters)
        .order_by(
            Soup.avg_rating.desc(),
            Soup.created_at.desc(),
            Soup.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": row.id,
            "author_uid": row.author_uid,
            "title": row.title,
            "puzzle_excerpt": row.puzzle[:200],
            "average_score": row.avg_rating,
            "rating_count": row.rating_count,
            "favorite_count": row.favorite_count,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return _page_payload(items, total, page, page_size)
