"""Public browsing and owner management for soup collections."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import exists, func, update
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import Soup, SoupCollection, User, get_db
from app.schemas.collections import (
    CollectionCreate,
    CollectionDetail,
    CollectionMinePage,
    CollectionPage,
    CollectionSummary,
    CollectionUpdate,
)
from app.schemas.soups import AuthorSummary
from app.services.competition_entries import competition_colors_for_soups
from app.services.levels import level_band, level_progress


router = APIRouter()
PUBLIC_SOUP_STATUSES = ("published", "revealed")


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "COLLECTION_NOT_FOUND", "message": "合集不存在"},
    )


def _public_soup_count(db: Session, collection_id: int) -> int:
    return db.exec(
        select(func.count())
        .select_from(Soup)
        .where(
            Soup.collection_id == collection_id,
            Soup.status.in_(PUBLIC_SOUP_STATUSES),
        )
    ).one()


def _summary(
    db: Session,
    collection: SoupCollection,
    soup_count: Optional[int] = None,
) -> CollectionSummary:
    return CollectionSummary(
        id=collection.id,
        owner_uid=collection.owner_uid,
        name=collection.name,
        description=collection.description,
        soup_count=(
            _public_soup_count(db, collection.id)
            if soup_count is None
            else soup_count
        ),
        created_at=collection.created_at,
        updated_at=collection.updated_at,
    )


def _author(user: User) -> AuthorSummary:
    progress = level_progress(user.points)
    return AuthorSummary(
        uid=user.uid,
        username=user.username,
        nickname=user.nickname,
        level=progress.level,
        level_band=level_band(progress.level),
    )


def _owned_collection(
    db: Session,
    collection_id: int,
    current_user: User,
) -> SoupCollection:
    collection = db.get(SoupCollection, collection_id)
    if collection is None:
        raise _not_found()
    if collection.owner_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "COLLECTION_MANAGE_FORBIDDEN",
                "message": "无权管理此合集",
            },
        )
    return collection


def _page_payload(
    db: Session,
    rows: list[SoupCollection],
    total: int,
    page: int,
    page_size: int,
) -> dict:
    counts = dict(
        db.exec(
            select(Soup.collection_id, func.count(Soup.id))
            .where(
                Soup.collection_id.in_([row.id for row in rows]),
                Soup.status.in_(PUBLIC_SOUP_STATUSES),
            )
            .group_by(Soup.collection_id)
        ).all()
    ) if rows else {}
    return {
        "items": [
            _summary(db, row, counts.get(row.id, 0))
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=CollectionSummary, status_code=status.HTTP_201_CREATED)
def create_collection(
    data: CollectionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    collection = SoupCollection(
        owner_uid=current_user.uid,
        name=data.name,
        description=data.description,
    )
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return _summary(db, collection, 0)


@router.get("", response_model=CollectionPage)
def list_collections(
    owner_uid: int = Query(..., gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    filters = [SoupCollection.owner_uid == owner_uid]
    if current_user is None or current_user.uid != owner_uid:
        filters.append(
            exists().where(
                Soup.collection_id == SoupCollection.id,
                Soup.status.in_(PUBLIC_SOUP_STATUSES),
            )
        )
    total = db.exec(
        select(func.count())
        .select_from(SoupCollection)
        .where(*filters)
    ).one()
    rows = db.exec(
        select(SoupCollection)
        .where(*filters)
        .order_by(SoupCollection.created_at.desc(), SoupCollection.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _page_payload(db, rows, total, page, page_size)


@router.get("/mine", response_model=CollectionMinePage)
def list_my_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    filters = [SoupCollection.owner_uid == current_user.uid]
    total = db.exec(
        select(func.count())
        .select_from(SoupCollection)
        .where(*filters)
    ).one()
    rows = db.exec(
        select(SoupCollection)
        .where(*filters)
        .order_by(SoupCollection.created_at.desc(), SoupCollection.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _page_payload(db, rows, total, page, page_size)


@router.get("/{collection_id}", response_model=CollectionDetail)
def get_collection(
    collection_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    collection = db.get(SoupCollection, collection_id)
    if collection is None:
        raise _not_found()
    is_owner = current_user is not None and current_user.uid == collection.owner_uid
    total = _public_soup_count(db, collection_id)
    if total == 0 and not is_owner:
        raise _not_found()

    soups = db.exec(
        select(Soup)
        .where(
            Soup.collection_id == collection_id,
            Soup.status.in_(PUBLIC_SOUP_STATUSES),
        )
        .order_by(Soup.created_at.asc(), Soup.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    colors = competition_colors_for_soups(db, [soup.id for soup in soups])
    user = db.get(User, collection.owner_uid)
    if user is None:
        raise _not_found()
    summary = _summary(db, collection, total)
    return {
        **summary.model_dump(),
        "author": _author(user),
        "soups": {
            "items": [
                {
                    "id": soup.id,
                    "title": soup.title,
                    "puzzle_excerpt": soup.puzzle[:200],
                    "genre": soup.genre,
                    "soup_color": soup.soup_color,
                    "average_score": soup.avg_rating,
                    "rating_count": soup.rating_count,
                    "like_count": soup.like_count,
                    "competition_colors": colors.get(soup.id, []),
                    "is_hall_of_fame": soup.is_hall_of_fame,
                    "created_at": soup.created_at,
                }
                for soup in soups
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.put("/{collection_id}", response_model=CollectionSummary)
def update_collection(
    collection_id: int,
    data: CollectionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    collection = _owned_collection(db, collection_id, current_user)
    collection.name = data.name
    collection.description = data.description
    collection.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(collection)
    return _summary(db, collection)


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(
    collection_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    collection = _owned_collection(db, collection_id, current_user)
    db.exec(
        update(Soup)
        .where(Soup.collection_id == collection_id)
        .values(collection_id=None)
    )
    db.delete(collection)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
