from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import turtle_soups
from app.models.database import Soup, User, UserRole, UserStatus, get_db


def _test_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        author = User(
            username="author",
            nickname="作者",
            email="author@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        session.add(author)
        session.commit()
        session.refresh(author)
        soup = Soup(
            author_uid=author.uid,
            title="密室",
            puzzle="门从里面锁着。",
            solution="凶手从窗户离开。",
            status="published",
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        soup_id = soup.id

    app = FastAPI()
    app.include_router(turtle_soups.router, prefix="/api/turtle-soups")

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    return app, soup_id


def test_anonymous_can_read_public_soup_without_solution():
    app, soup_id = _test_app()

    response = TestClient(app).get(f"/api/turtle-soups/{soup_id}")

    assert response.status_code == 200
    assert response.json()["solution"] is None


def test_anonymous_can_reveal_published_soup_solution_on_demand():
    app, soup_id = _test_app()

    response = TestClient(app).get(
        f"/api/turtle-soups/{soup_id}",
        params={"reveal": "true"},
    )

    assert response.status_code == 200
    assert response.json()["solution"] == "凶手从窗户离开。"
