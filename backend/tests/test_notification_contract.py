from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import notifications
from app.api.auth import get_current_active_user
from app.models.database import Notification, NotificationType, User, UserStatus, get_db


def _client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="notice-user", nickname="通知用户", email="notice@example.com", hashed_password="unused", status=UserStatus.ACTIVE)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.add(Notification(recipient_uid=user.uid, notification_type=NotificationType.SYSTEM, title="系统通知", content="内容"))
        session.commit()
        uid = user.uid

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
    return TestClient(app), uid


def test_notification_list_and_mark_read_use_recipient_uid():
    client, uid = _client()
    listed = client.get("/api/notifications")
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["recipient_uid"] == uid
    assert item["is_read"] is False

    updated = client.put(f"/api/notifications/{item['id']}/read")
    assert updated.status_code == 200
    assert updated.json()["is_read"] is True
