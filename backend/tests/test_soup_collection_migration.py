from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

from app.migrations.soup_collections import ensure_soup_collection_schema


def test_collection_migration_is_dry_run_capable_and_repeatable():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (uid INTEGER PRIMARY KEY)"))
        connection.execute(text(
            "CREATE TABLE soups (id INTEGER PRIMARY KEY, author_uid INTEGER NOT NULL)"
        ))
        connection.execute(text("INSERT INTO users (uid) VALUES (1)"))
        connection.execute(text("INSERT INTO soups (id, author_uid) VALUES (10, 1)"))

    preview = ensure_soup_collection_schema(engine, dry_run=True)
    assert preview.actions == (
        "CREATE soup_collections",
        "ADD soups.collection_id",
        "CREATE INDEX ix_soups_collection_id",
    )
    assert preview.applied is False

    applied = ensure_soup_collection_schema(engine)
    repeated = ensure_soup_collection_schema(engine)
    inspector = inspect(engine)

    assert applied.applied is True
    assert repeated.actions == ()
    assert "soup_collections" in inspector.get_table_names()
    assert "collection_id" in {
        column["name"] for column in inspector.get_columns("soups")
    }
    assert "ix_soups_collection_id" in {
        index["name"] for index in inspector.get_indexes("soups")
    }
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT collection_id FROM soups WHERE id = 10")
        ).scalar_one() is None
