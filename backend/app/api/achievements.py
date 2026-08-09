from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_current_root_user
from app.models.database import Achievement, User, UserAchievement, get_db
from app.schemas.community import AchievementCreate, AchievementPageResponse, UserAchievementPageResponse

router = APIRouter()


def _achievement(item: Achievement) -> dict:
    return {"id": item.id, "code": item.code, "name": item.name, "description": item.description, "icon_url": item.icon_url, "condition_type": item.condition_type, "condition_params": item.condition_params, "is_repeatable": item.is_repeatable, "title_id": item.title_id, "created_at": item.created_at}


def _page(items, page: int, page_size: int) -> dict:
    total = len(items)
    rows = items[(page - 1) * page_size : page * page_size]
    return {"items": rows, "total": total, "page": page, "page_size": page_size, "total_pages": (total + page_size - 1) // page_size}


@router.get("", response_model=AchievementPageResponse)
def list_achievements(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    items = [_achievement(item) for item in db.exec(select(Achievement).order_by(Achievement.created_at.desc())).all()]
    return _page(items, page, page_size)


@router.post("", response_model=AchievementPageResponse, status_code=status.HTTP_201_CREATED)
def create_achievement(data: AchievementCreate, _current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    if db.exec(select(Achievement).where(Achievement.code == data.code)).first() is not None:
        raise HTTPException(status_code=409, detail="成就代码已存在")
    item = Achievement(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _page([_achievement(item)], 1, 1)


@router.get("/my", response_model=UserAchievementPageResponse)
def my_achievements(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    rows = db.exec(select(UserAchievement).where(UserAchievement.user_uid == current_user.uid).order_by(UserAchievement.created_at.desc())).all()
    items = []
    for row in rows:
        achievement = db.get(Achievement, row.achievement_id)
        if achievement:
            items.append({"id": row.id, "user_uid": row.user_uid, "achievement_id": row.achievement_id, "achievement": _achievement(achievement), "current_value": row.current_value, "is_achieved": row.is_achieved, "achieved_at": row.achieved_at, "created_at": row.created_at, "updated_at": row.updated_at})
    return _page(items, page, page_size)
