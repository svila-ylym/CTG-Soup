from sqlalchemy import Text, inspect, text
from sqlmodel import create_engine

from app.migrations.social_platform import upgrade_social_platform


def _legacy_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE soups ("
                "id INTEGER PRIMARY KEY, "
                "tags JSON NOT NULL DEFAULT '[]'"
                ")"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE users ("
                "uid INTEGER PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (uid, username, role) "
                "VALUES (1, 'SkyUnreal', 'user')"
            )
        )
    return engine


def test_social_upgrade_dry_run_never_executes_ddl():
    engine = _legacy_engine()

    report = upgrade_social_platform(engine, dry_run=True, phase="foundation")

    assert report.applied is False
    assert report.actions
    assert report.counts["actions"] == len(report.actions)
    assert {column["name"] for column in inspect(engine).get_columns("soups")} == {
        "id",
        "tags",
    }


def test_social_upgrade_foundation_is_repeatable():
    engine = _legacy_engine()

    first = upgrade_social_platform(engine, phase="foundation")
    second = upgrade_social_platform(engine, phase="foundation")

    assert first.applied is True
    assert second.applied is False
    assert second.actions == ()
    assert second.counts == {"promoted_root_users": 0, "actions": 0}


def test_foundation_converts_legacy_people_counts_to_text_without_losing_values():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE soups ("
                "id INTEGER PRIMARY KEY, "
                "tags JSON NOT NULL DEFAULT '[]', "
                "main_player_count INTEGER NOT NULL DEFAULT 1, "
                "secondary_player_count INTEGER NOT NULL DEFAULT 0"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO soups "
                "(id, main_player_count, secondary_player_count) "
                "VALUES (1, 2, 0)"
            )
        )

    preview = upgrade_social_platform(engine, dry_run=True, phase="foundation")

    assert preview.applied is False
    assert any("people count columns to TEXT" in action for action in preview.actions)
    assert all(
        not isinstance(column["type"], Text)
        for column in inspect(engine).get_columns("soups")
        if column["name"] in {"main_player_count", "secondary_player_count"}
    )

    applied = upgrade_social_platform(engine, phase="foundation")

    columns = {
        column["name"]: column["type"]
        for column in inspect(engine).get_columns("soups")
    }
    assert applied.applied is True
    assert isinstance(columns["main_player_count"], Text)
    assert isinstance(columns["secondary_player_count"], Text)
    with engine.connect() as connection:
        values = connection.execute(
            text(
                "SELECT main_player_count, secondary_player_count "
                "FROM soups WHERE id = 1"
            )
        ).one()
    assert values == ("2", "0")


def test_foundation_promotes_only_exact_skyunreal_username():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "uid INTEGER PRIMARY KEY, username TEXT NOT NULL, role TEXT NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO users (uid, username, role) VALUES "
                "(1, 'SkyUnreal', 'user'), "
                "(2, 'skyunreal', 'user'), "
                "(3, 'OtherUser', 'admin')"
            )
        )

    preview = upgrade_social_platform(engine, dry_run=True, phase="foundation")
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT role FROM users WHERE username = 'SkyUnreal'")
        ).scalar_one() == "user"

    applied = upgrade_social_platform(engine, phase="foundation")
    with engine.connect() as connection:
        roles = dict(
            connection.execute(
                text("SELECT username, role FROM users ORDER BY uid")
            ).all()
        )

    assert preview.counts["promoted_root_users"] == 1
    assert applied.counts["promoted_root_users"] == 1
    assert roles == {
        "SkyUnreal": "root",
        "skyunreal": "user",
        "OtherUser": "admin",
    }
    assert upgrade_social_platform(engine, phase="foundation").counts[
        "promoted_root_users"
    ] == 0
