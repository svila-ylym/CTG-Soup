from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import home
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Soup,
    Tag,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
    get_db,
)


def _client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    now = datetime.utcnow()
    with Session(engine) as session:
        author = User(
            username="home-author",
            nickname="首页作者",
            email="home-author@example.com",
            hashed_password="unused",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        tag = Tag(
            slug="首页标签",
            name="首页标签",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add_all([author, tag])
        session.commit()
        session.refresh(author)
        session.refresh(tag)
        public_soup = Soup(
            author_uid=author.uid,
            title="公开推荐汤",
            puzzle="这是首页展示的随机谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            status="published",
            avg_rating=8.5,
            rating_count=2,
        )
        deleted_soup = Soup(
            author_uid=author.uid,
            title="已删除汤",
            puzzle="不应展示",
            solution="汤底",
            status="deleted",
        )
        session.add_all([public_soup, deleted_soup])
        session.flush()
        older = Competition(
            creator_uid=author.uid,
            name="旧比赛",
            description="旧比赛说明",
            start_time=now - timedelta(days=3),
            end_time=now - timedelta(days=2),
            required_tag_ids=[tag.id],
            status=CompetitionStatus.COMPLETED,
            created_at=now - timedelta(days=2),
        )
        latest = Competition(
            creator_uid=author.uid,
            name="最新比赛",
            description="<p>最新的 <strong>比赛说明</strong></p>",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=2),
            required_tag_ids=[tag.id],
            competition_color="#2468AC",
            custom_page_config={
                "cover_asset_id": 99,
                "cover_url": "/storage/images/home-cover.webp",
            },
            status=CompetitionStatus.ONGOING,
            created_at=now,
        )
        session.add_all([older, latest])
        session.flush()
        session.add(CompetitionEntry(
            competition_id=latest.id,
            soup_id=public_soup.id,
            author_uid=author.uid,
        ))
        session.commit()

    app = FastAPI()
    app.include_router(home.router, prefix="/api/home")

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    cache_writes = []
    monkeypatch.setattr(home, "cache_get", lambda _key: None)
    monkeypatch.setattr(home, "cache_set", lambda key, value, ttl: cache_writes.append((key, value, ttl)) or True)
    monkeypatch.setattr(home, "cache_delete", lambda _key: True)
    return TestClient(app), cache_writes


def test_home_discovery_returns_latest_competition_public_soups_and_cache_headers(monkeypatch):
    client, cache_writes = _client(monkeypatch)

    response = client.get("/api/home/discovery")

    assert response.status_code == 200
    assert response.headers["cache-control"] == home.HOME_DISCOVERY_BROWSER_CACHE
    payload = response.json()
    assert payload["latest_competition"]["name"] == "最新比赛"
    assert payload["latest_competition"]["description_excerpt"] == "最新的 比赛说明"
    assert payload["latest_competition"]["cover_asset_id"] == 99
    assert payload["latest_competition"]["cover_url"] == "/storage/images/home-cover.webp"
    assert payload["latest_competition"]["required_tags"] == ["首页标签"]
    assert payload["latest_competition"]["entry_count"] == 1
    assert [item["title"] for item in payload["random_soups"]] == ["公开推荐汤"]
    assert payload["random_soups"][0]["competition_colors"] == ["#2468AC"]
    assert cache_writes[0][2] == 60

    refreshed = client.get("/api/home/discovery", params={"refresh": True})
    assert refreshed.status_code == 200
    assert refreshed.headers["cache-control"] == "no-store"
    assert len(cache_writes) == 1


def test_home_discovery_accepts_valid_cache_and_drops_invalid_schema(monkeypatch):
    client, _cache_writes = _client(monkeypatch)
    cached = {
        "lines": ["缓存文案"],
        "latest_competition": None,
        "random_soups": [],
    }
    monkeypatch.setattr(home, "cache_get", lambda _key: cached)
    response = client.get("/api/home/discovery")
    assert response.status_code == 200
    assert response.json() == cached

    deleted = []
    monkeypatch.setattr(home, "cache_get", lambda _key: {"lines": "not-a-list"})
    monkeypatch.setattr(home, "cache_delete", lambda key: deleted.append(key) or True)
    response = client.get("/api/home/discovery")
    assert response.status_code == 200
    assert response.json()["latest_competition"]["name"] == "最新比赛"
    assert deleted == [home.HOME_DISCOVERY_CACHE_KEY]
