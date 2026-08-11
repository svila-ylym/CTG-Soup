from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import collections, turtle_soups
from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import Soup, SoupCollection, User, UserStatus, get_db


def _test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        stored = [
            User(
                username=username,
                nickname=nickname,
                email=f"{username}@example.com",
                hashed_password="x",
            )
            for username, nickname in (
                ("owner", "作者"),
                ("visitor", "访客"),
                ("other", "其他作者"),
            )
        ]
        session.add_all(stored)
        session.commit()
        user_ids = [user.uid for user in stored]

    users = [
        User(
            uid=uid,
            username=username,
            nickname=nickname,
            email=f"{username}@example.com",
            hashed_password="x",
            status=UserStatus.ACTIVE,
        )
        for uid, (username, nickname) in zip(
            user_ids,
            (("owner", "作者"), ("visitor", "访客"), ("other", "其他作者")),
        )
    ]
    current = {"user": users[0]}

    def override_db():
        with Session(engine) as session:
            yield session

    def override_active_user():
        if current["user"] is None:
            raise HTTPException(401, detail="未登录")
        return current["user"]

    def override_optional_user():
        return current["user"]

    app = FastAPI()
    app.include_router(collections.router, prefix="/api/collections")
    app.include_router(turtle_soups.router, prefix="/api/turtle-soups")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_active_user
    app.dependency_overrides[get_optional_current_user] = override_optional_user
    return TestClient(app), engine, users, current


def _add_soup(engine, author_uid: int, collection_id: int, title: str, day: int):
    with Session(engine) as session:
        soup = Soup(
            author_uid=author_uid,
            collection_id=collection_id,
            title=title,
            puzzle="谜面",
            solution="汤底",
            status="published",
            created_at=datetime(2026, 1, 1) + timedelta(days=day),
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        return soup.id


def _soup_payload(collection_id: int):
    return {
        "title": "系列新作",
        "collection_id": collection_id,
        "puzzle": "谜面",
        "solution": "汤底",
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "1",
        "secondary_player_count": "0",
        "tag_ids": [],
        "custom_tags": [],
        "puzzle_image_ids": [],
        "solution_image_ids": [],
        "is_revealed": False,
    }


def test_collection_visibility_order_and_delete_detachment():
    client, engine, users, current = _test_app()
    created = client.post(
        "/api/collections",
        json={"name": "  时间线  ", "description": "按顺序阅读"},
    )
    assert created.status_code == 201
    collection_id = created.json()["id"]
    assert created.json()["name"] == "时间线"
    empty_id = client.post(
        "/api/collections",
        json={"name": "空合集", "description": ""},
    ).json()["id"]
    newest_id = _add_soup(engine, users[0].uid, collection_id, "第三篇", 3)
    oldest_id = _add_soup(engine, users[0].uid, collection_id, "第一篇", 1)

    current["user"] = users[1]
    visible = client.get(
        "/api/collections", params={"owner_uid": users[0].uid}
    ).json()
    assert [item["id"] for item in visible["items"]] == [collection_id]
    assert client.get(f"/api/collections/{empty_id}").status_code == 404
    detail = client.get(f"/api/collections/{collection_id}").json()
    assert [item["id"] for item in detail["soups"]["items"]] == [
        oldest_id,
        newest_id,
    ]

    current["user"] = users[0]
    assert client.delete(f"/api/collections/{collection_id}").status_code == 204
    with Session(engine) as session:
        assert session.get(Soup, oldest_id).collection_id is None
        assert session.get(Soup, newest_id).collection_id is None


def test_soup_collection_association_requires_owner_and_supports_removal():
    client, engine, users, current = _test_app()
    own_id = client.post(
        "/api/collections", json={"name": "自己的合集", "description": ""}
    ).json()["id"]
    current["user"] = users[2]
    other_id = client.post(
        "/api/collections", json={"name": "别人的合集", "description": ""}
    ).json()["id"]
    current["user"] = users[0]

    created = client.post("/api/turtle-soups", json=_soup_payload(own_id))
    assert created.status_code == 201
    soup_id = created.json()["id"]
    assert created.json()["collection"]["id"] == own_id
    assert client.put(
        f"/api/turtle-soups/{soup_id}", json={"collection_id": other_id}
    ).status_code == 403
    preserved = client.put(
        f"/api/turtle-soups/{soup_id}", json={"title": "改名后仍在合集"}
    )
    assert preserved.json()["collection"]["id"] == own_id
    removed = client.put(
        f"/api/turtle-soups/{soup_id}", json={"collection_id": None}
    )
    assert removed.status_code == 200
    assert removed.json()["collection"] is None
