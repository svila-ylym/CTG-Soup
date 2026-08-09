"""Schema and data migration for normalized soup taxonomy metadata."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, select

from app.db import engine as default_engine
from app.models.database import Soup, SoupTag, Tag, TagKind, TagStatus
from app.services.tag_rules import normalize_tag_name


@dataclass(frozen=True)
class SchemaMigrationReport:
    actions: tuple[str, ...]
    applied: bool


@dataclass(frozen=True)
class MigrationReport:
    scanned_soups: int
    created_tags: int
    created_links: int
    skipped_tags: int
    dry_run: bool


def _existing_columns(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def ensure_soup_metadata_schema(
    engine: Engine = default_engine,
    dry_run: bool = False,
) -> SchemaMigrationReport:
    """Create taxonomy tables and add soup metadata columns idempotently."""
    actions: list[str] = []
    inspector = inspect(engine)
    if "soups" in inspector.get_table_names():
        columns = _existing_columns(engine, "soups")
        additions = {
            "genre": "VARCHAR(20) NOT NULL DEFAULT '未分类'",
            "soup_color": "VARCHAR(20) NOT NULL DEFAULT '未分类'",
            "main_player_count": "TEXT NOT NULL DEFAULT ''",
            "secondary_player_count": "TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in additions.items():
            if name not in columns:
                actions.append(f"ALTER TABLE soups ADD COLUMN {name}")
                if not dry_run:
                    with engine.begin() as connection:
                        connection.execute(text(f"ALTER TABLE soups ADD COLUMN {name} {definition}"))

    expected_tables = {"tags", "tag_aliases", "soup_tags"}
    missing_tables = expected_tables - set(inspector.get_table_names())
    if missing_tables:
        actions.extend(f"CREATE TABLE {name}" for name in sorted(missing_tables))
        if not dry_run:
            SQLModel.metadata.create_all(bind=engine)
    return SchemaMigrationReport(actions=tuple(actions), applied=bool(actions) and not dry_run)


def _legacy_names(soup: Soup) -> list[str]:
    values: Any = soup.tags or []
    return values if isinstance(values, list) else []


def _decoded_legacy_names(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    return value if isinstance(value, list) else []


def _preview_data_migration(session: Session) -> MigrationReport:
    table_names = set(inspect(session.get_bind()).get_table_names())
    if "soups" not in table_names:
        return MigrationReport(0, 0, 0, 0, True)

    soup_rows = session.execute(text("SELECT id, tags FROM soups")).all()
    existing_tags = (
        {tag.slug: tag.id for tag in session.exec(select(Tag)).all()}
        if "tags" in table_names
        else {}
    )
    existing_links = (
        {
            (link.soup_id, link.tag_id)
            for link in session.exec(select(SoupTag)).all()
        }
        if "soup_tags" in table_names
        else set()
    )
    pending_slugs: set[str] = set()
    pending_links: set[tuple[int, str]] = set()
    skipped = 0
    for soup_id, raw_tags in soup_rows:
        for raw_name in _decoded_legacy_names(raw_tags):
            try:
                _, slug = normalize_tag_name(raw_name)
            except ValueError:
                skipped += 1
                continue
            if slug not in existing_tags:
                pending_slugs.add(slug)
            tag_id = existing_tags.get(slug)
            if tag_id is None or (soup_id, tag_id) not in existing_links:
                pending_links.add((soup_id, slug))
    return MigrationReport(
        scanned_soups=len(soup_rows),
        created_tags=len(pending_slugs),
        created_links=len(pending_links),
        skipped_tags=skipped,
        dry_run=True,
    )


def migrate_soup_metadata(
    session: Session,
    dry_run: bool = False,
) -> MigrationReport:
    """Import legacy ``Soup.tags`` values and backfill explicit metadata."""
    if dry_run:
        return _preview_data_migration(session)

    soups = session.exec(select(Soup)).all()
    existing_tags = {tag.slug: tag for tag in session.exec(select(Tag)).all()}
    existing_links = {
        (link.soup_id, link.tag_id)
        for link in session.exec(select(SoupTag)).all()
    }
    pending_tags: dict[str, Tag] = {}
    pending_links: list[tuple[int, str]] = []
    pending_link_keys: set[tuple[int, str]] = set()
    skipped = 0

    for soup in soups:
        for raw_name in _legacy_names(soup):
            try:
                name, slug = normalize_tag_name(raw_name)
            except ValueError:
                skipped += 1
                continue
            tag = existing_tags.get(slug) or pending_tags.get(slug)
            if tag is None:
                tag = Tag(name=name, slug=slug, kind=TagKind.CUSTOM, status=TagStatus.ACTIVE)
                pending_tags[slug] = tag
            link_key = (soup.id, slug)
            if link_key not in pending_link_keys:
                pending_links.append(link_key)
                pending_link_keys.add(link_key)

    new_links = [
        (soup_id, slug)
        for soup_id, slug in pending_links
        if not (
            soup_id,
            (existing_tags.get(slug) or pending_tags[slug]).id,
        ) in existing_links
    ]
    created_tags = len(pending_tags)
    created_links = len(new_links)

    for soup in soups:
        if soup.genre is None:
            soup.genre = "未分类"
        if soup.soup_color is None:
            soup.soup_color = "未分类"
        if soup.main_player_count is None:
            soup.main_player_count = ""
        if soup.secondary_player_count is None:
            soup.secondary_player_count = ""

    for tag in pending_tags.values():
        session.add(tag)
    session.flush()

    for soup_id, slug in pending_links:
        tag = existing_tags.get(slug) or pending_tags[slug]
        if (soup_id, tag.id) not in existing_links:
            session.add(SoupTag(soup_id=soup_id, tag_id=tag.id))
            existing_links.add((soup_id, tag.id))

    session.flush()
    for tag in session.exec(select(Tag)).all():
        tag.usage_count = len(session.exec(select(SoupTag).where(SoupTag.tag_id == tag.id)).all())
    session.commit()
    return MigrationReport(len(soups), created_tags, created_links, skipped, False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    schema_report = ensure_soup_metadata_schema(dry_run=args.dry_run)
    with Session(default_engine) as session:
        report = migrate_soup_metadata(session, dry_run=args.dry_run)
    print({"schema": schema_report, "data": report})


if __name__ == "__main__":
    main()
