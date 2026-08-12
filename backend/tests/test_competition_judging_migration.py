from sqlalchemy import inspect, text
from sqlmodel import create_engine

from app.migrations.competition_judging import ensure_competition_judging_schema


def _legacy_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE competitions ("
            "id INTEGER PRIMARY KEY, score_type VARCHAR(20) NOT NULL"
            ")"
        ))
        connection.execute(text(
            "CREATE TABLE competition_entries ("
            "id INTEGER PRIMARY KEY, competition_id INTEGER NOT NULL"
            ")"
        ))
    return engine


def test_competition_judging_migration_is_dry_run_capable_and_repeatable():
    engine = _legacy_engine()

    preview = ensure_competition_judging_schema(engine, dry_run=True)

    assert preview.actions == (
        "ADD competitions.scoring_at",
        "ADD competition_entries.judge_score",
        "ADD competition_entries.judged_by_uid",
        "ADD competition_entries.judged_at",
    )
    assert preview.applied is False
    assert "scoring_at" not in {
        column["name"] for column in inspect(engine).get_columns("competitions")
    }

    applied = ensure_competition_judging_schema(engine)
    repeated = ensure_competition_judging_schema(engine)

    assert applied.applied is True
    assert repeated.actions == ()
    assert {
        "judge_score",
        "judged_by_uid",
        "judged_at",
    } <= {
        column["name"]
        for column in inspect(engine).get_columns("competition_entries")
    }
