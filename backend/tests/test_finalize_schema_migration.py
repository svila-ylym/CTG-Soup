from sqlalchemy import inspect, text
from sqlmodel import create_engine

from app.migrations.finalize_schema import finalize_schema


def _legacy_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE competitions ("
                "id INTEGER PRIMARY KEY, "
                "required_tags JSON NOT NULL DEFAULT '[]'"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO competitions (id, required_tags) "
                "VALUES (1, '[2, 3]')"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE ratings ("
                "id INTEGER PRIMARY KEY, user_uid INTEGER NOT NULL, "
                "soup_id INTEGER NOT NULL, score FLOAT NOT NULL, "
                "updated_at DATETIME"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO ratings "
                "(id, user_uid, soup_id, score, updated_at) VALUES "
                "(1, 7, 9, 3.0, '2026-01-01 00:00:00'), "
                "(2, 7, 9, 4.5, '2026-02-01 00:00:00')"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE follows ("
                "id INTEGER PRIMARY KEY, follower_uid INTEGER NOT NULL, "
                "followed_uid INTEGER NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO follows (id, follower_uid, followed_uid) VALUES "
                "(1, 7, 8), (2, 7, 8)"
            )
        )
    return engine


def _unique_signatures(engine, table):
    inspector = inspect(engine)
    constraints = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(table)
    }
    indexes = {
        tuple(index["column_names"])
        for index in inspector.get_indexes(table)
        if index.get("unique")
    }
    return constraints | indexes


def test_finalize_schema_dry_run_reports_without_mutating():
    engine = _legacy_engine()

    report = finalize_schema(engine, dry_run=True)

    assert report.applied is False
    assert report.duplicate_rows == 2
    assert any("required_tags" in action for action in report.actions)
    assert any("uq_ratings_user_soup" in action for action in report.actions)
    assert {column["name"] for column in inspect(engine).get_columns("competitions")} == {
        "id",
        "required_tags",
    }
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM ratings")).scalar_one() == 2


def test_finalize_schema_preserves_latest_rows_and_is_repeatable():
    engine = _legacy_engine()

    first = finalize_schema(engine)
    second = finalize_schema(engine)

    assert first.applied is True
    assert first.duplicate_rows == 2
    assert second.actions == ()
    assert second.duplicate_rows == 0
    competition_columns = {
        column["name"] for column in inspect(engine).get_columns("competitions")
    }
    assert "required_tag_ids" in competition_columns
    assert "required_tags" not in competition_columns
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT required_tag_ids FROM competitions WHERE id = 1")
        ).scalar_one() == "[2, 3]"
        rating = connection.execute(
            text("SELECT id, score FROM ratings WHERE user_uid = 7 AND soup_id = 9")
        ).one()
        assert rating == (2, 4.5)
        assert connection.execute(text("SELECT COUNT(*) FROM follows")).scalar_one() == 1
    assert ("user_uid", "soup_id") in _unique_signatures(engine, "ratings")
    assert ("follower_uid", "followed_uid") in _unique_signatures(engine, "follows")


def test_finalize_schema_adds_constraints_to_empty_interaction_tables():
    engine = create_engine("sqlite://")
    tables = {
        "likes": ("user_uid", "target_type", "target_id"),
        "favorites": ("user_uid", "target_type", "target_id"),
        "blacklists": ("blocker_uid", "blocked_uid"),
        "competition_entries": ("competition_id", "soup_id"),
    }
    with engine.begin() as connection:
        for table, columns in tables.items():
            definitions = ", ".join(f"{column} INTEGER NOT NULL" for column in columns)
            connection.execute(
                text(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, {definitions})")
            )

    finalize_schema(engine)

    for table, columns in tables.items():
        assert columns in _unique_signatures(engine, table)
