from copy import deepcopy
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import surveys
from app.api.auth import get_current_active_user
from app.models.database import get_db
from app.models.models import (
    Survey,
    SurveyQuestion,
    SurveyQuestionType,
    SurveyResponse,
    SurveyStatus,
    User,
    UserRole,
    UserStatus,
)


def _test_context(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin = User(
            username="survey-admin",
            nickname="问卷管理员",
            email="survey-admin@example.com",
            hashed_password="x",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        first = User(
            username="survey-first",
            nickname="用户一",
            email="survey-first@example.com",
            hashed_password="x",
            status=UserStatus.ACTIVE,
        )
        second = User(
            username="survey-second",
            nickname="用户二",
            email="survey-second@example.com",
            hashed_password="x",
            status=UserStatus.ACTIVE,
        )
        session.add_all([admin, first, second])
        session.commit()
        session.refresh(admin)
        session.refresh(first)
        session.refresh(second)

        active = Survey(
            author_uid=admin.uid,
            title="社区体验调查",
            status=SurveyStatus.ACTIVE,
            starts_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() + timedelta(days=1),
        )
        draft = Survey(
            author_uid=admin.uid,
            title="内部草稿",
            status=SurveyStatus.DRAFT,
        )
        session.add_all([active, draft])
        session.commit()
        session.refresh(active)
        session.refresh(draft)
        session.add_all([
            SurveyQuestion(
                survey_id=active.id,
                question_text="第一题",
                question_type=SurveyQuestionType.TEXT,
                sort_order=0,
            ),
            SurveyQuestion(
                survey_id=active.id,
                question_text="第二题",
                question_type=SurveyQuestionType.RATING,
                sort_order=1,
            ),
            SurveyResponse(survey_id=active.id, user_uid=first.uid),
        ])
        session.commit()
        ids = {
            "admin": admin.uid,
            "first": first.uid,
            "second": second.uid,
            "active": active.id,
            "draft": draft.id,
        }

    current = {"uid": ids["first"]}
    cache_state = {
        "values": {},
        "sets": [],
        "deletes": [],
        "pattern_deletes": [],
    }

    def cache_get(key):
        value = cache_state["values"].get(key)
        return deepcopy(value)

    def cache_set(key, value, ttl=None):
        cache_state["sets"].append((key, ttl))
        cache_state["values"][key] = deepcopy(value)
        return True

    def cache_delete(key):
        cache_state["deletes"].append(key)
        cache_state["values"].pop(key, None)
        return True

    def cache_delete_pattern(pattern):
        cache_state["pattern_deletes"].append(pattern)
        prefix = pattern.removesuffix("*")
        for key in list(cache_state["values"]):
            if key.startswith(prefix):
                cache_state["values"].pop(key)
        return True

    monkeypatch.setattr(surveys, "cache_get", cache_get)
    monkeypatch.setattr(surveys, "cache_set", cache_set)
    monkeypatch.setattr(surveys, "cache_delete", cache_delete)
    monkeypatch.setattr(surveys, "cache_delete_pattern", cache_delete_pattern)

    def override_db():
        with Session(engine) as session:
            yield session

    def override_user():
        with Session(engine) as session:
            return session.get(User, current["uid"])

    app = FastAPI()
    app.include_router(surveys.router, prefix="/api/surveys")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user
    return TestClient(app), engine, ids, current, cache_state


def test_list_returns_real_counts_without_n_plus_one(monkeypatch):
    client, engine, ids, _, cache_state = _test_context(monkeypatch)
    statements = []

    def count_selects(conn, cursor, statement, parameters, context, executemany):
        normalized = statement.lstrip().upper()
        if normalized.startswith("SELECT") and "FROM USERS" not in normalized:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count_selects)
    response = client.get("/api/surveys")
    assert response.status_code == 200
    assert response.json()["items"][0]["question_count"] == 2
    assert response.json()["items"][0]["response_count"] == 1
    first_query_count = len(statements)

    with Session(engine) as session:
        second_survey = Survey(
            author_uid=ids["admin"],
            title="第二份公开问卷",
            status=SurveyStatus.ACTIVE,
        )
        session.add(second_survey)
        session.commit()
    cache_state["values"].clear()
    statements.clear()

    response = client.get("/api/surveys")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert len(statements) == first_query_count == 2


def test_list_cache_separates_public_and_manager_views(monkeypatch):
    client, _, ids, current, cache_state = _test_context(monkeypatch)

    public = client.get("/api/surveys", params={"status": "all"})
    assert [item["title"] for item in public.json()["items"]] == ["社区体验调查"]

    current["uid"] = ids["admin"]
    manager = client.get("/api/surveys", params={"status": "all"})
    assert {item["title"] for item in manager.json()["items"]} == {
        "社区体验调查",
        "内部草稿",
    }
    assert len({key for key, _ in cache_state["sets"]}) == 2


def test_detail_cache_keeps_submission_state_per_user(monkeypatch):
    client, _, ids, current, cache_state = _test_context(monkeypatch)
    detail_url = f"/api/surveys/{ids['active']}"

    first = client.get(detail_url)
    assert first.status_code == 200
    assert first.json()["has_submitted"] is True

    current["uid"] = ids["second"]
    second = client.get(detail_url)
    assert second.status_code == 200
    assert second.json()["has_submitted"] is False
    detail_key = surveys._survey_detail_cache_key(ids["active"])
    assert [key for key, _ in cache_state["sets"]].count(detail_key) == 1


def test_create_update_and_submit_invalidate_expected_keys(monkeypatch):
    client, _, ids, current, cache_state = _test_context(monkeypatch)
    current["uid"] = ids["admin"]
    created = client.post(
        "/api/surveys",
        json={
            "title": "新发布问卷",
            "status": "active",
            "questions": [{
                "question_text": "意见",
                "question_type": "text",
                "required": True,
                "sort_order": 0,
            }],
        },
    )
    assert created.status_code == 200
    survey_id = created.json()["id"]
    question_id = created.json()["questions"][0]["id"]
    assert surveys.SURVEY_LIST_CACHE_PATTERN in cache_state["pattern_deletes"]
    assert surveys._survey_detail_cache_key(survey_id) in cache_state["deletes"]

    cache_state["pattern_deletes"].clear()
    cache_state["deletes"].clear()
    updated = client.put(f"/api/surveys/{survey_id}", json={"title": "已更新问卷"})
    assert updated.status_code == 200
    assert surveys.SURVEY_LIST_CACHE_PATTERN in cache_state["pattern_deletes"]
    assert surveys._survey_detail_cache_key(survey_id) in cache_state["deletes"]

    cache_state["pattern_deletes"].clear()
    current["uid"] = ids["second"]
    submitted = client.post(
        f"/api/surveys/{survey_id}/submit",
        json={"answers": [{"question_id": question_id, "answer_text": "很好"}]},
    )
    assert submitted.status_code == 200
    assert cache_state["pattern_deletes"] == [surveys.SURVEY_LIST_CACHE_PATTERN]


def test_statistics_returns_actual_response_count(monkeypatch):
    client, engine, ids, current, _ = _test_context(monkeypatch)
    with Session(engine) as session:
        session.add(SurveyResponse(survey_id=ids["active"], user_uid=ids["second"]))
        session.commit()
    current["uid"] = ids["admin"]

    response = client.get(f"/api/surveys/{ids['active']}/statistics")

    assert response.status_code == 200
    assert response.json()["total_responses"] == 2
