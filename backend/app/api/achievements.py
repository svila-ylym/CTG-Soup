from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db, AchievementDefinition, UserAchievement, User
from app.schemas import AchievementDefinitionCreate, AchievementDefinitionResponse, UserAchievementResponse, PageResponse
from app.api.auth import get_current_active_user, get_current_admin_user, get_current_root_user

router = APIRouter()


@router.get("", response_model=PageResponse)
async def list_achievements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取成就列表"""
    offset = (page - 1) * page_size
    
    query = db.query(AchievementDefinition)
    
    if is_active is not None:
        query = query.filter(AchievementDefinition.is_active == is_active)
    
    query = query.order_by(AchievementDefinition.created_at.desc())
    
    total = query.count()
    achievements = query.offset(offset).limit(page_size).all()
    
    items = []
    for achievement in achievements:
        items.append({
            "id": achievement.id,
            "code": achievement.code,
            "name": achievement.name,
            "description": achievement.description,
            "icon_url": achievement.icon_url,
            "condition_type": achievement.condition_type,
            "condition_params": achievement.condition_params,
            "is_repeatable": achievement.is_repeatable,
            "is_active": achievement.is_active,
            "created_at": achievement.created_at,
            "updated_at": achievement.updated_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("", response_model=AchievementDefinitionResponse)
async def create_achievement(
    achievement_data: AchievementDefinitionCreate,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db)
):
    """创建成就定义（仅根用户）"""
    existing = db.query(AchievementDefinition).filter(
        AchievementDefinition.code == achievement_data.code
    ).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="成就代码已存在")
    
    db_achievement = AchievementDefinition(
        code=achievement_data.code,
        name=achievement_data.name,
        description=achievement_data.description,
        icon_url=achievement_data.icon_url,
        condition_type=achievement_data.condition_type,
        condition_params=achievement_data.condition_params,
        is_repeatable=achievement_data.is_repeatable,
        is_active=True,
    )
    
    db.add(db_achievement)
    db.commit()
    db.refresh(db_achievement)
    
    return db_achievement


@router.get("/my", response_model=PageResponse)
async def get_my_achievements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取我的成就"""
    offset = (page - 1) * page_size
    
    query = db.query(UserAchievement).filter(
        UserAchievement.user_id == current_user.id
    ).join(AchievementDefinition)
    
    total = query.count()
    user_achievements = query.offset(offset).limit(page_size).all()
    
    items = []
    for ua in user_achievements:
        items.append({
            "id": ua.id,
            "achievement_id": ua.achievement_id,
            "achievement_name": ua.achievement_definition.name,
            "achievement_icon": ua.achievement_definition.icon_url,
            "current_value": ua.current_value,
            "is_completed": ua.is_completed,
            "completed_at": ua.completed_at,
            "granted_count": ua.granted_count,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
