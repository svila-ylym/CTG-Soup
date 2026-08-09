from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.models.database import Tag, TagKind, TagStatus, get_db
from app.schemas.soups import TagPageResponse

router = APIRouter()


@router.get("", response_model=TagPageResponse)
def list_tags(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Optional[TagKind] = None,
    keyword: Optional[str] = Query(None, min_length=1, max_length=30),
    sort_by: str = Query("usage_count", pattern="^(usage_count|view_count|name)$"),
    db: Session = Depends(get_db),
):
    query = select(Tag).where(Tag.status == TagStatus.ACTIVE)
    if kind:
        query = query.where(Tag.kind == kind)
    if keyword:
        query = query.where(Tag.name.ilike(f"%{keyword.strip()}%"))
    order = {
        "view_count": Tag.view_count.desc(),
        "name": Tag.name.asc(),
        "usage_count": Tag.usage_count.desc(),
    }[sort_by]
    total = len(db.exec(query).all())
    rows = db.exec(
        query.order_by(order, Tag.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }
