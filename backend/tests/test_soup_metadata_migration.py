from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.migrations.soup_metadata import (
    ensure_soup_metadata_schema,
    migrate_soup_metadata,
)
from app.models.database import Soup, SoupTag, Tag, User, UserRole, UserStatus


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _legacy_session():
    engine = _engine()
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    user = User(
        username="migration-author",
        nickname="迁移作者",
        email="migration@example.com",
        hashed_password="not-used",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    session.add(
        Soup(
            author_uid=user.uid,
            title="旧作品",
            puzzle="旧谜面",
            solution="旧汤底",
            tags=[" 悬疑 ", "悬疑", "Story   TAG", "危险<script>"],
        )
    )
    session.commit()
    return session


def test_schema_migration_dry_run_is_non_mutating_and_apply_is_repeatable():
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE soups ("
                "id INTEGER PRIMARY KEY, "
                "tags JSON NOT NULL DEFAULT '[]'"
                ")"
            )
        )

    preview = ensure_soup_metadata_schema(engine, dry_run=True)

    assert preview.applied is False
    assert preview.actions
    assert {column["name"] for column in inspect(engine).get_columns("soups")} == {
        "id",
        "tags",
    }
    assert "tags" not in inspect(engine).get_table_names()

    applied = ensure_soup_metadata_schema(engine)

    assert applied.applied is True
    soup_columns = {column["name"] for column in inspect(engine).get_columns("soups")}
    assert {
        "genre",
        "soup_color",
        "main_player_count",
        "secondary_player_count",
    } <= soup_columns
    assert {"tags", "tag_aliases", "soup_tags"} <= set(
        inspect(engine).get_table_names()
    )
    assert ensure_soup_metadata_schema(engine).actions == ()


def test_data_dry_run_can_preview_a_database_before_schema_upgrade():
    engine = _engine()
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
                "INSERT INTO soups (id, tags) VALUES "
                "(1, '[\"悬疑\", \" Story TAG \", \"危险<script>\"]')"
            )
        )

    with Session(engine) as session:
        report = migrate_soup_metadata(session, dry_run=True)

    assert report.scanned_soups == 1
    assert report.created_tags == 2
    assert report.created_links == 2
    assert report.skipped_tags == 1
    assert set(inspect(engine).get_table_names()) == {"soups"}


def test_migration_imports_legacy_tags_once_and_recomputes_usage():
    session = _legacy_session()
    try:
        first = migrate_soup_metadata(session)
        second = migrate_soup_metadata(session)

        assert first.scanned_soups == 1
        assert first.created_tags == 2
        assert first.created_links == 2
        assert first.skipped_tags == 1
        assert second.created_tags == 0
        assert second.created_links == 0
        assert sorted(tag.name for tag in session.exec(select(Tag)).all()) == [
            "Story TAG",
            "悬疑",
        ]
        assert all(tag.usage_count == 1 for tag in session.exec(select(Tag)).all())
        assert len(session.exec(select(SoupTag)).all()) == 2
    finally:
        session.close()


def test_data_migration_dry_run_reports_without_writes():
    session = _legacy_session()
    try:
        report = migrate_soup_metadata(session, dry_run=True)

        assert report.created_tags == 2
        assert report.created_links == 2
        assert report.skipped_tags == 1
        assert session.exec(select(Tag)).all() == []
        assert session.exec(select(SoupTag)).all() == []
    finally:
        session.close()
