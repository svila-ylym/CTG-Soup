from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import achievements, messages, posts, search, social
from app.api.auth import get_current_active_user, get_current_root_user
from app.models.database import (
    Achievement,
    AchievementConditionType,
    Post,
    Soup,
    User,
    UserAchievement,
    UserRole,
    UserStatus,
    get_db,
)


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        root = User(
            username="community-root",
            nickname="管理员",
            email="community-root@example.com",
            hashed_password="not-used",
            role=UserRole.ROOT,
            status=UserStatus.ACTIVE,
        )
        other = User(
            username="community-user",
            nickname="用户",
            email="community-user@example.com",
            hashed_password="not-used",
            status=UserStatus.ACTIVE,
        )
        session.add_all([root, other])
        session.commit()
        session.refresh(root)
        session.refresh(other)
        post = Post(author_uid=other.uid, title="契约帖子", content="正文")
        soup = Soup(
            author_uid=other.uid,
            title="可搜索汤",
            puzzle="搜索谜面",
            solution="答案",
            genre="本格",
            soup_color="清汤",
            main_player_count=1,
        )
        achievement = Achievement(
            code="FIRST_POST",
            name="初次发帖",
            description="发布第一篇帖子",
            condition_type=AchievementConditionType.POST_COUNT,
            condition_params={"count": 1},
        )
        session.add_all([post, soup, achievement])
        session.commit()
        session.refresh(achievement)
        user_achievement = UserAchievement(
            user_uid=root.uid,
            achievement_id=achievement.id,
            current_value=1,
            is_achieved=True,
        )
        session.add(user_achievement)
        session.commit()
        ids = root.uid, other.uid

    app = FastAPI()
    app.include_router(posts.router, prefix="/api/posts")
    app.include_router(social.router, prefix="/api/social")
    app.include_router(messages.router, prefix="/api/messages")
    app.include_router(achievements.router, prefix="/api/achievements")
    app.include_router(search.router, prefix="/api/search")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_user():
        with Session(engine) as session:
            return session.get(User, ids[0])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user
    app.dependency_overrides[get_current_root_user] = override_user
    return TestClient(app, raise_server_exceptions=False), ids


def test_posts_are_public_and_use_author_uid():
    client, ids = _setup()
    created = client.post(
        "/api/posts",
        json={"title": "新帖子", "content": "内容", "section": "general"},
    )
    assert created.status_code == 201
    assert created.json()["author_uid"] == ids[0]
    assert "author_id" not in created.json()

    listed = client.get("/api/posts")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["author_uid"] == ids[0]


def test_follow_and_blacklist_use_uid_pairs_idempotently():
    client, ids = _setup()
    first = client.post("/api/social/follow", json={"target_uid": ids[1]})
    second = client.post("/api/social/follow", json={"target_uid": ids[1]})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["follower_uid"] == ids[0]
    assert first.json()["followed_uid"] == ids[1]

    blocked = client.post("/api/social/blacklist", json={"target_uid": ids[1]})
    assert blocked.status_code == 200
    assert blocked.json()["blocker_uid"] == ids[0]
    assert blocked.json()["blocked_uid"] == ids[1]


def test_messages_use_sender_and_receiver_uid_and_enforce_blacklist():
    client, ids = _setup()
    sent = client.post(
        "/api/messages",
        json={"receiver_uid": ids[1], "content": "你好"},
    )
    assert sent.status_code == 201
    assert sent.json()["sender_uid"] == ids[0]
    assert sent.json()["receiver_uid"] == ids[1]
    assert "sender_id" not in sent.json()

    client.post("/api/social/blacklist", json={"target_uid": ids[1]})
    # The current user blocked the receiver; sending in either blocked direction is rejected.
    rejected = client.post(
        "/api/messages",
        json={"receiver_uid": ids[1], "content": "不能发送"},
    )
    assert rejected.status_code == 403


def test_achievement_contract_uses_canonical_state_fields():
    client, ids = _setup()
    mine = client.get("/api/achievements/my")
    assert mine.status_code == 200
    item = mine.json()["items"][0]
    assert item["user_uid"] == ids[0]
    assert item["is_achieved"] is True
    assert "is_completed" not in item


def test_search_returns_canonical_paged_results():
    client, ids = _setup()
    users = client.get("/api/search/users", params={"q": "community-user"})
    posts_result = client.get("/api/search/posts", params={"q": "契约"})
    soups_result = client.get("/api/search/turtle-soups", params={"q": "搜索"})
    assert users.status_code == posts_result.status_code == soups_result.status_code == 200
    assert users.json()["items"][0]["uid"] == ids[1]
    assert posts_result.json()["items"][0]["author_uid"] == ids[1]
    assert soups_result.json()["items"][0]["author_uid"] == ids[1]
    assert soups_result.json()["items"][0]["average_score"] == 0
