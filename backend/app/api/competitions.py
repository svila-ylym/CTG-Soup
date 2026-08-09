from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_admin_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Tag,
    TagStatus,
    User,
    get_db,
)
from app.schemas.competitions import (
    CompetitionCreate,
    CompetitionPageResponse,
    CompetitionResponse,
)
from app.services.competition_entries import competition_tag_ids, settle_competition

router = APIRouter()


def _payload(db: Session, competition: Competition, include_entries: bool = False) -> dict:
    entries = []
    if include_entries:
        entries = db.exec(
            select(CompetitionEntry)
            .where(CompetitionEntry.competition_id == competition.id)
            .order_by(CompetitionEntry.rank.is_(None), CompetitionEntry.rank, CompetitionEntry.created_at)
        ).all()
    return {
        "id": competition.id,
        "creator_uid": competition.creator_uid,
        "name": competition.name,
        "description": competition.description,
        "start_time": competition.start_time,
        "end_time": competition.end_time,
        "required_tag_ids": competition_tag_ids(competition),
        "score_type": competition.score_type,
        "top_n": competition.top_n,
        "custom_page_config": competition.custom_page_config,
        "status": competition.status,
        "result_snapshot": competition.result_snapshot,
        "created_at": competition.created_at,
        "updated_at": competition.updated_at,
        "settled_at": competition.settled_at,
        "entries": entries,
    }


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
def create_competition(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    tags = db.exec(select(Tag).where(Tag.id.in_(data.required_tag_ids))).all()
    active_ids = {tag.id for tag in tags if tag.status == TagStatus.ACTIVE}
    if active_ids != set(data.required_tag_ids):
        raise HTTPException(
            status_code=422,
            detail={"code": "COMPETITION_TAG_NOT_ACTIVE", "message": "比赛只能引用已启用标签"},
        )

    now = datetime.utcnow()
    current_status = (
        CompetitionStatus.PENDING
        if now < data.start_time
        else CompetitionStatus.ONGOING
        if now <= data.end_time
        else CompetitionStatus.COMPLETED
    )
    competition = Competition(
        creator_uid=current_user.uid,
        name=data.name.strip(),
        description=data.description.strip(),
        start_time=data.start_time,
        end_time=data.end_time,
        required_tag_ids=data.required_tag_ids,
        score_type=data.score_type,
        top_n=data.top_n,
        custom_page_config=data.custom_page_config,
        status=current_status,
    )
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return _payload(db, competition)


@router.get("", response_model=CompetitionPageResponse)
def list_competitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[CompetitionStatus] = None,
    db: Session = Depends(get_db),
):
    query = select(Competition)
    if status_filter is not None:
        query = query.where(Competition.status == status_filter)
    total = len(db.exec(query).all())
    rows = db.exec(
        query.order_by(Competition.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_payload(db, competition) for competition in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{competition_id}", response_model=CompetitionResponse)
def get_competition(competition_id: int, db: Session = Depends(get_db)):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    return _payload(db, competition, include_entries=True)


@router.post("/{competition_id}/settle", response_model=CompetitionResponse)
def settle_competition_endpoint(
    competition_id: int,
    _current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if competition.status != CompetitionStatus.COMPLETED and datetime.utcnow() < competition.end_time:
        raise HTTPException(status_code=409, detail="比赛尚未结束，不能结算")
    settle_competition(db, competition)
    return _payload(db, competition, include_entries=True)
