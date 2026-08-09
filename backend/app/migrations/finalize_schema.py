"""Finalize legacy schema names and interaction uniqueness constraints."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import engine as default_engine


@dataclass(frozen=True)
class FinalizeSchemaReport:
    actions: tuple[str, ...]
    duplicate_rows: int
    applied: bool


_UNIQUE_CONSTRAINTS = {
    "ratings": ("uq_ratings_user_soup", ("user_uid", "soup_id")),
    "likes": ("uq_likes_user_target", ("user_uid", "target_type", "target_id")),
    "favorites": (
        "uq_favorites_user_target",
        ("user_uid", "target_type", "target_id"),
    ),
    "follows": ("uq_follows_pair", ("follower_uid", "followed_uid")),
    "blacklists": ("uq_blacklists_pair", ("blocker_uid", "blocked_uid")),
    "competition_entries": (
        "uq_competition_entries_pair",
        ("competition_id", "soup_id"),
    ),
}


def _columns(engine: Engine, table: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table)}


def _has_unique_key(engine: Engine, table: str, columns: tuple[str, ...]) -> bool:
    inspector = inspect(engine)
    expected = set(columns)
    if any(
        set(constraint.get("column_names") or ()) == expected
        for constraint in inspector.get_unique_constraints(table)
    ):
        return True
    return any(
        index.get("unique")
        and set(index.get("column_names") or ()) == expected
        for index in inspector.get_indexes(table)
    )


def _duplicate_count(connection, table: str, columns: tuple[str, ...]) -> int:
    grouped_columns = ", ".join(columns)
    statement = text(
        f"SELECT COALESCE(SUM(group_count - 1), 0) FROM ("
        f"SELECT COUNT(*) AS group_count FROM {table} "
        f"GROUP BY {grouped_columns} HAVING COUNT(*) > 1"
        ") AS duplicate_groups"
    )
    return int(connection.execute(statement).scalar_one())


def _deduplicate(connection, table: str, columns: tuple[str, ...], has_updated_at: bool) -> None:
    grouped_columns = ", ".join(columns)
    if has_updated_at:
        order_by = "CASE WHEN updated_at IS NULL THEN 1 ELSE 0 END, updated_at DESC, id DESC"
    else:
        order_by = "id DESC"
    connection.execute(
        text(
            f"DELETE FROM {table} WHERE id IN ("
            "SELECT id FROM ("
            f"SELECT id, ROW_NUMBER() OVER (PARTITION BY {grouped_columns} "
            f"ORDER BY {order_by}) AS duplicate_rank FROM {table}"
            ") AS ranked_rows WHERE duplicate_rank > 1"
            ")"
        )
    )


def _add_unique_key(
    connection,
    dialect: str,
    table: str,
    name: str,
    columns: tuple[str, ...],
) -> None:
    joined_columns = ", ".join(columns)
    if dialect == "sqlite":
        connection.execute(
            text(f"CREATE UNIQUE INDEX {name} ON {table} ({joined_columns})")
        )
    else:
        connection.execute(
            text(
                f"ALTER TABLE {table} ADD CONSTRAINT {name} "
                f"UNIQUE ({joined_columns})"
            )
        )


def finalize_schema(
    engine: Engine = default_engine,
    dry_run: bool = False,
) -> FinalizeSchemaReport:
    """Upgrade historical tables without requiring a migration framework."""
    actions: list[str] = []
    duplicate_rows = 0
    table_names = set(inspect(engine).get_table_names())

    if "competitions" in table_names:
        competition_columns = _columns(engine, "competitions")
        if "required_tags" in competition_columns and "required_tag_ids" not in competition_columns:
            actions.append("RENAME competitions.required_tags TO required_tag_ids")

    pending_constraints: list[tuple[str, str, tuple[str, ...], int, bool]] = []
    with engine.connect() as connection:
        for table, (name, columns) in _UNIQUE_CONSTRAINTS.items():
            if table not in table_names or not set(columns) <= _columns(engine, table):
                continue
            if _has_unique_key(engine, table, columns):
                continue
            duplicates = _duplicate_count(connection, table, columns)
            duplicate_rows += duplicates
            if duplicates:
                actions.append(f"DELETE {duplicates} duplicate row(s) FROM {table}")
            actions.append(f"ADD CONSTRAINT {name} ON {table}")
            pending_constraints.append(
                (table, name, columns, duplicates, "updated_at" in _columns(engine, table))
            )

    if not dry_run and actions:
        with engine.begin() as connection:
            if "competitions" in table_names:
                competition_columns = _columns(engine, "competitions")
                if "required_tags" in competition_columns and "required_tag_ids" not in competition_columns:
                    connection.execute(
                        text(
                            "ALTER TABLE competitions RENAME COLUMN "
                            "required_tags TO required_tag_ids"
                        )
                    )
            for table, name, columns, duplicates, has_updated_at in pending_constraints:
                if duplicates:
                    _deduplicate(connection, table, columns, has_updated_at)
                _add_unique_key(connection, engine.dialect.name, table, name, columns)

    return FinalizeSchemaReport(
        actions=tuple(actions),
        duplicate_rows=duplicate_rows,
        applied=bool(actions) and not dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(finalize_schema(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
