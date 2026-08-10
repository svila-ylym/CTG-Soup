from datetime import datetime, timezone
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_admin_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    OperationLog,
    User,
    UploadedAsset,
    get_db,
)
from app.schemas.competitions import (
    CompetitionCreate,
    CompetitionPageResponse,
    CompetitionResponse,
    CompetitionUpdate,
)
from app.services.competition_entries import (
    collect_competition_entries,
    competition_tag_ids,
    delete_competition_entries,
    lock_competition_collection,
    settle_competition,
)
from app.services.tag_resolution import TagSelectionError, resolve_active_tags
from app.services.safe_html import sanitize_rich_html

router = APIRouter()


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _current_status(competition: Competition, now: datetime) -> CompetitionStatus:
    if competition.settled_at is not None:
        return CompetitionStatus.COMPLETED
    if now < competition.start_time:
        return CompetitionStatus.PENDING
    if now <= competition.end_time:
        return CompetitionStatus.ONGOING
    return CompetitionStatus.COMPLETED


def _sync_statuses(db: Session, competitions: list[Competition]) -> None:
    now = datetime.utcnow()
    changed = False
    for competition in competitions:
        current_status = _current_status(competition, now)
        if competition.status != current_status:
            competition.status = current_status
            competition.updated_at = now
            changed = True
    if changed:
        db.commit()


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
        "start_time": _utc(competition.start_time),
        "end_time": _utc(competition.end_time),
        "required_tag_ids": competition_tag_ids(competition),
        "score_type": competition.score_type,
        "top_n": competition.top_n,
        "custom_page_config": competition.custom_page_config,
        "status": competition.status,
        "result_snapshot": competition.result_snapshot,
        "created_at": _utc(competition.created_at),
        "updated_at": _utc(competition.updated_at),
        "settled_at": _utc(competition.settled_at),
        "entries": entries,
    }


def _resolve_competition_tags(db: Session, data: CompetitionCreate | CompetitionUpdate):
    try:
        return resolve_active_tags(
            db,
            data.required_tag_ids,
            data.custom_tags,
            min_count=1,
            max_count=10,
        )
    except TagSelectionError as exc:
        code = "COMPETITION_TAG_NOT_ACTIVE" if exc.code == "TAG_NOT_ACTIVE" else exc.code
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": exc.message},
        ) from exc


def _competition_content(
    db: Session,
    data: CompetitionCreate | CompetitionUpdate,
    owner_uid: int,
) -> tuple[str, dict]:
    description = sanitize_rich_html(data.description)
    text_description = re.sub(r"<[^>]+>", "", description).strip()
    if not text_description and "<img" not in description:
        raise HTTPException(status_code=422, detail="比赛说明不能为空")

    image_asset_ids = [
        int(value)
        for value in data.custom_page_config.get("image_asset_ids", [])
        if str(value).isdigit()
    ]
    unique_image_asset_ids = list(dict.fromkeys(image_asset_ids))
    if len(unique_image_asset_ids) > 20:
        raise HTTPException(status_code=422, detail="比赛图片最多 20 张")

    owned_urls: set[str] = set()
    if unique_image_asset_ids:
        owned = db.exec(
            select(UploadedAsset).where(
                UploadedAsset.owner_uid == owner_uid,
                UploadedAsset.id.in_(unique_image_asset_ids),
            )
        ).all()
        if len(owned) != len(unique_image_asset_ids):
            raise HTTPException(status_code=403, detail="比赛图片必须使用本人上传的图片")
        owned_urls = {asset.public_url for asset in owned}

    image_sources = set(re.findall(
        r"<img[^>]+src=[\"']([^\"']+)[\"']",
        description,
        flags=re.IGNORECASE,
    ))
    if any(source not in owned_urls for source in image_sources):
        raise HTTPException(status_code=422, detail="比赛正文图片必须来自已上传的图片")

    custom_page_config = dict(data.custom_page_config)
    custom_page_config.update({
        "format": "rich_html",
        "image_asset_ids": unique_image_asset_ids,
    })
    return description, custom_page_config


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
def create_competition(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    tags = _resolve_competition_tags(db, data)
    description, custom_page_config = _competition_content(db, data, current_user.uid)
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
        name=data.name,
        description=description,
        start_time=data.start_time,
        end_time=data.end_time,
        required_tag_ids=[tag.id for tag in tags],
        score_type=data.score_type,
        top_n=data.top_n,
        custom_page_config=custom_page_config,
        status=current_status,
    )
    db.add(competition)
    db.flush()
    collect_competition_entries(db, competition)
    db.commit()
    db.refresh(competition)
    return _payload(db, competition, include_entries=True)


@router.put("/{competition_id}", response_model=CompetitionResponse)
def update_competition(
    competition_id: int,
    data: CompetitionUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    if competition.creator_uid != current_user.uid:
        raise HTTPException(status_code=403, detail="只能修改自己发布的比赛")
    lock_competition_collection(db)
    db.refresh(competition)
    if competition.settled_at is not None:
        raise HTTPException(status_code=409, detail="已结算的比赛不能修改")

    tags = _resolve_competition_tags(db, data)
    description, custom_page_config = _competition_content(db, data, current_user.uid)
    competition.name = data.name
    competition.description = description
    competition.start_time = data.start_time
    competition.end_time = data.end_time
    competition.required_tag_ids = [tag.id for tag in tags]
    competition.score_type = data.score_type
    competition.top_n = data.top_n
    competition.custom_page_config = custom_page_config
    competition.status = _current_status(competition, datetime.utcnow())
    competition.updated_at = datetime.utcnow()
    delete_competition_entries(db, competition.id)
    db.flush()
    collect_competition_entries(db, competition)
    db.commit()
    db.refresh(competition)
    return _payload(db, competition, include_entries=True)


@router.get("", response_model=CompetitionPageResponse)
def list_competitions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[CompetitionStatus] = None,
    db: Session = Depends(get_db),
):
    _sync_statuses(db, db.exec(select(Competition)).all())
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
    _sync_statuses(db, [competition])
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
    if competition.settled_at is None and datetime.utcnow() < competition.end_time:
        raise HTTPException(status_code=409, detail="比赛尚未结束，不能结算")
    settle_competition(db, competition)
    return _payload(db, competition, include_entries=True)


@router.delete("/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_competition(
    competition_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    entry_count = delete_competition_entries(db, competition.id)
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete",
        target_type="competition",
        target_id=competition.id,
        details={"name": competition.name, "entry_count": entry_count},
    ))
    db.delete(competition)
    db.commit()
