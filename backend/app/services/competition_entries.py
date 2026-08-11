from datetime import datetime

from sqlalchemy import or_, text
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


class CompetitionNotEndedError(ValueError):
    pass


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
    return _normalized_tag_ids(competition.required_tag_ids)


def competition_optional_tag_ids(competition: Competition) -> list[int]:
    """Return normalized optional tag IDs in display order."""
    return _normalized_tag_ids(competition.optional_tag_ids)


def _normalized_tag_ids(values) -> list[int]:
    normalized: list[int] = []
    for value in values or []:
        try:
            tag_id = int(value)
        except (TypeError, ValueError):
            continue
        if tag_id > 0 and tag_id not in normalized:
            normalized.append(tag_id)
    return normalized


def _active_soup_tag_ids(db: Session, soup_id: int) -> set[int]:
    return set(db.exec(
        select(Tag.id)
        .join(SoupTag, SoupTag.tag_id == Tag.id)
        .where(
            SoupTag.soup_id == soup_id,
            Tag.status == TagStatus.ACTIVE,
        )
    ).all())


def _active_tag_ids_by_soup(
    db: Session,
    soup_ids: list[int],
) -> dict[int, set[int]]:
    unique_soup_ids = list(dict.fromkeys(soup_ids))
    tag_ids_by_soup = {soup_id: set() for soup_id in unique_soup_ids}
    if not unique_soup_ids:
        return tag_ids_by_soup
    rows = db.exec(
        select(SoupTag.soup_id, SoupTag.tag_id)
        .join(Tag, Tag.id == SoupTag.tag_id)
        .where(
            SoupTag.soup_id.in_(unique_soup_ids),
            Tag.status == TagStatus.ACTIVE,
        )
    ).all()
    for soup_id, tag_id in rows:
        tag_ids_by_soup[soup_id].add(tag_id)
    return tag_ids_by_soup


def _matches_competition(
    competition: Competition,
    soup: Soup,
    active_tag_ids: set[int],
) -> bool:
    required_tag_ids = set(competition_tag_ids(competition))
    return bool(required_tag_ids) and all((
        soup.status in {"published", "revealed"},
        competition.start_time <= soup.created_at <= competition.end_time,
        required_tag_ids.issubset(active_tag_ids),
    ))


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

    required_tag_ids = competition_tag_ids(competition)
    if not required_tag_ids:
        return []

    candidate_soup_ids = select(SoupTag.soup_id).where(
        SoupTag.tag_id == required_tag_ids[0]
    )
    soups = db.exec(
        select(Soup).where(
            Soup.status.in_(["published", "revealed"]),
            Soup.created_at >= competition.start_time,
            Soup.created_at <= competition.end_time,
            Soup.id.in_(candidate_soup_ids),
        )
    ).all()
    active_tag_ids_by_soup = _active_tag_ids_by_soup(
        db,
        [soup.id for soup in soups],
    )
    return [
        _ensure_entry(db, competition, soup)
        for soup in soups
        if _matches_competition(
            competition,
            soup,
            active_tag_ids_by_soup[soup.id],
        )
    ]


def evaluate_soup_competitions(db: Session, soup: Soup) -> list[CompetitionEntry]:
    """Reconcile a soup against relevant unsettled competitions."""
    if soup.id is None or soup.created_at is None:
        return []

    _lock_competition_collection(db)
    active_tag_ids = _active_soup_tag_ids(db, soup.id)

    existing = {
        entry.competition_id: entry
        for entry in db.exec(
            select(CompetitionEntry)
            .join(Competition, Competition.id == CompetitionEntry.competition_id)
            .where(
                CompetitionEntry.soup_id == soup.id,
                Competition.settled_at.is_(None),
            )
        ).all()
    }
    relevant_window = (
        (Competition.start_time <= soup.created_at)
        & (Competition.end_time >= soup.created_at)
    )
    if existing:
        relevant_window = or_(relevant_window, Competition.id.in_(existing))
    competitions = db.exec(
        select(Competition).where(
            Competition.settled_at.is_(None),
            relevant_window,
        )
    ).all()

    entries: list[CompetitionEntry] = []
    for competition in competitions:
        entry = existing.get(competition.id)
        if not _matches_competition(competition, soup, active_tag_ids):
            if entry is not None:
                db.delete(entry)
            continue
        entry = entry or _ensure_entry(db, competition, soup)
        entry.final_score = _entry_score(soup)
        entries.append(entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


def reconcile_soup_competitions(db: Session, soup: Soup) -> list[CompetitionEntry]:
    return evaluate_soup_competitions(db, soup)


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


def rebuild_competition_entries(
    db: Session,
    competition: Competition,
) -> list[CompetitionEntry]:
    """Rebuild one unsettled competition inside the caller's transaction."""
    if competition.settled_at is not None:
        return []
    _lock_competition_collection(db)
    delete_competition_entries(db, competition.id)
    db.flush()
    return collect_competition_entries(db, competition)


def rebuild_unsettled_competitions_for_tags(
    db: Session,
    tag_ids: set[int],
) -> int:
    """Rebuild live competitions affected by a taxonomy status or merge change."""
    normalized_tag_ids = {int(tag_id) for tag_id in tag_ids if int(tag_id) > 0}
    if not normalized_tag_ids:
        return 0
    _lock_competition_collection(db)
    competitions = db.exec(
        select(Competition).where(Competition.settled_at.is_(None))
    ).all()
    affected = [
        competition
        for competition in competitions
        if normalized_tag_ids.intersection(
            competition_tag_ids(competition)
            + competition_optional_tag_ids(competition)
        )
    ]
    for competition in affected:
        rebuild_competition_entries(db, competition)
    return len(affected)


def _competition_ranking_rows(
    db: Session,
    competition: Competition,
    persist_scores: bool = False,
):
    rows = db.exec(
        select(CompetitionEntry, Soup)
        .join(Soup, Soup.id == CompetitionEntry.soup_id)
        .where(CompetitionEntry.competition_id == competition.id)
    ).all()
    ranked_rows = []
    for entry, soup in rows:
        score = _entry_score(soup)
        if persist_scores:
            entry.final_score = score
        ranked_rows.append((entry, soup, score))
    ranked_rows.sort(key=lambda item: (-item[2], item[1].created_at, item[1].id))
    return ranked_rows


def _ranking_payload(rows, top_n: int) -> list[dict]:
    return [
        {
            "entry_id": entry.id,
            "soup_id": soup.id,
            "soup_title": soup.title,
            "author_uid": entry.author_uid,
            "final_score": score,
            "rank": rank,
            "soup_created_at": soup.created_at.isoformat(),
        }
        for rank, (entry, soup, score) in enumerate(rows[:top_n], start=1)
    ]


def _build_rankings(
    db: Session,
    competition: Competition,
    persist_scores: bool = False,
) -> dict:
    rows = _competition_ranking_rows(db, competition, persist_scores=persist_scores)
    total = _ranking_payload(rows, competition.top_n)
    optional_tag_ids = competition_optional_tag_ids(competition)
    if not optional_tag_ids:
        return {"total": total, "groups": []}

    tag_names = {
        tag.id: tag.name
        for tag in db.exec(select(Tag).where(Tag.id.in_(optional_tag_ids))).all()
    }
    soup_ids_by_tag: dict[int, set[int]] = {
        tag_id: set() for tag_id in optional_tag_ids
    }
    soup_ids = [soup.id for _entry, soup, _score in rows]
    if soup_ids:
        relations = db.exec(
            select(SoupTag.soup_id, SoupTag.tag_id).where(
                SoupTag.soup_id.in_(soup_ids),
                SoupTag.tag_id.in_(optional_tag_ids),
            )
        ).all()
        for soup_id, tag_id in relations:
            soup_ids_by_tag[tag_id].add(soup_id)

    groups = []
    for tag_id in optional_tag_ids:
        group_rows = [
            row for row in rows if row[1].id in soup_ids_by_tag[tag_id]
        ]
        groups.append({
            "tag_id": tag_id,
            "tag_name": tag_names.get(tag_id, f"标签 #{tag_id}"),
            "entries": _ranking_payload(group_rows, competition.top_n),
        })
    return {"total": total, "groups": groups}


def competition_rankings(db: Session, competition: Competition) -> dict:
    snapshot = competition.result_snapshot
    if competition.settled_at is not None and snapshot is not None:
        if "total" in snapshot:
            rankings = {
                "total": snapshot.get("total", []),
                "groups": snapshot.get("groups", []),
            }
        else:
            rankings = {"total": snapshot.get("entries", []), "groups": []}
        entries = [*rankings["total"]]
        for group in rankings["groups"]:
            entries.extend(group.get("entries", []))
        missing_ids = {
            item.get("soup_id") for item in entries
            if not item.get("soup_title") and item.get("soup_id")
        }
        titles = {
            soup.id: soup.title
            for soup in db.exec(select(Soup).where(Soup.id.in_(missing_ids))).all()
        } if missing_ids else {}
        for item in entries:
            item.setdefault("soup_title", titles.get(item.get("soup_id"), "已删除作品"))
        return rankings
    return _build_rankings(db, competition)


def competition_colors_for_soups(
    db: Session,
    soup_ids: list[int],
) -> dict[int, list[str]]:
    unique_soup_ids = list(dict.fromkeys(soup_ids))
    colors_by_soup = {soup_id: [] for soup_id in unique_soup_ids}
    if not unique_soup_ids:
        return colors_by_soup
    rows = db.exec(
        select(
            CompetitionEntry.soup_id,
            Competition.competition_color,
        )
        .join(Competition, Competition.id == CompetitionEntry.competition_id)
        .where(CompetitionEntry.soup_id.in_(unique_soup_ids))
        .order_by(Competition.start_time, Competition.id)
    ).all()
    for soup_id, color in rows:
        normalized = str(color or "#2563EB").upper()
        if normalized not in colors_by_soup[soup_id]:
            colors_by_soup[soup_id].append(normalized)
    return colors_by_soup


def settle_competition(db: Session, competition: Competition) -> dict:
    """Freeze entry ranking so later soup changes cannot rewrite results."""
    _lock_competition_collection(db)
    db.refresh(competition)
    if competition.result_snapshot is not None:
        return competition.result_snapshot
    if datetime.utcnow() < competition.end_time:
        raise CompetitionNotEndedError("比赛尚未结束，不能结算")

    entries = db.exec(select(CompetitionEntry).where(
        CompetitionEntry.competition_id == competition.id
    )).all()
    rankings = _build_rankings(db, competition, persist_scores=True)
    total_ranks = {
        item["entry_id"]: item["rank"] for item in rankings["total"]
    }
    for entry in entries:
        entry.rank = total_ranks.get(entry.id)
    now = datetime.utcnow()
    competition.result_snapshot = {
        "entries": rankings["total"],
        "total": rankings["total"],
        "groups": rankings["groups"],
        "settled_at": now.isoformat(),
    }
    competition.status = CompetitionStatus.COMPLETED
    competition.settled_at = now
    competition.updated_at = now
    db.commit()
    db.refresh(competition)
    return competition.result_snapshot
