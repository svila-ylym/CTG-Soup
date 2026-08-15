from datetime import datetime, timezone
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_current_admin_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionScoreType,
    CompetitionStatus,
    OperationLog,
    Soup,
    Tag,
    User,
    UserRole,
    UploadedAsset,
    get_db,
)
from app.schemas.competitions import (
    CompetitionCreate,
    CompetitionJudgeScoreUpdate,
    CompetitionJudgingEntryResponse,
    CompetitionJudgingResponse,
    CompetitionPageResponse,
    CompetitionResponse,
    CompetitionUpdate,
)
from app.services.competition_entries import (
    CompetitionNotEndedError,
    IndependentScoringIncompleteError,
    IndependentScoringNotOpenError,
    collect_competition_entries,
    competition_optional_tag_ids,
    competition_rankings,
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


def _can_judge_competition(competition: Competition, user: User) -> bool:
    return (
        competition.creator_uid == user.uid
        or user.role in {UserRole.ADMIN, UserRole.ROOT}
    )


def _require_judging_access(competition: Competition, user: User) -> None:
    if not _can_judge_competition(competition, user):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "COMPETITION_JUDGING_FORBIDDEN",
                "message": "无权查看或修改比赛方评分",
            },
        )


def _require_independent_competition(competition: Competition) -> None:
    if competition.score_type != CompetitionScoreType.INDEPENDENT:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "NOT_INDEPENDENT_COMPETITION",
                "message": "该比赛不使用独评方式",
            },
        )


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


def _config_optional_int(config: dict | None, key: str) -> int | None:
    value = (config or {}).get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _config_optional_str(config: dict | None, key: str) -> str | None:
    value = (config or {}).get(key)
    return value if isinstance(value, str) and value.strip() else None


def _payload(
    db: Session,
    competition: Competition,
    include_entries: bool = False,
    tag_names_by_id: dict[int, str] | None = None,
) -> dict:
    entries = []
    if include_entries:
        entry_rows = db.exec(
            select(CompetitionEntry)
            .where(CompetitionEntry.competition_id == competition.id)
            .order_by(CompetitionEntry.rank.is_(None), CompetitionEntry.rank, CompetitionEntry.created_at)
        ).all()
        soup_ids = {entry.soup_id for entry in entry_rows}
        soup_titles = {
            soup.id: soup.title
            for soup in db.exec(select(Soup).where(Soup.id.in_(soup_ids))).all()
        } if soup_ids else {}
        entries = [
            {
                "id": entry.id,
                "competition_id": entry.competition_id,
                "soup_id": entry.soup_id,
                "soup_title": soup_titles.get(entry.soup_id, "已删除作品"),
                "author_uid": entry.author_uid,
                "final_score": (
                    None
                    if competition.score_type == CompetitionScoreType.INDEPENDENT
                    and competition.settled_at is None
                    else entry.final_score
                ),
                "rank": entry.rank,
                "created_at": _utc(entry.created_at),
            }
            for entry in entry_rows
        ]
    required_tag_ids = competition_tag_ids(competition)
    optional_tag_ids = competition_optional_tag_ids(competition)
    if tag_names_by_id is None:
        all_tag_ids = list(dict.fromkeys(required_tag_ids + optional_tag_ids))
        tag_names_by_id = {
            tag.id: tag.name
            for tag in db.exec(select(Tag).where(Tag.id.in_(all_tag_ids))).all()
        } if all_tag_ids else {}
    return {
        "id": competition.id,
        "creator_uid": competition.creator_uid,
        "name": competition.name,
        "description": competition.description,
        "start_time": _utc(competition.start_time),
        "end_time": _utc(competition.end_time),
        "required_tag_ids": required_tag_ids,
        "required_tags": [
            {
                "id": tag_id,
                "name": tag_names_by_id.get(tag_id, f"标签 #{tag_id}"),
            }
            for tag_id in required_tag_ids
        ],
        "optional_tag_ids": optional_tag_ids,
        "optional_tags": [
            {
                "id": tag_id,
                "name": tag_names_by_id.get(tag_id, f"标签 #{tag_id}"),
            }
            for tag_id in optional_tag_ids
        ],
        "cover_asset_id": _config_optional_int(
            competition.custom_page_config,
            "cover_asset_id",
        ),
        "cover_url": _config_optional_str(
            competition.custom_page_config,
            "cover_url",
        ),
        "competition_color": competition.competition_color,
        "score_type": competition.score_type,
        "scoring_at": _utc(competition.scoring_at),
        "top_n": competition.top_n,
        "custom_page_config": competition.custom_page_config,
        "status": competition.status,
        "result_snapshot": competition.result_snapshot,
        "created_at": _utc(competition.created_at),
        "updated_at": _utc(competition.updated_at),
        "settled_at": _utc(competition.settled_at),
        "entries": entries,
        "rankings": (
            competition_rankings(db, competition)
            if include_entries
            else {"total": [], "groups": []}
        ),
    }


def _resolve_competition_tags(db: Session, data: CompetitionCreate | CompetitionUpdate):
    try:
        required_tags = resolve_active_tags(
            db,
            data.required_tag_ids,
            data.custom_tags,
            min_count=1,
            max_count=10,
        )
        optional_tags = resolve_active_tags(
            db,
            data.optional_tag_ids,
            data.optional_custom_tags,
            min_count=0,
            max_count=10,
        )
    except TagSelectionError as exc:
        code = "COMPETITION_TAG_NOT_ACTIVE" if exc.code == "TAG_NOT_ACTIVE" else exc.code
        raise HTTPException(
            status_code=422,
            detail={"code": code, "message": exc.message},
        ) from exc
    if {tag.id for tag in required_tags}.intersection(tag.id for tag in optional_tags):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COMPETITION_TAG_ROLE_CONFLICT",
                "message": "同一标签不能同时设为必选和可选",
            },
        )
    return required_tags, optional_tags


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

    cover: UploadedAsset | None = None
    if data.cover_asset_id is not None:
        cover = db.exec(
            select(UploadedAsset).where(
                UploadedAsset.id == data.cover_asset_id,
                UploadedAsset.owner_uid == owner_uid,
                UploadedAsset.kind == "image",
            )
        ).first()
        if cover is None:
            raise HTTPException(
                status_code=403,
                detail="比赛封面必须使用本人上传的图片",
            )

    custom_page_config = dict(data.custom_page_config)
    custom_page_config.pop("cover_asset_id", None)
    custom_page_config.pop("cover_url", None)
    custom_page_config.update({
        "format": "rich_html",
        "image_asset_ids": unique_image_asset_ids,
    })
    if cover is not None:
        custom_page_config.update({
            "cover_asset_id": cover.id,
            "cover_url": cover.public_url,
        })
    return description, custom_page_config


@router.post("", response_model=CompetitionResponse, status_code=status.HTTP_201_CREATED)
def create_competition(
    data: CompetitionCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    required_tags, optional_tags = _resolve_competition_tags(db, data)
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
        required_tag_ids=[tag.id for tag in required_tags],
        optional_tag_ids=[tag.id for tag in optional_tags],
        competition_color=data.competition_color,
        score_type=data.score_type,
        scoring_at=data.scoring_at,
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

    resolved_data = data
    scoring_update: dict = {}
    if "score_type" not in data.model_fields_set:
        scoring_update["score_type"] = competition.score_type
    if "scoring_at" not in data.model_fields_set:
        scoring_update["scoring_at"] = competition.scoring_at
    if scoring_update:
        resolved_data = resolved_data.model_copy(update=scoring_update)
    if not {"optional_tag_ids", "optional_custom_tags"}.intersection(
        data.model_fields_set
    ):
        resolved_data = resolved_data.model_copy(update={
            "optional_tag_ids": competition_optional_tag_ids(competition),
            "optional_custom_tags": [],
        })
    if "cover_asset_id" not in data.model_fields_set:
        resolved_data = resolved_data.model_copy(update={
            "cover_asset_id": _config_optional_int(
                competition.custom_page_config,
                "cover_asset_id",
            ),
        })
    if resolved_data.score_type == CompetitionScoreType.INDEPENDENT:
        if resolved_data.scoring_at is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INDEPENDENT_SCORING_DATE_REQUIRED",
                    "message": "独评比赛必须设置评分日期",
                },
            )
        if resolved_data.scoring_at < resolved_data.end_time:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_INDEPENDENT_SCORING_DATE",
                    "message": "评分日期不能早于比赛结束时间",
                },
            )
    elif resolved_data.scoring_at is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "AVERAGE_SCORING_DATE_FORBIDDEN",
                "message": "平均分比赛不能设置评分日期",
            },
        )
    required_tags, optional_tags = _resolve_competition_tags(db, resolved_data)
    description, custom_page_config = _competition_content(
        db,
        resolved_data,
        current_user.uid,
    )
    next_required_tag_ids = [tag.id for tag in required_tags]
    next_optional_tag_ids = [tag.id for tag in optional_tags]
    has_judge_scores = db.exec(
        select(CompetitionEntry.id).where(
            CompetitionEntry.competition_id == competition.id,
            CompetitionEntry.judge_score.is_not(None),
        )
    ).first() is not None
    collection_changed = any((
        resolved_data.start_time != competition.start_time,
        resolved_data.end_time != competition.end_time,
        next_required_tag_ids != competition_tag_ids(competition),
        next_optional_tag_ids != competition_optional_tag_ids(competition),
    ))
    scoring_changed = any((
        resolved_data.score_type != competition.score_type,
        resolved_data.scoring_at != competition.scoring_at,
    ))
    if has_judge_scores and (collection_changed or scoring_changed):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INDEPENDENT_SCORING_LOCKED",
                "message": "已有比赛方评分，不能修改评分配置或参赛范围",
            },
        )
    competition.name = data.name
    competition.description = description
    competition.start_time = resolved_data.start_time
    competition.end_time = resolved_data.end_time
    competition.required_tag_ids = next_required_tag_ids
    competition.optional_tag_ids = next_optional_tag_ids
    if "competition_color" in data.model_fields_set:
        competition.competition_color = data.competition_color
    competition.score_type = resolved_data.score_type
    competition.scoring_at = resolved_data.scoring_at
    competition.top_n = data.top_n
    competition.custom_page_config = custom_page_config
    competition.status = _current_status(competition, datetime.utcnow())
    competition.updated_at = datetime.utcnow()
    if not has_judge_scores:
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
    tag_ids = list(dict.fromkeys(
        tag_id
        for competition in rows
        for tag_id in (
            competition_tag_ids(competition)
            + competition_optional_tag_ids(competition)
        )
    ))
    tag_names_by_id = {
        tag.id: tag.name
        for tag in db.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()
    } if tag_ids else {}
    return {
        "items": [
            _payload(db, competition, tag_names_by_id=tag_names_by_id)
            for competition in rows
        ],
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


@router.get(
    "/{competition_id}/judging",
    response_model=CompetitionJudgingResponse,
)
def get_competition_judging(
    competition_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    _require_judging_access(competition, current_user)
    _require_independent_competition(competition)
    entries = db.exec(
        select(CompetitionEntry, Soup)
        .join(Soup, Soup.id == CompetitionEntry.soup_id)
        .where(CompetitionEntry.competition_id == competition.id)
        .order_by(Soup.created_at, Soup.id)
    ).all()
    return {
        "competition_id": competition.id,
        "competition_name": competition.name,
        "score_type": competition.score_type,
        "scoring_at": _utc(competition.scoring_at),
        "settled_at": _utc(competition.settled_at),
        "scored_count": sum(entry.judge_score is not None for entry, _soup in entries),
        "total_count": len(entries),
        "entries": [
            CompetitionJudgingEntryResponse(
                entry_id=entry.id,
                soup_id=soup.id,
                soup_title=soup.title,
                author_uid=entry.author_uid,
                judge_score=entry.judge_score,
                judged_by_uid=entry.judged_by_uid,
                judged_at=_utc(entry.judged_at),
            )
            for entry, soup in entries
        ],
    }


@router.put(
    "/{competition_id}/entries/{entry_id}/judge-score",
    response_model=CompetitionJudgingEntryResponse,
)
def update_competition_judge_score(
    competition_id: int,
    entry_id: int,
    data: CompetitionJudgeScoreUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    _require_judging_access(competition, current_user)
    _require_independent_competition(competition)
    lock_competition_collection(db)
    db.refresh(competition)
    if competition.settled_at is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INDEPENDENT_SCORING_LOCKED",
                "message": "比赛已结算，不能修改比赛方评分",
            },
        )
    if competition.scoring_at is None or datetime.utcnow() < competition.scoring_at:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INDEPENDENT_SCORING_NOT_OPEN",
                "message": "尚未到比赛方评分日期",
            },
        )
    row = db.exec(
        select(CompetitionEntry, Soup)
        .join(Soup, Soup.id == CompetitionEntry.soup_id)
        .where(
            CompetitionEntry.id == entry_id,
            CompetitionEntry.competition_id == competition.id,
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "COMPETITION_ENTRY_NOT_FOUND",
                "message": "参赛作品不存在",
            },
        )
    entry, soup = row
    entry.judge_score = data.score
    entry.judged_by_uid = current_user.uid
    entry.judged_at = datetime.utcnow()
    db.commit()
    db.refresh(entry)
    return {
        "entry_id": entry.id,
        "soup_id": soup.id,
        "soup_title": soup.title,
        "author_uid": entry.author_uid,
        "judge_score": entry.judge_score,
        "judged_by_uid": entry.judged_by_uid,
        "judged_at": _utc(entry.judged_at),
    }


@router.post("/{competition_id}/settle", response_model=CompetitionResponse)
def settle_competition_endpoint(
    competition_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    competition = db.get(Competition, competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="比赛不存在")
    _require_judging_access(competition, current_user)
    try:
        settle_competition(db, competition)
    except CompetitionNotEndedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IndependentScoringNotOpenError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INDEPENDENT_SCORING_NOT_OPEN",
                "message": str(exc),
            },
        ) from exc
    except IndependentScoringIncompleteError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INDEPENDENT_SCORING_INCOMPLETE",
                "message": str(exc),
                "missing_count": exc.missing_count,
            },
        ) from exc
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
