from sqlalchemy import inspect, text
from sqlmodel import create_engine

from app.migrations.competition_groups import ensure_competition_group_schema


def _legacy_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE competitions ("
            "id INTEGER PRIMARY KEY, required_tag_ids JSON NOT NULL DEFAULT '[]'"
            ")"
        ))
        connection.execute(text(
            "INSERT INTO competitions (id, required_tag_ids) VALUES (1, '[2]')"
        ))
    return engine


def test_competition_group_migration_is_dry_run_capable_and_repeatable():
    engine = _legacy_engine()

    preview = ensure_competition_group_schema(engine, dry_run=True)

    assert preview.applied is False
    assert preview.actions == (
        "ADD competitions.optional_tag_ids",
        "ADD competitions.competition_color",
    )
    assert {column["name"] for column in inspect(engine).get_columns("competitions")} == {
        "id",
        "required_tag_ids",
    }

    applied = ensure_competition_group_schema(engine)
    repeated = ensure_competition_group_schema(engine)

    assert applied.applied is True
    assert repeated.actions == ()
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT optional_tag_ids, competition_color FROM competitions WHERE id = 1"
        )).one()
    assert row == ("[]", "#2563EB")
