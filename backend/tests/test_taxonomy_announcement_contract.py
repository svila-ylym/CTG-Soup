from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import admin, announcements
from app.api.auth import get_current_admin_user, get_optional_current_user
from app.models.database import (
    Announcement,
    AnnouncementStatus,
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    OperationLog,
    Soup,
    SoupTag,
    Tag,
    TagAlias,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
    get_db,
)


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin_user = User(
            username="taxonomy-admin",
            nickname="管理员",
            email="taxonomy-admin@example.com",
            hashed_password="unused",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        regular_user = User(
            username="taxonomy-user",
            nickname="用户",
            email="taxonomy-user@example.com",
            hashed_password="unused",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        source = Tag(slug="source", name="来源", kind=TagKind.SYSTEM)
        target = Tag(slug="target", name="目标", kind=TagKind.CUSTOM)
        soup = Soup(
            author_uid=admin_user.uid or 1,
            title="作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count=1,
            secondary_player_count=0,
        )
        session.add_all([admin_user, regular_user, source, target])
        session.commit()
        session.refresh(admin_user)
        session.refresh(regular_user)
        session.refresh(source)
        session.refresh(target)
        soup.author_uid = admin_user.uid
        session.add(soup)
        session.commit()
        session.refresh(soup)
        session.add(SoupTag(soup_id=soup.id, tag_id=source.id))
        competition = Competition(
            creator_uid=admin_user.uid,
            name="标签赛",
            description="比赛",
            start_time=datetime.utcnow() - timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=1),
            required_tag_ids=[source.id],
            status=CompetitionStatus.ONGOING,
        )
        session.add(competition)
        session.commit()
        session.refresh(competition)
        ids = admin_user.uid, regular_user.uid, source.id, target.id, soup.id, competition.id

    app = FastAPI()
    app.include_router(admin.router, prefix="/api/admin")
    app.include_router(announcements.router, prefix="/api/announcements")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_admin():
        with Session(engine) as session:
            return session.get(User, ids[0])

    async def override_optional():
        return None

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin_user] = override_admin
    app.dependency_overrides[get_optional_current_user] = override_optional
    return TestClient(app), engine, ids


def test_admin_tag_create_sanitizes_text_and_public_tags_hide_disabled():
    client, engine, ids = _client()
    response = client.post(
        "/api/admin/tags",
        json={"name": " 新标签 ", "description": "<script>alert(1)</script>说明"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "新标签"
    assert "<script>" not in payload["description"]

    disabled = client.put(f"/api/admin/tags/{payload['id']}", json={"status": "disabled"})
    assert disabled.status_code == 200
    public = client.get("/api/announcements")
    assert public.status_code == 200
    with Session(engine) as session:
        assert session.exec(select(OperationLog)).first() is not None


def test_tag_merge_moves_soups_and_preserves_alias():
    client, engine, ids = _client()
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.required_tag_ids = [ids[2], ids[3]]
        session.commit()

    response = client.post(f"/api/admin/tags/{ids[2]}/merge", json={"target_tag_id": ids[3]})
    assert response.status_code == 200
    with Session(engine) as session:
        assert session.get(SoupTag, (ids[4], ids[3])) is not None
        alias = session.exec(select(TagAlias).where(TagAlias.tag_id == ids[3])).first()
        assert alias is not None and alias.alias_slug == "source"
        assert session.get(Competition, ids[5]).required_tag_ids == [ids[3]]
        assert session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == ids[5],
                CompetitionEntry.soup_id == ids[4],
            )
        ).one() is not None


def test_tag_merge_rejects_locked_independent_competition_configuration():
    client, engine, ids = _client()
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.score_type = "independent"
        entry = CompetitionEntry(
            competition_id=competition.id,
            soup_id=ids[4],
            author_uid=ids[0],
            judge_score=8.0,
        )
        session.add(entry)
        session.commit()

    response = client.post(
        f"/api/admin/tags/{ids[2]}/merge",
        json={"target_tag_id": ids[3]},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INDEPENDENT_SCORING_LOCKED"
    with Session(engine) as session:
        assert session.get(Competition, ids[5]).required_tag_ids == [ids[2]]
        assert session.get(SoupTag, (ids[4], ids[2])) is not None
        assert session.get(SoupTag, (ids[4], ids[3])) is None
        assert session.get(Tag, ids[2]).status == TagStatus.ACTIVE


def test_disabling_tag_rebuilds_unsettled_membership_but_keeps_settled_entries():
    client, engine, ids = _client()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        settled = Competition(
            creator_uid=ids[0],
            name="已冻结标签赛",
            description="比赛",
            start_time=datetime.utcnow() - timedelta(days=2),
            end_time=datetime.utcnow() - timedelta(days=1),
            required_tag_ids=[ids[2]],
            status=CompetitionStatus.COMPLETED,
            settled_at=datetime.utcnow(),
            result_snapshot={"total": [], "groups": []},
        )
        session.add(settled)
        session.flush()
        session.add_all([
            CompetitionEntry(
                competition_id=ids[5],
                soup_id=soup.id,
                author_uid=soup.author_uid,
            ),
            CompetitionEntry(
                competition_id=settled.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
            ),
        ])
        session.commit()
        settled_id = settled.id

    response = client.put(
        f"/api/admin/tags/{ids[2]}",
        json={"status": "disabled"},
    )

    assert response.status_code == 200
    with Session(engine) as session:
        assert session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == ids[5]
            )
        ).all() == []
        assert session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == settled_id
            )
        ).one() is not None


def test_announcements_only_return_published_and_strip_html():
    client, engine, ids = _client()
    created = client.post(
        "/api/admin/announcements",
        json={
            "title": "公告",
            "content": "<b>重要</b><script>bad()</script>",
            "priority": 5,
            "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
    assert client.get("/api/announcements").json()["items"] == []

    published = client.post(f"/api/admin/announcements/{created.json()['id']}/publish")
    assert published.status_code == 200
    items = client.get("/api/announcements").json()["items"]
    assert items[0]["content"] == "重要bad()"
    with Session(engine) as session:
        assert session.get(Announcement, created.json()["id"]).status == AnnouncementStatus.PUBLISHED
