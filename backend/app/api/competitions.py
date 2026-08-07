from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.models.database import get_db, Competition, CompetitionEntry, TurtleSoup, User
from app.schemas import CompetitionCreate, CompetitionResponse, PageResponse
from app.api.auth import get_current_active_user, get_current_admin_user

router = APIRouter()


@router.post("", response_model=CompetitionResponse)
async def create_competition(
    competition_data: CompetitionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """创建比赛（仅管理员）"""
    if competition_data.start_time >= competition_data.end_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="开始时间必须早于结束时间")
    
    db_competition = Competition(
        creator_id=current_user.id,
        name=competition_data.name,
        description=competition_data.description,
        start_time=competition_data.start_time,
        end_time=competition_data.end_time,
        entry_tags=competition_data.entry_tags,
        scoring_method=competition_data.scoring_method,
        top_n=competition_data.top_n,
        custom_page_config=competition_data.custom_page_config,
        status="pending",
    )
    
    db.add(db_competition)
    db.commit()
    db.refresh(db_competition)
    
    return db_competition


@router.get("/{competition_id}", response_model=CompetitionResponse)
async def get_competition(
    competition_id: int,
    db: Session = Depends(get_db)
):
    """获取比赛详情"""
    competition = db.query(Competition).filter(Competition.id == competition_id).first()
    if not competition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="比赛不存在")
    return competition


@router.get("")
async def list_competitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取比赛列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Competition)
    
    if status_filter:
        query = query.filter(Competition.status == status_filter)
    
    query = query.order_by(Competition.created_at.desc())
    
    total = query.count()
    competitions = query.offset(offset).limit(page_size).all()
    
    items = []
    for comp in competitions:
        items.append({
            "id": comp.id,
            "name": comp.name,
            "description": comp.description,
            "start_time": comp.start_time,
            "end_time": comp.end_time,
            "entry_tags": comp.entry_tags,
            "scoring_method": comp.scoring_method,
            "top_n": comp.top_n,
            "custom_page_config": comp.custom_page_config,
            "status": comp.status,
            "result_snapshot": comp.result_snapshot,
            "creator_id": comp.creator_id,
            "created_at": comp.created_at,
            "updated_at": comp.updated_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
