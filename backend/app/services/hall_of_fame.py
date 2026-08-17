"""Hall of fame qualification and persistence rules for turtle soups."""

from datetime import datetime
from math import ceil

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.database import HallOfFameSettings, Soup, User, UserStatus


DEFAULT_SCORE_THRESHOLD = 9.85
DEFAULT_RATING_COVERAGE_RATIO = 0.5


def get_settings(db: Session) -> HallOfFameSettings:
    settings = db.get(HallOfFameSettings, 1)
    if settings is None:
        settings = HallOfFameSettings(
            id=1,
            score_threshold=DEFAULT_SCORE_THRESHOLD,
            rating_coverage_ratio=DEFAULT_RATING_COVERAGE_RATIO,
        )
        db.add(settings)
        db.flush()
    return settings


def active_user_count(db: Session) -> int:
    return int(
        db.exec(
            select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
        ).one()
        or 0
    )


def qualifies(
    db: Session,
    soup: Soup,
    settings: HallOfFameSettings | None = None,
    total_users: int | None = None,
) -> bool:
    if soup.genre == "鳖汤":
        return False
    settings = settings or get_settings(db)
    total_users = active_user_count(db) if total_users is None else total_users
    if total_users <= 0:
        return False
    required_ratings = ceil(total_users * settings.rating_coverage_ratio)
    return (
        soup.avg_rating >= settings.score_threshold
        and soup.rating_count >= required_ratings
    )


def evaluate_soup(db: Session, soup: Soup) -> bool:
    """Enter a qualifying soup once; explicit removals suppress re-entry."""
    if soup.genre == "鳖汤":
        if soup.is_hall_of_fame:
            soup.is_hall_of_fame = False
            soup.hall_of_fame_entered_at = None
            soup.updated_at = datetime.utcnow()
        return False
    if soup.is_hall_of_fame or soup.hall_of_fame_removed_at is not None:
        return False
    if not qualifies(db, soup):
        return False
    soup.is_hall_of_fame = True
    soup.hall_of_fame_entered_at = datetime.utcnow()
    soup.updated_at = datetime.utcnow()
    return True


def evaluate_all(db: Session) -> int:
    settings = get_settings(db)
    total_users = active_user_count(db)
    existing_bie_soups = db.exec(
        select(Soup).where(
            Soup.genre == "鳖汤",
            Soup.is_hall_of_fame.is_(True),
        ).with_for_update()
    ).all()
    for soup in existing_bie_soups:
        soup.is_hall_of_fame = False
        soup.hall_of_fame_entered_at = None
        soup.updated_at = datetime.utcnow()

    rows = db.exec(
        select(Soup).where(
            Soup.status.in_(["published", "revealed"]),
            Soup.genre != "鳖汤",
            Soup.is_hall_of_fame.is_(False),
            Soup.hall_of_fame_removed_at.is_(None),
        ).with_for_update()
    ).all()
    added = 0
    for soup in rows:
        if qualifies(db, soup, settings, total_users):
            soup.is_hall_of_fame = True
            soup.hall_of_fame_entered_at = datetime.utcnow()
            soup.updated_at = datetime.utcnow()
            added += 1
    return added
