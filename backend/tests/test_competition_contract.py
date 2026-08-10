from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import competitions
from app.api.auth import get_current_admin_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Soup,
    SoupTag,
    Tag,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
    get_db,
)
from app.services.competition_entries import (
    evaluate_soup_competitions,
    refresh_soup_competition_scores,
)


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin = User(
            username="competition-admin",
            nickname="管理员",
            email="competition-admin@example.com",
            hashed_password="not-used",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        author = User(
            username="competition-author",
            nickname="作者",
            email="competition-author@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        tag = Tag(slug="原创", name="原创", kind=TagKind.SYSTEM, status=TagStatus.ACTIVE)
        disabled = Tag(slug="停用", name="停用", kind=TagKind.SYSTEM, status=TagStatus.DISABLED)
        session.add_all([admin, author, tag, disabled])
        session.commit()
        session.refresh(admin)
        session.refresh(author)
        session.refresh(tag)
        session.refresh(disabled)
        now = datetime.utcnow()
        soup = Soup(
            author_uid=author.uid,
            title="参赛作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count=1,
            secondary_player_count=0,
            created_at=now,
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        session.add(SoupTag(soup_id=soup.id, tag_id=tag.id))
        competition = Competition(
            creator_uid=admin.uid,
            name="原创赛",
            description="比赛",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            required_tag_ids=[tag.id],
            status=CompetitionStatus.ONGOING,
        )
        session.add(competition)
        session.commit()
        session.refresh(competition)
        ids = admin.uid, author.uid, tag.id, disabled.id, soup.id, competition.id

    app = FastAPI()
    app.include_router(competitions.router, prefix="/api/competitions")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_admin():
        with Session(engine) as session:
            return session.get(User, ids[0])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin_user] = override_admin
    return TestClient(app), engine, ids


def test_create_competition_uses_canonical_creator_and_required_tag_ids():
    client, _, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "新赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[2]],
            "score_type": "average",
            "top_n": 10,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["creator_uid"] == ids[0]
    assert payload["required_tag_ids"] == [ids[2]]
    assert "creator_id" not in payload
    assert "entry_tags" not in payload


def test_create_competition_creates_global_custom_keyword():
    client, engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "夏夜赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": ["  夏夜   推理  "],
        },
    )

    assert response.status_code == 201
    with Session(engine) as session:
        tag = session.exec(select(Tag).where(Tag.slug == "夏夜-推理")).one()
        assert tag.kind == TagKind.CUSTOM
        assert tag.status == TagStatus.ACTIVE
        assert response.json()["required_tag_ids"] == [tag.id]


def test_create_competition_reuses_keyword_selected_by_id_and_name():
    client, engine, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "复用标签赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[2]],
            "custom_tags": [" 原创 "],
        },
    )

    assert response.status_code == 201
    assert response.json()["required_tag_ids"] == [ids[2]]
    with Session(engine) as session:
        assert len(session.exec(select(Tag).where(Tag.slug == "原创")).all()) == 1


def test_create_competition_rejects_more_than_ten_unique_keywords():
    client, _engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "关键词过多",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": [f"关键词 {index}" for index in range(11)],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TOO_MANY_TAGS"


def test_create_competition_rolls_back_new_keyword_when_later_name_is_invalid():
    client, engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "回滚标签赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": ["临时关键词", "危险<script>"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_TAG_NAME"
    with Session(engine) as session:
        assert session.exec(select(Tag).where(Tag.slug == "临时关键词")).first() is None


def test_competition_entry_is_created_once_for_matching_soup():
    _, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        first = evaluate_soup_competitions(session, soup)
        second = evaluate_soup_competitions(session, soup)
        assert len(first) == 1
        assert second == first
        entries = session.exec(select(CompetitionEntry)).all()
        assert len(entries) == 1


def test_settled_competition_does_not_accept_new_entries():
    _, engine, ids = _setup()
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.status = CompetitionStatus.COMPLETED
        competition.settled_at = datetime.utcnow()
        soup = session.get(Soup, ids[4])
        assert evaluate_soup_competitions(session, soup) == []


def test_non_matching_and_out_of_range_soups_are_not_entered():
    _, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        competition = session.get(Competition, ids[5])
        competition.required_tag_ids = [ids[3]]
        assert evaluate_soup_competitions(session, soup) == []

        competition.required_tag_ids = [ids[2]]
        competition.start_time = soup.created_at + timedelta(minutes=1)
        competition.end_time = soup.created_at + timedelta(hours=1)
        assert evaluate_soup_competitions(session, soup) == []


def test_create_competition_rejects_disabled_tag():
    client, _, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "无效比赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[3]],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "COMPETITION_TAG_NOT_ACTIVE"


def test_settlement_snapshot_is_stable():
    client, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        evaluate_soup_competitions(session, soup)
        competition = session.get(Competition, ids[5])
        competition.end_time = datetime.utcnow() - timedelta(minutes=1)
        session.commit()

    first = client.post(f"/api/competitions/{ids[5]}/settle")
    second = client.post(f"/api/competitions/{ids[5]}/settle")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["result_snapshot"] == second.json()["result_snapshot"]


def test_ongoing_competition_cannot_be_settled_early():
    client, _, ids = _setup()
    response = client.post(f"/api/competitions/{ids[5]}/settle")
    assert response.status_code == 409


def test_create_competition_accepts_timezone_aware_range():
    client, _, ids = _setup()
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/competitions",
        json={
            "name": "时区比赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ongoing"


def test_create_ongoing_competition_collects_existing_matching_soup():
    client, engine, ids = _setup()
    now = datetime.now(timezone.utc)

    response = client.post(
        "/api/competitions",
        json={
            "name": "自动收录赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    assert response.status_code == 201
    assert [entry["soup_id"] for entry in response.json()["entries"]] == [ids[4]]
    with Session(engine) as session:
        entries = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == response.json()["id"]
            )
        ).all()
        assert [entry.soup_id for entry in entries] == [ids[4]]


def test_create_completed_competition_collects_historical_matching_soup():
    client, engine, ids = _setup()
    now = datetime.utcnow()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.created_at = now - timedelta(hours=2)
        session.commit()

    response = client.post(
        "/api/competitions",
        json={
            "name": "历史自动收录赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=3)).replace(
                tzinfo=timezone.utc
            ).isoformat(),
            "end_time": (now - timedelta(hours=1)).replace(
                tzinfo=timezone.utc
            ).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["settled_at"] is None
    assert [entry["soup_id"] for entry in response.json()["entries"]] == [ids[4]]


def test_competition_entry_score_tracks_average_until_settlement():
    client, engine, ids = _setup()
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/competitions",
        json={
            "name": "平均分同步赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.avg_rating = 8.5
        refresh_soup_competition_scores(session, soup)
        session.commit()
        entry = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == created.json()["id"]
            )
        ).one()
        assert entry.final_score == 8.5


def test_unranked_entries_are_frozen_after_settlement():
    client, engine, ids = _setup()
    with Session(engine) as session:
        reference_time = datetime.utcnow()
        first = session.get(Soup, ids[4])
        first.avg_rating = 9.0
        first.created_at = reference_time - timedelta(minutes=30)
        second = Soup(
            author_uid=ids[1],
            title="第二份参赛作品",
            puzzle="谜面",
            solution="汤底",
            avg_rating=5.0,
            created_at=reference_time - timedelta(minutes=30),
        )
        session.add(second)
        session.flush()
        session.add(SoupTag(soup_id=second.id, tag_id=ids[2]))
        competition = session.get(Competition, ids[5])
        competition.top_n = 1
        competition.end_time = reference_time - timedelta(minutes=1)
        session.flush()
        evaluate_soup_competitions(session, first)
        evaluate_soup_competitions(session, second)
        second_id = second.id

    settled = client.post(f"/api/competitions/{ids[5]}/settle")
    assert settled.status_code == 200

    with Session(engine) as session:
        second = session.get(Soup, second_id)
        second.avg_rating = 10.0
        refresh_soup_competition_scores(session, second)
        session.commit()
        entry = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == ids[5],
                CompetitionEntry.soup_id == second_id,
            )
        ).one()
        assert entry.rank is None
        assert entry.final_score == 5.0
