import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.database import Tag, TagKind, TagStatus
from app.services.tag_resolution import TagSelectionError, resolve_active_tags


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def test_resolver_reuses_normalized_name_and_creates_custom_tag(session):
    existing = Tag(
        name="剧情 推理",
        slug="剧情-推理",
        kind=TagKind.SYSTEM,
        status=TagStatus.ACTIVE,
    )
    session.add(existing)
    session.commit()
    session.refresh(existing)

    tags = resolve_active_tags(
        session,
        [existing.id],
        ["  剧情   推理  ", "夏夜"],
        min_count=1,
        max_count=10,
    )

    assert [tag.name for tag in tags] == ["剧情 推理", "夏夜"]
    assert tags[1].kind == TagKind.CUSTOM
    assert tags[1].status == TagStatus.ACTIVE


def test_resolver_rejects_disabled_tag_id(session):
    disabled = Tag(
        name="停用标签",
        slug="停用标签",
        kind=TagKind.SYSTEM,
        status=TagStatus.DISABLED,
    )
    session.add(disabled)
    session.commit()
    session.refresh(disabled)

    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(session, [disabled.id], [], min_count=1)

    assert captured.value.code == "TAG_NOT_ACTIVE"


def test_resolver_rejects_disabled_normalized_name(session):
    session.add(
        Tag(
            name="停用 标签",
            slug="停用-标签",
            kind=TagKind.CUSTOM,
            status=TagStatus.DISABLED,
        )
    )
    session.commit()

    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(session, [], [" 停用   标签 "], min_count=1)

    assert captured.value.code == "TAG_NOT_ACTIVE"


def test_resolver_requires_minimum_tag_count(session):
    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(session, [], [], min_count=1)

    assert captured.value.code == "NO_TAGS"


def test_resolver_rejects_more_than_maximum_unique_tags(session):
    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(
            session,
            [],
            [f"关键词 {index}" for index in range(11)],
            min_count=1,
            max_count=10,
        )

    assert captured.value.code == "TOO_MANY_TAGS"


def test_resolver_applies_maximum_to_existing_tag_ids(session):
    tags = [
        Tag(
            name=f"已有标签 {index}",
            slug=f"已有标签-{index}",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        for index in range(11)
    ]
    session.add_all(tags)
    session.commit()
    tag_ids = [tag.id for tag in tags]

    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(session, tag_ids, [], min_count=1, max_count=10)

    assert captured.value.code == "TOO_MANY_TAGS"


def test_resolver_wraps_invalid_tag_name(session):
    with pytest.raises(TagSelectionError) as captured:
        resolve_active_tags(session, [], ["危险<script>"], min_count=1)

    assert captured.value.code == "INVALID_TAG_NAME"
    assert captured.value.message == "标签不能包含 HTML"


def test_resolver_reuses_tag_created_between_lookup_and_insert(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'concurrent-tags.db'}",
        connect_args={"check_same_thread": False},
    )
    Tag.__table__.create(engine)

    with Session(engine) as session:
        inserted = False

        def insert_competing_tag(
            _connection,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ):
            nonlocal inserted
            if inserted or not statement.lstrip().upper().startswith("INSERT INTO TAGS"):
                return
            inserted = True
            with Session(engine) as competing_session:
                competing_session.add(
                    Tag(
                        name="并发关键词",
                        slug="并发关键词",
                        kind=TagKind.CUSTOM,
                        status=TagStatus.ACTIVE,
                    )
                )
                competing_session.commit()

        event.listen(engine, "before_cursor_execute", insert_competing_tag)
        try:
            tags = resolve_active_tags(
                session,
                [],
                ["并发关键词"],
                min_count=1,
            )
        finally:
            event.remove(engine, "before_cursor_execute", insert_competing_tag)

        assert [tag.slug for tag in tags] == ["并发关键词"]
        session.commit()

    with Session(engine) as session:
        assert len(session.exec(select(Tag).where(Tag.slug == "并发关键词")).all()) == 1
