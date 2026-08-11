from datetime import datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import tags, turtle_soups
from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Soup,
    SoupImage,
    SoupTag,
    Tag,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
    UploadedAsset,
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


def test_list_and_detail_include_competition_colors():
    client, engine, _active_id, _, soup_id, _, _ = _client()
    with Session(engine) as session:
        soup = session.get(Soup, soup_id)
        competition = Competition(
            creator_uid=soup.author_uid,
            name="竞赛色接口",
            description="比赛",
            start_time=soup.created_at - timedelta(hours=1),
            end_time=soup.created_at + timedelta(hours=1),
            required_tag_ids=[1],
            competition_color="#2468AC",
            status=CompetitionStatus.ONGOING,
        )
        session.add(competition)
        session.flush()
        session.add(CompetitionEntry(
            competition_id=competition.id,
            soup_id=soup.id,
            author_uid=soup.author_uid,
        ))
        session.commit()

    listed = client.get("/api/turtle-soups")
    detail = client.get(f"/api/turtle-soups/{soup_id}")

    assert listed.status_code == detail.status_code == 200
    assert listed.json()["items"][0]["competition_colors"] == ["#2468AC"]
    assert detail.json()["competition_colors"] == ["#2468AC"]


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


def test_list_supports_average_rating_sort():
    client, engine, _, _, existing_soup_id, _, _ = _client()
    with Session(engine) as session:
        existing = session.get(Soup, existing_soup_id)
        existing.avg_rating = 9.0
        second = Soup(
            author_uid=existing.author_uid,
            title="低平均分作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count="👩‍🚀/AI",
            secondary_player_count="不确定",
            avg_rating=3.0,
            created_at=datetime(2020, 1, 1),
        )
        session.add(second)
        session.commit()
        session.refresh(second)

    response = client.get("/api/turtle-soups", params={"sort_by": "score"})

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == existing_soup_id


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


def test_soup_text_preserves_leading_trailing_spaces_and_blank_lines():
    client, engine, _, _, _, _, _ = _client()
    puzzle = "\n  第一行\n第二行  \n"
    solution = "\n汤底第一行\n\n汤底第三行  \n"

    response = client.post(
        "/api/turtle-soups",
        json={
            "title": "保留排版",
            "puzzle": puzzle,
            "solution": solution,
            "genre": "本格",
            "soup_color": "清汤",
            "main_player_count": "",
            "secondary_player_count": "",
        },
    )

    assert response.status_code == 201
    assert response.json()["puzzle"] == puzzle
    assert response.json()["solution"] == solution
    with Session(engine) as session:
        soup = session.exec(select(Soup).where(Soup.title == "保留排版")).one()
        assert soup.puzzle == puzzle
        assert soup.solution == solution


def test_image_only_soup_hides_solution_assets_until_reveal():
    client, engine, _, _, _, _, _ = _client()
    with Session(engine) as session:
        author = session.exec(select(User).where(User.username == "api-author")).one()
        assets = [
            UploadedAsset(
                owner_uid=author.uid,
                kind="image",
                storage_key=f"soups/image-{index}.png",
                public_url=f"/storage/soups/image-{index}.png",
                mime_type="image/png",
                size=100 + index,
            )
            for index in range(2)
        ]
        session.add_all(assets)
        session.commit()
        for asset in assets:
            session.refresh(asset)
        puzzle_image_id, solution_image_id = [asset.id for asset in assets]

    created = client.post(
        "/api/turtle-soups",
        json={
            "title": "纯图片汤",
            "puzzle": "",
            "solution": "",
            "genre": "变格",
            "soup_color": "红汤",
            "main_player_count": "",
            "secondary_player_count": "",
            "puzzle_image_ids": [puzzle_image_id],
            "solution_image_ids": [solution_image_id],
        },
    )

    assert created.status_code == 201
    soup_id = created.json()["id"]
    hidden = client.get(f"/api/turtle-soups/{soup_id}")
    revealed = client.get(f"/api/turtle-soups/{soup_id}", params={"reveal": True})
    assert [item["id"] for item in hidden.json()["puzzle_images"]] == [puzzle_image_id]
    assert hidden.json()["solution"] is None
    assert hidden.json()["solution_images"] == []
    assert [item["id"] for item in revealed.json()["solution_images"]] == [solution_image_id]
    with Session(engine) as session:
        links = session.exec(
            select(SoupImage).where(SoupImage.soup_id == soup_id).order_by(SoupImage.sort_order)
        ).all()
        assert [(link.placement, link.asset_id) for link in links] == [
            ("puzzle", puzzle_image_id),
            ("solution", solution_image_id),
        ]


def test_soup_images_must_be_owned_and_cannot_be_reused_across_sections():
    client, engine, _, _, _, _, _ = _client()
    with Session(engine) as session:
        other = session.exec(select(User).where(User.username == "api-other")).one()
        asset = UploadedAsset(
            owner_uid=other.uid,
            kind="image",
            storage_key="soups/other.png",
            public_url="/storage/soups/other.png",
            mime_type="image/png",
            size=100,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

    base = {
        "title": "图片校验",
        "puzzle": "谜面",
        "solution": "汤底",
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "",
        "secondary_player_count": "",
    }
    not_owned = client.post(
        "/api/turtle-soups",
        json={**base, "puzzle_image_ids": [asset.id]},
    )
    duplicated = client.post(
        "/api/turtle-soups",
        json={
            **base,
            "puzzle_image_ids": [asset.id],
            "solution_image_ids": [asset.id],
        },
    )

    assert not_owned.status_code == 422
    assert not_owned.json()["detail"]["code"] == "INVALID_SOUP_IMAGE"
    assert duplicated.status_code == 422
    assert duplicated.json()["detail"]["code"] == "DUPLICATE_SOUP_IMAGE"
