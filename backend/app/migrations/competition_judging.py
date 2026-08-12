"""Add private organizer scoring fields to competitions and entries."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db import engine as default_engine


@dataclass(frozen=True)
class CompetitionJudgingMigrationReport:
    actions: tuple[str, ...]
    applied: bool


def _postgres_enum_has_independent(engine: Engine) -> bool:
    if engine.dialect.name != "postgresql":
        return True
    with engine.connect() as connection:
        return bool(connection.execute(text(
            "SELECT 1 FROM pg_type type "
            "JOIN pg_enum enum ON enum.enumtypid = type.oid "
            "WHERE type.typname = 'competitionscoretype' "
            "AND enum.enumlabel = 'INDEPENDENT'"
        )).first())


def ensure_competition_judging_schema(
    engine: Engine = default_engine,
    dry_run: bool = False,
) -> CompetitionJudgingMigrationReport:
    """Add independent-scoring storage without rewriting existing rows."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if not {"competitions", "competition_entries"} <= table_names:
        return CompetitionJudgingMigrationReport(actions=(), applied=False)

    competition_columns = {
        column["name"] for column in inspector.get_columns("competitions")
    }
    entry_columns = {
        column["name"] for column in inspector.get_columns("competition_entries")
    }
    add_enum_value = not _postgres_enum_has_independent(engine)
    actions = tuple(
        action
        for action, needed in (
            ("ADD competitionscoretype.INDEPENDENT", add_enum_value),
            ("ADD competitions.scoring_at", "scoring_at" not in competition_columns),
            ("ADD competition_entries.judge_score", "judge_score" not in entry_columns),
            ("ADD competition_entries.judged_by_uid", "judged_by_uid" not in entry_columns),
            ("ADD competition_entries.judged_at", "judged_at" not in entry_columns),
        )
        if needed
    )
    if dry_run or not actions:
        return CompetitionJudgingMigrationReport(actions=actions, applied=False)

    if add_enum_value:
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TYPE competitionscoretype "
                "ADD VALUE IF NOT EXISTS 'INDEPENDENT'"
            ))

    with engine.begin() as connection:
        if "scoring_at" not in competition_columns:
            connection.execute(text(
                "ALTER TABLE competitions ADD COLUMN scoring_at TIMESTAMP NULL"
            ))
        if "judge_score" not in entry_columns:
            connection.execute(text(
                "ALTER TABLE competition_entries ADD COLUMN judge_score FLOAT NULL"
            ))
        if "judged_by_uid" not in entry_columns:
            foreign_key = (
                " REFERENCES users(uid) ON DELETE SET NULL"
                if engine.dialect.name == "postgresql"
                else ""
            )
            connection.execute(text(
                "ALTER TABLE competition_entries ADD COLUMN "
                f"judged_by_uid INTEGER NULL{foreign_key}"
            ))
        if "judged_at" not in entry_columns:
            connection.execute(text(
                "ALTER TABLE competition_entries ADD COLUMN judged_at TIMESTAMP NULL"
            ))

    return CompetitionJudgingMigrationReport(actions=actions, applied=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(ensure_competition_judging_schema(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
