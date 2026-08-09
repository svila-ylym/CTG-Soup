from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import users
from app.api.auth import get_current_active_user
from app.models.database import User, UserRole, UserStatus, get_db


def _test_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        current_user = User(
            uid=42,
            username="route-user",
            nickname="路由用户",
            email="route@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        session.add(current_user)
        session.commit()
        session.refresh(current_user)

    app = FastAPI()
    app.include_router(users.router, prefix="/api/users")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_current_user():
        with Session(engine) as session:
            return session.get(User, 42)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_current_user
    return TestClient(app)


def test_me_route_is_not_captured_by_dynamic_user_route():
    response = _test_client().get("/api/users/me")

    assert response.status_code == 200
    assert response.json()["uid"] == 42


def test_public_user_route_uses_explicit_uid_prefix():
    client = _test_client()

    assert client.get("/api/users/uid/42").status_code == 200
    assert client.get("/api/users/42").status_code == 404
