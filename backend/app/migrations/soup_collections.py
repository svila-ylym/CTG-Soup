"""Idempotent schema migration for author-owned soup collections."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import engine as default_engine
from app.models.database import SoupCollection


@dataclass(frozen=True)
class SoupCollectionMigrationReport:
    actions: tuple[str, ...]
    applied: bool


def ensure_soup_collection_schema(
    engine: Engine = default_engine,
    dry_run: bool = False,
) -> SoupCollectionMigrationReport:
    """Create collection storage and the nullable soup association."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not {"users", "soups"} <= table_names:
        return SoupCollectionMigrationReport(actions=(), applied=False)

    create_table = "soup_collections" not in table_names
    soup_columns = {column["name"] for column in inspector.get_columns("soups")}
    add_column = "collection_id" not in soup_columns
    soup_indexes = {index["name"] for index in inspector.get_indexes("soups")}
    create_index = "ix_soups_collection_id" not in soup_indexes

    actions = tuple(
        action
        for action, needed in (
            ("CREATE soup_collections", create_table),
            ("ADD soups.collection_id", add_column),
            ("CREATE INDEX ix_soups_collection_id", create_index),
        )
        if needed
    )
    if dry_run or not actions:
        return SoupCollectionMigrationReport(actions=actions, applied=False)

    with engine.begin() as connection:
        if create_table:
            SoupCollection.__table__.create(connection)
        if add_column:
            connection.execute(
                text(
                    "ALTER TABLE soups ADD COLUMN collection_id INTEGER NULL "
                    "REFERENCES soup_collections(id) ON DELETE SET NULL"
                )
            )
        if create_index:
            connection.execute(
                text(
                    "CREATE INDEX ix_soups_collection_id "
                    "ON soups (collection_id)"
                )
            )
    return SoupCollectionMigrationReport(actions=actions, applied=True)
