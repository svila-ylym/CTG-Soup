from datetime import datetime

from sqlmodel import Session, select

from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionScoreType,
    CompetitionStatus,
    Soup,
    SoupTag,
    Tag,
    TagStatus,
)


def competition_tag_ids(competition: Competition) -> list[int]:
    """Return normalized tag IDs from the canonical JSON storage column."""
    normalized: list[int] = []
    for value in competition.required_tag_ids or []:
        try:
            tag_id = int(value)
        except (TypeError, ValueError):
            continue
        if tag_id > 0 and tag_id not in normalized:
            normalized.append(tag_id)
    return normalized


def _entry_score(competition: Competition, soup: Soup) -> float:
    if competition.score_type == CompetitionScoreType.TOP_SCORE:
        return float(max(soup.avg_rating, soup.bayesian_rating))
    return float(soup.avg_rating)


def evaluate_soup_competitions(db: Session, soup: Soup) -> list[CompetitionEntry]:
    """Create or return matching, unsettled competition entries for a soup."""
    if soup.id is None or soup.created_at is None:
        return []

    soup_tag_ids = set(
        db.exec(select(SoupTag.tag_id).where(SoupTag.soup_id == soup.id)).all()
    )
    if not soup_tag_ids:
        return []

    active_tag_ids = set(
        db.exec(
            select(Tag.id).where(
                Tag.id.in_(soup_tag_ids),
                Tag.status == TagStatus.ACTIVE,
            )
        ).all()
    )
    if not active_tag_ids:
        return []

    competitions = db.exec(
        select(Competition).where(
            Competition.status.in_([
                CompetitionStatus.PENDING,
                CompetitionStatus.ONGOING,
            ]),
            Competition.start_time <= soup.created_at,
            Competition.end_time >= soup.created_at,
            Competition.settled_at.is_(None),
        )
    ).all()

    entries: list[CompetitionEntry] = []
    for competition in competitions:
        if not active_tag_ids.intersection(competition_tag_ids(competition)):
            continue
        entry = db.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition.id,
                CompetitionEntry.soup_id == soup.id,
            )
        ).first()
        if entry is None:
            entry = CompetitionEntry(
                competition_id=competition.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
                final_score=_entry_score(competition, soup),
            )
            db.add(entry)
            db.flush()
        entries.append(entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


def settle_competition(db: Session, competition: Competition) -> dict:
    """Freeze entry ranking so later soup changes cannot rewrite results."""
    if competition.result_snapshot is not None:
        return competition.result_snapshot

    entries = db.exec(
        select(CompetitionEntry)
        .where(CompetitionEntry.competition_id == competition.id)
        .order_by(CompetitionEntry.final_score.desc(), CompetitionEntry.created_at)
    ).all()
    ranking = []
    for rank, entry in enumerate(entries[: competition.top_n], start=1):
        entry.rank = rank
        ranking.append(
            {
                "entry_id": entry.id,
                "soup_id": entry.soup_id,
                "author_uid": entry.author_uid,
                "final_score": entry.final_score,
                "rank": rank,
            }
        )
    now = datetime.utcnow()
    competition.result_snapshot = {"entries": ranking, "settled_at": now.isoformat()}
    competition.status = CompetitionStatus.COMPLETED
    competition.settled_at = now
    competition.updated_at = now
    db.commit()
    db.refresh(competition)
    return competition.result_snapshot
