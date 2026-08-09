from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api.auth import get_current_active_user, get_optional_current_user
from app.api import turtle_soups
from app.models.database import Comment, CommentTargetType, Rating, Soup, User, UserRole, UserStatus, get_db


def _test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        users = [
            User(username="author", nickname="作者", email="author@example.com", hashed_password="x"),
            User(username="commenter", nickname="评论者", email="commenter@example.com", hashed_password="x"),
            User(username="other", nickname="其他人", email="other@example.com", hashed_password="x"),
            User(username="admin", nickname="管理员", email="admin@example.com", hashed_password="x", role=UserRole.ADMIN),
        ]
        session.add_all(users)
        session.commit()
        for user in users:
            session.refresh(user)
        user_ids = [user.uid for user in users]
        soup = Soup(author_uid=users[0].uid, title="谜题", puzzle="谜面", solution="汤底")
        session.add(soup)
        session.commit()
        session.refresh(soup)
        soup_id = soup.id

    app = FastAPI()
    app.include_router(turtle_soups.router, prefix="/api/turtle-soups")
    users = [
        User(
            uid=user_id,
            username=username,
            nickname=nickname,
            email=email,
            hashed_password="x",
            role=role,
            status=UserStatus.ACTIVE,
        )
        for user_id, username, nickname, email, role in zip(
            user_ids,
            ("author", "commenter", "other", "admin"),
            ("作者", "评论者", "其他人", "管理员"),
            ("author@example.com", "commenter@example.com", "other@example.com", "admin@example.com"),
            (UserRole.USER, UserRole.USER, UserRole.USER, UserRole.ADMIN),
        )
    ]
    current = {"user": users[1]}

    def override_db():
        with Session(engine) as session:
            yield session

    def override_user():
        return current["user"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user
    app.dependency_overrides[get_optional_current_user] = override_user
    return TestClient(app), engine, soup_id, users, current


def test_comments_create_list_reply_and_paginate_with_minimal_author_contract():
    client, _engine, soup_id, _users, _current = _test_app()

    first = client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "第一条"})
    assert first.status_code == 201
    assert set(first.json()) == {"id", "content", "author_uid", "parent_id", "created_at", "replies"}
    reply = client.post(
        f"/api/turtle-soups/{soup_id}/comments",
        json={"content": "回复", "parent_id": first.json()["id"]},
    )
    assert reply.status_code == 201
    client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "第二条"})

    response = client.get(f"/api/turtle-soups/{soup_id}/comments", params={"page": 1, "page_size": 20})

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page_size"] == 20
    root = next(item for item in response.json()["items"] if item["id"] == first.json()["id"])
    assert root["replies"] == [reply.json()]


def test_comments_reject_html_and_invalid_reply_parents():
    client, _engine, soup_id, _users, _current = _test_app()

    html = client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "<script>alert(1)</script>"})
    missing_parent = client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "回复", "parent_id": 999})

    assert html.status_code == 422
    assert missing_parent.status_code == 422


def test_comments_hide_deleted_content_and_allow_only_author_or_admin_to_delete():
    client, engine, soup_id, users, current = _test_app()
    created = client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "可删除"})
    comment_id = created.json()["id"]
    assert client.delete(f"/api/turtle-soups/{soup_id}/comments/{comment_id}").status_code == 204

    created = client.post(f"/api/turtle-soups/{soup_id}/comments", json={"content": "管理员删除"})
    comment_id = created.json()["id"]
    current["user"] = users[2]
    assert client.delete(f"/api/turtle-soups/{soup_id}/comments/{comment_id}").status_code == 403

    current["user"] = users[3]
    assert client.delete(f"/api/turtle-soups/{soup_id}/comments/{comment_id}").status_code == 204
    with Session(engine) as session:
        comment = session.get(Comment, comment_id)
        assert comment.status == "deleted"
        session.add(
            Comment(
                author_uid=users[1].uid,
                target_type=CommentTargetType.SOUP,
                target_id=soup_id,
                content="已隐藏",
                status="hidden",
            )
        )
        session.commit()
    assert client.get(f"/api/turtle-soups/{soup_id}/comments").json()["items"] == []


def test_rating_is_unique_per_user_and_soup():
    _client, engine, soup_id, users, _current = _test_app()
    with Session(engine) as session:
        session.add(Rating(user_uid=users[1].uid, soup_id=soup_id, score=8))
        session.commit()
        session.add(Rating(user_uid=users[1].uid, soup_id=soup_id, score=9))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("duplicate ratings must be rejected")


def test_repeated_interactions_and_ratings_are_idempotent():
    client, engine, soup_id, users, _current = _test_app()

    assert client.put(f"/api/turtle-soups/{soup_id}/like", json={"active": True}).status_code == 200
    assert client.put(f"/api/turtle-soups/{soup_id}/like", json={"active": True}).status_code == 200
    assert client.put(f"/api/turtle-soups/{soup_id}/favorite", json={"active": True}).status_code == 200
    assert client.put(f"/api/turtle-soups/{soup_id}/favorite", json={"active": True}).status_code == 200
    assert client.put(f"/api/turtle-soups/{soup_id}/rating", json={"score": 8}).status_code == 200
    assert client.put(f"/api/turtle-soups/{soup_id}/rating", json={"score": 9}).status_code == 200

    with Session(engine) as session:
        assert len(session.exec(select(Rating).where(Rating.user_uid == users[1].uid, Rating.soup_id == soup_id)).all()) == 1
        soup = session.get(Soup, soup_id)
        assert (soup.like_count, soup.favorite_count, soup.rating_count, soup.avg_rating) == (1, 1, 1, 9)
