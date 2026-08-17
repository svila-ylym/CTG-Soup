from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import re

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionScoreType,
    CompetitionStatus,
    Soup,
    Tag,
    User,
    get_db,
)
from app.services.competition_entries import (
    competition_colors_for_soups,
    competition_tag_ids,
)
from app.utils.cache import cache_delete, cache_get, cache_set, generate_cache_key

router = APIRouter()

DEFAULT_HOME_LINE = "一碗汤，一群人，一场从“为什么”开始的推理冒险。读故事、问线索、把藏起来的真相一点点拼完整。"
HOME_COPY_PATH = Path(__file__).resolve().parents[3] / "home.txt"
HOME_DISCOVERY_CACHE_KEY = generate_cache_key("home:discovery", schema=1)
HOME_DISCOVERY_CACHE_TTL_SECONDS = 60
HOME_DISCOVERY_BROWSER_CACHE = "public, max-age=30, stale-while-revalidate=120"


class HomeCompetitionSummary(BaseModel):
    id: int
    name: str
    description_excerpt: str
    cover_asset_id: int | None = None
    cover_url: str | None = None
    competition_color: str
    status: CompetitionStatus
    start_time: datetime
    end_time: datetime
    score_type: CompetitionScoreType
    top_n: int
    required_tags: list[str] = Field(default_factory=list)
    entry_count: int = 0


class HomeSoupSummary(BaseModel):
    id: int
    title: str
    puzzle_excerpt: str
    genre: str
    soup_color: str
    average_score: float
    rating_count: int
    author_name: str
    competition_colors: list[str] = Field(default_factory=list)
    is_hall_of_fame: bool = False
    created_at: datetime


class HomeDiscoveryResponse(BaseModel):
    lines: list[str] = Field(default_factory=lambda: [DEFAULT_HOME_LINE])
    latest_competition: HomeCompetitionSummary | None = None
    random_soups: list[HomeSoupSummary] = Field(default_factory=list)


def _home_lines() -> list[str]:
    try:
        content = HOME_COPY_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return [DEFAULT_HOME_LINE]
    lines = [line for raw_line in content.splitlines() if (line := raw_line.strip())]
    return lines or [DEFAULT_HOME_LINE]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _description_excerpt(value: str, limit: int = 220) -> str:
    plain = unescape(re.sub(r"<[^>]*>", " ", value))
    normalized = re.sub(r"\s+", " ", plain).strip()
    return normalized if len(normalized) <= limit else f"{normalized[:limit].rstrip()}…"


def _config_int(config: dict | None, key: str) -> int | None:
    value = (config or {}).get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _config_str(config: dict | None, key: str) -> str | None:
    value = (config or {}).get(key)
    return value if isinstance(value, str) and value.strip() else None


def _current_status(competition: Competition) -> CompetitionStatus:
    now = datetime.utcnow()
    if competition.settled_at is not None:
        return CompetitionStatus.COMPLETED
    if now < competition.start_time:
        return CompetitionStatus.PENDING
    if now <= competition.end_time:
        return CompetitionStatus.ONGOING
    return CompetitionStatus.COMPLETED


def _latest_competition(db: Session) -> HomeCompetitionSummary | None:
    competition = db.exec(
        select(Competition)
        .order_by(Competition.created_at.desc(), Competition.id.desc())
        .limit(1)
    ).first()
    if competition is None:
        return None

    tag_ids = competition_tag_ids(competition)
    tag_names = {
        tag.id: tag.name
        for tag in db.exec(select(Tag).where(Tag.id.in_(tag_ids))).all()
    } if tag_ids else {}
    entry_count = db.exec(
        select(func.count(CompetitionEntry.id)).where(
            CompetitionEntry.competition_id == competition.id
        )
    ).one()
    return HomeCompetitionSummary(
        id=competition.id,
        name=competition.name,
        description_excerpt=_description_excerpt(competition.description),
        cover_asset_id=_config_int(competition.custom_page_config, "cover_asset_id"),
        cover_url=_config_str(competition.custom_page_config, "cover_url"),
        competition_color=competition.competition_color,
        status=_current_status(competition),
        start_time=_utc(competition.start_time),
        end_time=_utc(competition.end_time),
        score_type=competition.score_type,
        top_n=competition.top_n,
        required_tags=[tag_names.get(tag_id, f"标签 #{tag_id}") for tag_id in tag_ids],
        entry_count=entry_count,
    )


def _random_soups(db: Session) -> list[HomeSoupSummary]:
    rows = db.exec(
        select(Soup, User)
        .join(User, User.uid == Soup.author_uid)
        .where(Soup.status.in_(["published", "revealed"]))
        .order_by(func.random())
        .limit(4)
    ).all()
    colors_by_soup = competition_colors_for_soups(
        db,
        [soup.id for soup, _user in rows],
    )
    return [
        HomeSoupSummary(
            id=soup.id,
            title=soup.title,
            puzzle_excerpt=_description_excerpt(soup.puzzle, limit=100),
            genre=soup.genre,
            soup_color=soup.soup_color,
            average_score=soup.avg_rating,
            rating_count=soup.rating_count,
            author_name=user.nickname or user.username,
            competition_colors=colors_by_soup.get(soup.id, []),
            is_hall_of_fame=soup.is_hall_of_fame,
            created_at=_utc(soup.created_at),
        )
        for soup, user in rows
    ]


def _build_discovery(db: Session) -> HomeDiscoveryResponse:
    return HomeDiscoveryResponse(
        lines=_home_lines(),
        latest_competition=_latest_competition(db),
        random_soups=_random_soups(db),
    )


@router.get("/lines")
async def get_home_lines() -> dict[str, list[str]]:
    return {"lines": _home_lines()}


@router.get("/discovery", response_model=HomeDiscoveryResponse)
def get_home_discovery(
    response: Response,
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
) -> HomeDiscoveryResponse:
    response.headers["Cache-Control"] = (
        "no-store" if refresh else HOME_DISCOVERY_BROWSER_CACHE
    )
    if not refresh:
        cached = cache_get(HOME_DISCOVERY_CACHE_KEY)
        if cached is not None:
            try:
                return HomeDiscoveryResponse.model_validate(cached)
            except ValidationError:
                cache_delete(HOME_DISCOVERY_CACHE_KEY)

    discovery = _build_discovery(db)
    if not refresh:
        cache_set(
            HOME_DISCOVERY_CACHE_KEY,
            discovery.model_dump(mode="json"),
            HOME_DISCOVERY_CACHE_TTL_SECONDS,
        )
    return discovery
