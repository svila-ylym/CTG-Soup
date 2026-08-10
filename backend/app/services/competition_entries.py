from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session, select

from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Soup,
    SoupTag,
    Tag,
    TagStatus,
)


COMPETITION_COLLECTION_LOCK_ID = 0x43544701


def _lock_competition_collection(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.exec(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            params={"lock_id": COMPETITION_COLLECTION_LOCK_ID},
        )


def lock_competition_collection(db: Session) -> None:
    """Serialize competition edits, collection and settlement in one transaction."""
    _lock_competition_collection(db)


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


def _entry_score(soup: Soup) -> float:
    return float(soup.avg_rating)


def _ensure_entry(
    db: Session,
    competition: Competition,
    soup: Soup,
) -> CompetitionEntry:
    entry = db.exec(
        select(CompetitionEntry).where(
            CompetitionEntry.competition_id == competition.id,
            CompetitionEntry.soup_id == soup.id,
        )
    ).first()
    if entry is None:
        values = {
            "competition_id": competition.id,
            "soup_id": soup.id,
            "author_uid": soup.author_uid,
            "final_score": _entry_score(soup),
        }
        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            db.exec(
                postgresql_insert(CompetitionEntry)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["competition_id", "soup_id"]
                )
            )
        elif dialect == "sqlite":
            db.exec(
                sqlite_insert(CompetitionEntry)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["competition_id", "soup_id"]
                )
            )
        else:
            db.add(CompetitionEntry(**values))
            db.flush()
        entry = db.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition.id,
                CompetitionEntry.soup_id == soup.id,
            )
        ).one()
    return entry


def collect_competition_entries(
    db: Session,
    competition: Competition,
) -> list[CompetitionEntry]:
    """Stage existing matching soups for a newly created competition."""
    if competition.id is None or competition.settled_at is not None:
        return []

    _lock_competition_collection(db)

    tag_ids = competition_tag_ids(competition)
    if not tag_ids:
        return []

    matching_soup_ids = select(SoupTag.soup_id).where(
        SoupTag.tag_id.in_(tag_ids)
    )
    soups = db.exec(
        select(Soup).where(
            Soup.status.in_(["published", "revealed"]),
            Soup.created_at >= competition.start_time,
            Soup.created_at <= competition.end_time,
            Soup.id.in_(matching_soup_ids),
        )
    ).all()
    return [_ensure_entry(db, competition, soup) for soup in soups]


def evaluate_soup_competitions(db: Session, soup: Soup) -> list[CompetitionEntry]:
    """Create or return matching, unsettled competition entries for a soup."""
    if soup.id is None or soup.created_at is None:
        return []

    _lock_competition_collection(db)

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
            Competition.start_time <= soup.created_at,
            Competition.end_time >= soup.created_at,
            Competition.settled_at.is_(None),
        )
    ).all()

    entries: list[CompetitionEntry] = []
    for competition in competitions:
        if not active_tag_ids.intersection(competition_tag_ids(competition)):
            continue
        entries.append(_ensure_entry(db, competition, soup))
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


def refresh_soup_competition_scores(db: Session, soup: Soup) -> None:
    _lock_competition_collection(db)
    entries = db.exec(
        select(CompetitionEntry)
        .join(Competition, Competition.id == CompetitionEntry.competition_id)
        .where(
            CompetitionEntry.soup_id == soup.id,
            Competition.settled_at.is_(None),
        )
    ).all()
    for entry in entries:
        entry.final_score = _entry_score(soup)
    db.flush()


def remove_soup_from_unsettled_competitions(db: Session, soup_id: int) -> int:
    """Remove a deleted soup from competitions whose results are not frozen."""
    _lock_competition_collection(db)
    entries = db.exec(
        select(CompetitionEntry)
        .join(Competition, Competition.id == CompetitionEntry.competition_id)
        .where(
            CompetitionEntry.soup_id == soup_id,
            Competition.settled_at.is_(None),
        )
    ).all()
    for entry in entries:
        db.delete(entry)
    db.flush()
    return len(entries)


def delete_competition_entries(db: Session, competition_id: int) -> int:
    """Delete all entries for a competition under the collection lock."""
    _lock_competition_collection(db)
    entries = db.exec(
        select(CompetitionEntry).where(
            CompetitionEntry.competition_id == competition_id
        )
    ).all()
    for entry in entries:
        db.delete(entry)
    db.flush()
    return len(entries)


def settle_competition(db: Session, competition: Competition) -> dict:
    """Freeze entry ranking so later soup changes cannot rewrite results."""
    _lock_competition_collection(db)
    db.refresh(competition)
    if competition.result_snapshot is not None:
        return competition.result_snapshot

    entries = db.exec(
        select(CompetitionEntry)
        .where(CompetitionEntry.competition_id == competition.id)
    ).all()
    for entry in entries:
        soup = db.get(Soup, entry.soup_id)
        if soup is not None:
            entry.final_score = _entry_score(soup)
    entries.sort(key=lambda entry: (-entry.final_score, entry.created_at, entry.id))
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
