from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models.database import (
    Soup,
    SoupTag,
    Tag,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.soups import SoupCreate, SoupResponse


def _valid_soup_data(**changes):
    data = {
        "title": "谜题",
        "puzzle": "谜面",
        "solution": "汤底",
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "一人",
        "secondary_player_count": "无人",
        "tag_ids": [],
        "custom_tags": [],
    }
    data.update(changes)
    return data


def test_soup_create_requires_taxonomy_and_accepts_arbitrary_people_text():
    item = SoupCreate(**_valid_soup_data())

    assert item.genre == "本格"
    assert item.soup_color == "清汤"
    assert item.main_player_count == "一人"
    assert item.secondary_player_count == "无人"

    for changes in ({"genre": "未分类"}, {"soup_color": "未分类"}):
        with pytest.raises(ValidationError):
            SoupCreate(**_valid_soup_data(**changes))

    arbitrary = SoupCreate(
        **_valid_soup_data(
            main_player_count="",
            secondary_player_count="👩‍🚀/AI 和不确定的人",
        )
    )
    assert arbitrary.main_player_count == ""
    assert arbitrary.secondary_player_count == "👩‍🚀/AI 和不确定的人"

    for missing in ("main_player_count", "secondary_player_count"):
        data = _valid_soup_data()
        data.pop(missing)
        with pytest.raises(ValidationError):
            SoupCreate(**data)


def test_soup_create_normalizes_custom_tags_and_limits_total_tags():
    item = SoupCreate(
        **_valid_soup_data(
            tag_ids=[2, 2, 3],
            custom_tags=[" 剧情   推理 ", "剧情 推理"],
        )
    )

    assert item.tag_ids == [2, 3]
    assert item.custom_tags == ["剧情 推理"]

    with pytest.raises(ValidationError):
        SoupCreate(
            **_valid_soup_data(
                tag_ids=list(range(1, 11)),
                custom_tags=["额外"],
            )
        )


def test_soup_response_uses_only_canonical_score_and_uid_fields():
    response = SoupResponse(
        id=7,
        title="谜题",
        puzzle="谜面",
        solution=None,
        solution_available=True,
        is_solution_public=False,
        genre="本格",
        soup_color="清汤",
        main_player_count="一人",
        secondary_player_count="无人",
        tags=[],
        author_uid=42,
        author={"uid": 42, "username": "author", "nickname": "作者"},
        average_score=8.5,
        rating_count=2,
        like_count=3,
        favorite_count=4,
        view_count=5,
        status="published",
        is_liked=False,
        is_favorited=False,
        my_rating=None,
        can_manage=False,
        created_at=datetime(2026, 8, 8),
        updated_at=datetime(2026, 8, 8),
    )

    payload = response.model_dump()
    assert payload["author_uid"] == 42
    assert payload["average_score"] == 8.5
    assert "avg_score" not in payload
    assert "score_count" not in payload
    assert "author_id" not in payload


def test_soup_tag_composite_key_rejects_duplicate_links():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(
            username="metadata-author",
            nickname="作者",
            email="metadata@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        soup = Soup(
            author_uid=user.uid,
            title="谜题",
            puzzle="谜面",
            solution="汤底",
        )
        tag = Tag(
            slug="story",
            name="Story",
            kind=TagKind.CUSTOM,
            status=TagStatus.ACTIVE,
        )
        session.add(soup)
        session.add(tag)
        session.commit()
        session.refresh(soup)
        session.refresh(tag)
        session.add(SoupTag(soup_id=soup.id, tag_id=tag.id))
        session.commit()
        session.add(SoupTag(soup_id=soup.id, tag_id=tag.id))

        with pytest.raises(IntegrityError):
            session.commit()
