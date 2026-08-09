from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import tags, turtle_soups
from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import (
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


def _client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        author = User(
            username="api-author",
            nickname="作者",
            email="api-author@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        other = User(
            username="api-other",
            nickname="其他用户",
            email="api-other@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        active = Tag(
            slug="悬疑",
            name="悬疑",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        disabled = Tag(
            slug="停用",
            name="停用",
            kind=TagKind.SYSTEM,
            status=TagStatus.DISABLED,
        )
        session.add_all([author, other, active, disabled])
        session.commit()
        session.refresh(author)
        session.refresh(other)
        session.refresh(active)
        session.refresh(disabled)
        soup = Soup(
            author_uid=author.uid,
            title="已有作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count="两个人",
            secondary_player_count="一个旁观者",
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        session.add(SoupTag(soup_id=soup.id, tag_id=active.id))
        active.usage_count = 1
        session.commit()
        author_uid = author.uid
        other_uid = other.uid
        active_id = active.id
        disabled_id = disabled.id
        soup_id = soup.id

    app = FastAPI()
    app.include_router(turtle_soups.router, prefix="/api/turtle-soups")
    app.include_router(tags.router, prefix="/api/tags")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_author():
        with Session(engine) as session:
            return session.get(User, author_uid)

    async def override_other():
        with Session(engine) as session:
            return session.get(User, other_uid)

    async def override_optional():
        return None

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_author
    app.dependency_overrides[get_optional_current_user] = override_optional
    return TestClient(app), engine, active_id, disabled_id, soup_id, override_author, override_other


def test_create_soup_returns_normalized_metadata_and_custom_tag():
    client, engine, active_id, _, _, _, _ = _client()

    response = client.post(
        "/api/turtle-soups",
        json={
            "title": "新谜题",
            "puzzle": "新谜面",
            "solution": "新汤底",
            "genre": "变格",
            "soup_color": "红汤",
            "main_player_count": "一人",
            "secondary_player_count": "无人",
            "tag_ids": [active_id],
            "custom_tags": [" 剧情   推理 "],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["genre"] == "变格"
    assert payload["soup_color"] == "红汤"
    assert payload["main_player_count"] == "一人"
    assert [tag["name"] for tag in payload["tags"]] == ["悬疑", "剧情 推理"]
    assert "avg_score" not in payload
    with Session(engine) as session:
        assert session.exec(select(Tag).where(Tag.slug == "剧情-推理")).first() is not None


def test_create_soup_rejects_disabled_tag():
    client, _, _, disabled_id, _, _, _ = _client()
    response = client.post(
        "/api/turtle-soups",
        json={
            "title": "新谜题",
            "puzzle": "新谜面",
            "solution": "新汤底",
            "genre": "本格",
            "soup_color": "清汤",
            "main_player_count": "一人",
            "secondary_player_count": "无人",
            "tag_ids": [disabled_id],
            "custom_tags": [],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TAG_NOT_ACTIVE"


def test_list_filters_by_taxonomy_and_increments_tag_page_view():
    client, engine, active_id, _, soup_id, _, _ = _client()

    response = client.get(
        "/api/turtle-soups",
        params={"genre": "本格", "soup_color": "清汤", "tag_id": active_id},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == soup_id
    with Session(engine) as session:
        assert session.get(Tag, active_id).view_count == 1


def test_non_author_cannot_update_soup():
    client, _, _, _, soup_id, _, override_other = _client()
    client.app.dependency_overrides[get_current_active_user] = override_other

    response = client.put(
        f"/api/turtle-soups/{soup_id}",
        json={
            "title": "篡改",
            "genre": "本格",
            "soup_color": "清汤",
            "main_player_count": "任意描述",
            "secondary_player_count": "",
            "tag_ids": [],
            "custom_tags": [],
        },
    )

    assert response.status_code == 403


def test_tags_endpoint_returns_active_tags_only():
    client, _, _, _, _, _, _ = _client()

    response = client.get("/api/tags")

    assert response.status_code == 200
    assert [tag["name"] for tag in response.json()["items"]] == ["悬疑"]


def test_list_supports_bayesian_rating_sort():
    client, engine, _, _, existing_soup_id, _, _ = _client()
    with Session(engine) as session:
        existing = session.get(Soup, existing_soup_id)
        existing.avg_rating = 9.0
        existing.bayesian_rating = 2.0
        second = Soup(
            author_uid=existing.author_uid,
            title="贝叶斯优先",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count="👩‍🚀/AI",
            secondary_player_count="不确定",
            avg_rating=3.0,
            bayesian_rating=8.0,
            created_at=datetime(2020, 1, 1),
        )
        session.add(second)
        session.commit()
        session.refresh(second)
        second_id = second.id

    response = client.get("/api/turtle-soups", params={"sort_by": "bayesian"})

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == second_id


@pytest.mark.parametrize(
    ("main", "secondary"),
    [
        ("一群人", "影子和一只猫"),
        ("", ""),
        ("👩‍🚀/AI", "不确定"),
    ],
)
def test_soup_people_fields_accept_arbitrary_text(main, secondary):
    client, _, active_id, _, _, _, _ = _client()

    response = client.post(
        "/api/turtle-soups",
        json={
            "title": "人物描述",
            "puzzle": "谜面",
            "solution": "汤底",
            "genre": "变格",
            "soup_color": "红汤",
            "main_player_count": main,
            "secondary_player_count": secondary,
            "tag_ids": [active_id],
            "custom_tags": [],
        },
    )

    assert response.status_code == 201
    assert response.json()["main_player_count"] == main
    assert response.json()["secondary_player_count"] == secondary
