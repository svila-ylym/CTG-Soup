"""Add optional tag groups and a display color to competitions."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import engine as default_engine


@dataclass(frozen=True)
class CompetitionGroupMigrationReport:
    actions: tuple[str, ...]
    applied: bool


def ensure_competition_group_schema(
    engine: Engine = default_engine,
    dry_run: bool = False,
) -> CompetitionGroupMigrationReport:
    inspector = inspect(engine)
    if "competitions" not in inspector.get_table_names():
        return CompetitionGroupMigrationReport(actions=(), applied=False)

    columns = {column["name"] for column in inspector.get_columns("competitions")}
    actions: list[str] = []
    if "optional_tag_ids" not in columns:
        actions.append("ADD competitions.optional_tag_ids")
    if "competition_color" not in columns:
        actions.append("ADD competitions.competition_color")

    if actions and not dry_run:
        with engine.begin() as connection:
            if "optional_tag_ids" not in columns:
                connection.execute(text(
                    "ALTER TABLE competitions ADD COLUMN optional_tag_ids "
                    "JSON NOT NULL DEFAULT '[]'"
                ))
            if "competition_color" not in columns:
                connection.execute(text(
                    "ALTER TABLE competitions ADD COLUMN competition_color "
                    "VARCHAR(7) NOT NULL DEFAULT '#2563EB'"
                ))

    return CompetitionGroupMigrationReport(
        actions=tuple(actions),
        applied=bool(actions) and not dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(ensure_competition_group_schema(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
