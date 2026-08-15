from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import notifications
from app.api.auth import get_current_active_user
from app.models.database import Notification, NotificationType, User, UserStatus, get_db


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="notice-user", nickname="通知用户", email="notice@example.com", hashed_password="unused", status=UserStatus.ACTIVE)
        other = User(username="other-notice-user", nickname="其他用户", email="other-notice@example.com", hashed_password="unused", status=UserStatus.ACTIVE)
        session.add_all([user, other])
        session.commit()
        session.refresh(user)
        session.refresh(other)
        session.add_all([
            Notification(recipient_uid=user.uid, notification_type=NotificationType.SYSTEM, title="系统通知", content="内容"),
            Notification(recipient_uid=user.uid, notification_type=NotificationType.SYSTEM, title="第二条通知", content="内容"),
            Notification(recipient_uid=other.uid, notification_type=NotificationType.SYSTEM, title="其他用户通知", content="内容"),
        ])
        session.commit()
        uid = user.uid
        other_uid = other.uid

    app = FastAPI()
    app.include_router(notifications.router, prefix="/api/notifications")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_user():
        with Session(engine) as session:
            return session.get(User, uid)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user
    return TestClient(app), uid, other_uid, engine


def test_notification_list_and_mark_read_use_recipient_uid():
    client, uid, _, _ = _client()
    listed = client.get("/api/notifications")
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["recipient_uid"] == uid
    assert item["is_read"] is False

    updated = client.put(f"/api/notifications/{item['id']}/read")
    assert updated.status_code == 200
    assert updated.json()["is_read"] is True


def test_mark_all_notifications_read_is_scoped_and_idempotent():
    client, uid, other_uid, engine = _client()

    updated = client.put("/api/notifications/read-all")
    repeated = client.put("/api/notifications/read-all")

    assert updated.status_code == 200
    assert updated.json() == {"updated_count": 2}
    assert repeated.status_code == 200
    assert repeated.json() == {"updated_count": 0}
    assert client.get("/api/notifications", params={"unread_only": True}).json()["total"] == 0
    with Session(engine) as session:
        current_rows = session.exec(
            select(Notification).where(Notification.recipient_uid == uid)
        ).all()
        other_rows = session.exec(
            select(Notification).where(Notification.recipient_uid == other_uid)
        ).all()
        assert all(item.is_read for item in current_rows)
        assert len(other_rows) == 1
        assert other_rows[0].is_read is False
