from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.models.database import CompetitionEntry, Favorite, Like, Soup, User
from app.schemas.common import ApiError, PageResponse


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_common_page_schema_and_api_error_use_fastapi_contract():
    page = PageResponse[int](items=[1], total=1, page=1, page_size=20, total_pages=1)
    error = ApiError(code="INVALID", message="参数错误")

    assert page.model_dump() == {
        "items": [1],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }
    assert error.model_dump() == {"code": "INVALID", "message": "参数错误"}


def test_interaction_and_competition_entry_tables_have_unique_constraints():
    engine = _engine()
    SQLModel.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())
    assert {"likes", "favorites", "competition_entries"} <= table_names

    with Session(engine) as session:
        user = User(
            username="foundation-user",
            nickname="基础用户",
            email="foundation@example.com",
            hashed_password="not-used",
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
        session.add(soup)
        session.commit()
        session.refresh(soup)
        session.add(Like(user_uid=user.uid, target_type="soup", target_id=soup.id))
        session.commit()
        session.add(Like(user_uid=user.uid, target_type="soup", target_id=soup.id))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        else:
            raise AssertionError("duplicate likes must be rejected")


def test_health_endpoint_reports_dependency_state_without_failing():
    from app.main import app

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert "dependencies" in body
    assert "redis" in body["dependencies"]
