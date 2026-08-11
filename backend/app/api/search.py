from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.database import Post, Soup, User, get_db
from app.schemas.community import (
    SearchPostPageResponse,
    SearchSoupPageResponse,
    UserPageResponse,
    UserSummary,
)
from app.services.levels import level_band, level_progress
from app.services.competition_entries import competition_colors_for_soups
from app.services.user_display import user_display_fields
from app.api.auth import get_optional_current_user
from app.services.easter_eggs import SEARCH_PHRASE, safely_claim_and_attach

router = APIRouter()


def _check_search_egg(
    db: Session,
    user: Optional[User],
    response: Response,
    term: str,
    track_egg: bool,
) -> None:
    if user is not None and track_egg and term == SEARCH_PHRASE:
        safely_claim_and_attach(db, user, response, [(7, "exact_search")])


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
    response: Response,
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    track_egg: bool = False,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    term = q.strip()
    _check_search_egg(db, current_user, response, term, track_egg)
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
            level=level_progress(row.points).level,
            level_band=level_band(level_progress(row.points).level),
            **user_display_fields(db, row),
        ).model_dump()
        for row in rows
    ]
    return _page_payload(items, total, page, page_size)


@router.get("/posts", response_model=SearchPostPageResponse)
def search_posts(
    response: Response,
    q: str = Query(min_length=1, max_length=100),
    section: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    track_egg: bool = False,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    term = q.strip()
    _check_search_egg(db, current_user, response, term, track_egg)
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
    response: Response,
    q: str = Query(min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    track_egg: bool = False,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    term = q.strip()
    _check_search_egg(db, current_user, response, term, track_egg)
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
    colors_by_soup = competition_colors_for_soups(db, [row.id for row in rows])
    items = [
        {
            "id": row.id,
            "author_uid": row.author_uid,
            "title": row.title,
            "puzzle_excerpt": row.puzzle[:200],
            "average_score": row.avg_rating,
            "rating_count": row.rating_count,
            "favorite_count": row.favorite_count,
            "competition_colors": colors_by_soup.get(row.id, []),
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return _page_payload(items, total, page, page_size)
