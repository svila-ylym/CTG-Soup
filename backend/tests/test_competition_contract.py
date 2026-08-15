from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import competitions
from app.api.auth import get_current_active_user, get_current_admin_user
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Soup,
    SoupTag,
    Tag,
    TagKind,
    TagStatus,
    User,
    UserRole,
    UserStatus,
    UploadedAsset,
    get_db,
)
from app.services.competition_entries import (
    competition_colors_for_soups,
    evaluate_soup_competitions,
    refresh_soup_competition_scores,
)


def _setup():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        admin = User(
            username="competition-admin",
            nickname="管理员",
            email="competition-admin@example.com",
            hashed_password="not-used",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        author = User(
            username="competition-author",
            nickname="作者",
            email="competition-author@example.com",
            hashed_password="not-used",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        tag = Tag(slug="原创", name="原创", kind=TagKind.SYSTEM, status=TagStatus.ACTIVE)
        disabled = Tag(slug="停用", name="停用", kind=TagKind.SYSTEM, status=TagStatus.DISABLED)
        session.add_all([admin, author, tag, disabled])
        session.commit()
        session.refresh(admin)
        session.refresh(author)
        session.refresh(tag)
        session.refresh(disabled)
        now = datetime.utcnow()
        soup = Soup(
            author_uid=author.uid,
            title="参赛作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count=1,
            secondary_player_count=0,
            created_at=now,
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        session.add(SoupTag(soup_id=soup.id, tag_id=tag.id))
        competition = Competition(
            creator_uid=admin.uid,
            name="原创赛",
            description="比赛",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            required_tag_ids=[tag.id],
            status=CompetitionStatus.ONGOING,
        )
        session.add(competition)
        session.commit()
        session.refresh(competition)
        ids = admin.uid, author.uid, tag.id, disabled.id, soup.id, competition.id

    app = FastAPI()
    app.include_router(competitions.router, prefix="/api/competitions")

    def override_db():
        with Session(engine) as session:
            yield session

    async def override_admin():
        with Session(engine) as session:
            return session.get(User, ids[0])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_admin_user] = override_admin
    app.dependency_overrides[get_current_active_user] = override_admin
    return TestClient(app), engine, ids


def test_create_competition_uses_canonical_creator_and_required_tag_ids():
    client, _, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "新赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[2]],
            "score_type": "average",
            "top_n": 10,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["creator_uid"] == ids[0]
    assert payload["required_tag_ids"] == [ids[2]]
    assert "creator_id" not in payload
    assert "entry_tags" not in payload


def test_competition_cover_is_owned_controlled_preserved_and_removable():
    client, engine, ids = _setup()
    with Session(engine) as session:
        owned = UploadedAsset(
            owner_uid=ids[0],
            kind="image",
            storage_key="images/admin/cover.webp",
            public_url="/storage/images/admin/cover.webp",
            mime_type="image/webp",
            size=1024,
        )
        foreign = UploadedAsset(
            owner_uid=ids[1],
            kind="image",
            storage_key="images/author/cover.webp",
            public_url="/storage/images/author/cover.webp",
            mime_type="image/webp",
            size=2048,
        )
        session.add_all([owned, foreign])
        session.commit()
        session.refresh(owned)
        session.refresh(foreign)
        owned_id = owned.id
        foreign_id = foreign.id

    now = datetime.now(timezone.utc)
    create_payload = {
        "name": "封面比赛",
        "description": "带封面的比赛",
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": (now + timedelta(hours=1)).isoformat(),
        "required_tag_ids": [ids[2]],
        "cover_asset_id": owned_id,
        "custom_page_config": {
            "cover_url": "https://attacker.invalid/spoof.webp",
        },
    }
    created = client.post("/api/competitions", json=create_payload)

    assert created.status_code == 201
    assert created.json()["cover_asset_id"] == owned_id
    assert created.json()["cover_url"] == "/storage/images/admin/cover.webp"
    assert created.json()["custom_page_config"]["cover_url"] == "/storage/images/admin/cover.webp"

    competition_id = created.json()["id"]
    update_payload = {
        "name": "保留封面的比赛",
        "description": "旧客户端没有发送封面字段",
        "start_time": (now - timedelta(hours=1)).isoformat(),
        "end_time": (now + timedelta(hours=2)).isoformat(),
        "required_tag_ids": [ids[2]],
        "custom_page_config": {"cover_url": "https://attacker.invalid/replaced.webp"},
    }
    preserved = client.put(f"/api/competitions/{competition_id}", json=update_payload)
    assert preserved.status_code == 200
    assert preserved.json()["cover_asset_id"] == owned_id
    assert preserved.json()["cover_url"] == "/storage/images/admin/cover.webp"

    removed = client.put(
        f"/api/competitions/{competition_id}",
        json={**update_payload, "cover_asset_id": None},
    )
    assert removed.status_code == 200
    assert removed.json()["cover_asset_id"] is None
    assert removed.json()["cover_url"] is None
    assert "cover_url" not in removed.json()["custom_page_config"]

    rejected = client.post(
        "/api/competitions",
        json={**create_payload, "name": "越权封面", "cover_asset_id": foreign_id},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "比赛封面必须使用本人上传的图片"


def test_create_competition_creates_global_custom_keyword():
    client, engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "夏夜赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": ["  夏夜   推理  "],
        },
    )

    assert response.status_code == 201
    with Session(engine) as session:
        tag = session.exec(select(Tag).where(Tag.slug == "夏夜-推理")).one()
        assert tag.kind == TagKind.CUSTOM
        assert tag.status == TagStatus.ACTIVE
        assert response.json()["required_tag_ids"] == [tag.id]


def test_create_competition_reuses_keyword_selected_by_id_and_name():
    client, engine, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "复用标签赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[2]],
            "custom_tags": [" 原创 "],
        },
    )

    assert response.status_code == 201
    assert response.json()["required_tag_ids"] == [ids[2]]
    with Session(engine) as session:
        assert len(session.exec(select(Tag).where(Tag.slug == "原创")).all()) == 1


def test_create_competition_rejects_more_than_ten_unique_keywords():
    client, _engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "关键词过多",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": [f"关键词 {index}" for index in range(11)],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "TOO_MANY_TAGS"


def test_create_competition_rolls_back_new_keyword_when_later_name_is_invalid():
    client, engine, _ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "回滚标签赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [],
            "custom_tags": ["临时关键词", "危险<script>"],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_TAG_NAME"
    with Session(engine) as session:
        assert session.exec(select(Tag).where(Tag.slug == "临时关键词")).first() is None


def test_competition_entry_is_created_once_for_matching_soup():
    _, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        first = evaluate_soup_competitions(session, soup)
        second = evaluate_soup_competitions(session, soup)
        assert len(first) == 1
        assert second == first
        entries = session.exec(select(CompetitionEntry)).all()
        assert len(entries) == 1


def test_settled_competition_does_not_accept_new_entries():
    _, engine, ids = _setup()
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.status = CompetitionStatus.COMPLETED
        competition.settled_at = datetime.utcnow()
        soup = session.get(Soup, ids[4])
        assert evaluate_soup_competitions(session, soup) == []


def test_non_matching_and_out_of_range_soups_are_not_entered():
    _, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        competition = session.get(Competition, ids[5])
        competition.required_tag_ids = [ids[3]]
        assert evaluate_soup_competitions(session, soup) == []

        competition.required_tag_ids = [ids[2]]
        competition.start_time = soup.created_at + timedelta(minutes=1)
        competition.end_time = soup.created_at + timedelta(hours=1)
        assert evaluate_soup_competitions(session, soup) == []


def test_create_competition_rejects_disabled_tag():
    client, _, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "无效比赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[3]],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "COMPETITION_TAG_NOT_ACTIVE"


def test_settlement_snapshot_is_stable():
    client, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        evaluate_soup_competitions(session, soup)
        competition = session.get(Competition, ids[5])
        competition.end_time = datetime.utcnow() - timedelta(minutes=1)
        session.commit()

    first = client.post(f"/api/competitions/{ids[5]}/settle")
    second = client.post(f"/api/competitions/{ids[5]}/settle")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["result_snapshot"] == second.json()["result_snapshot"]


def test_ongoing_competition_cannot_be_settled_early():
    client, _, ids = _setup()
    response = client.post(f"/api/competitions/{ids[5]}/settle")
    assert response.status_code == 409


def test_competition_creator_can_settle_without_admin_role():
    client, engine, ids = _setup()
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.creator_uid = ids[1]
        competition.end_time = datetime.utcnow() - timedelta(minutes=1)
        session.commit()

    async def override_creator():
        with Session(engine) as session:
            return session.get(User, ids[1])

    client.app.dependency_overrides[get_current_active_user] = override_creator
    response = client.post(f"/api/competitions/{ids[5]}/settle")

    assert response.status_code == 200
    assert response.json()["settled_at"] is not None


def test_create_competition_accepts_timezone_aware_range():
    client, _, ids = _setup()
    now = datetime.now(timezone.utc)
    response = client.post(
        "/api/competitions",
        json={
            "name": "时区比赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ongoing"


def test_create_ongoing_competition_collects_existing_matching_soup():
    client, engine, ids = _setup()
    now = datetime.now(timezone.utc)

    response = client.post(
        "/api/competitions",
        json={
            "name": "自动收录赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    assert response.status_code == 201
    assert [entry["soup_id"] for entry in response.json()["entries"]] == [ids[4]]
    with Session(engine) as session:
        entries = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == response.json()["id"]
            )
        ).all()
        assert [entry.soup_id for entry in entries] == [ids[4]]


def test_create_completed_competition_collects_historical_matching_soup():
    client, engine, ids = _setup()
    now = datetime.utcnow()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.created_at = now - timedelta(hours=2)
        session.commit()

    response = client.post(
        "/api/competitions",
        json={
            "name": "历史自动收录赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=3)).replace(
                tzinfo=timezone.utc
            ).isoformat(),
            "end_time": (now - timedelta(hours=1)).replace(
                tzinfo=timezone.utc
            ).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "completed"
    assert response.json()["settled_at"] is None
    assert [entry["soup_id"] for entry in response.json()["entries"]] == [ids[4]]


def test_competition_entry_score_tracks_average_until_settlement():
    client, engine, ids = _setup()
    now = datetime.now(timezone.utc)
    created = client.post(
        "/api/competitions",
        json={
            "name": "平均分同步赛",
            "description": "说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
        },
    )

    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.avg_rating = 8.5
        refresh_soup_competition_scores(session, soup)
        session.commit()
        entry = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == created.json()["id"]
            )
        ).one()
        assert entry.final_score == 8.5


def test_unranked_entries_are_frozen_after_settlement():
    client, engine, ids = _setup()
    with Session(engine) as session:
        reference_time = datetime.utcnow()
        first = session.get(Soup, ids[4])
        first.avg_rating = 9.0
        first.created_at = reference_time - timedelta(minutes=30)
        second = Soup(
            author_uid=ids[1],
            title="第二份参赛作品",
            puzzle="谜面",
            solution="汤底",
            avg_rating=5.0,
            created_at=reference_time - timedelta(minutes=30),
        )
        session.add(second)
        session.flush()
        session.add(SoupTag(soup_id=second.id, tag_id=ids[2]))
        competition = session.get(Competition, ids[5])
        competition.top_n = 1
        competition.end_time = reference_time - timedelta(minutes=1)
        session.flush()
        evaluate_soup_competitions(session, first)
        evaluate_soup_competitions(session, second)
        second_id = second.id

    settled = client.post(f"/api/competitions/{ids[5]}/settle")
    assert settled.status_code == 200

    with Session(engine) as session:
        second = session.get(Soup, second_id)
        second.avg_rating = 10.0
        refresh_soup_competition_scores(session, second)
        session.commit()
        entry = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == ids[5],
                CompetitionEntry.soup_id == second_id,
            )
        ).one()
        assert entry.rank is None
        assert entry.final_score == 5.0


def test_competition_requires_every_required_tag_and_reconciles_removal():
    _, engine, ids = _setup()
    with Session(engine) as session:
        second_required = Tag(
            slug="第二必选",
            name="第二必选",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add(second_required)
        session.flush()
        competition = session.get(Competition, ids[5])
        competition.required_tag_ids = [ids[2], second_required.id]
        soup = session.get(Soup, ids[4])

        assert evaluate_soup_competitions(session, soup) == []

        relation = SoupTag(soup_id=soup.id, tag_id=second_required.id)
        session.add(relation)
        session.flush()
        assert len(evaluate_soup_competitions(session, soup)) == 1

        session.delete(session.get(SoupTag, (soup.id, second_required.id)))
        session.flush()
        assert evaluate_soup_competitions(session, soup) == []
        assert session.exec(select(CompetitionEntry)).all() == []


def test_optional_tags_build_independent_rankings_with_oldest_tie_first():
    client, engine, ids = _setup()
    with Session(engine) as session:
        optional_one = Tag(
            slug="可选一",
            name="可选一",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        optional_two = Tag(
            slug="可选二",
            name="可选二",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add_all([optional_one, optional_two])
        session.flush()
        newer = session.get(Soup, ids[4])
        newer.avg_rating = 8.0
        older = Soup(
            author_uid=ids[1],
            title="更早发布",
            puzzle="谜面",
            solution="汤底",
            avg_rating=8.0,
            created_at=newer.created_at - timedelta(minutes=5),
        )
        session.add(older)
        session.flush()
        session.add_all([
            SoupTag(soup_id=newer.id, tag_id=optional_one.id),
            SoupTag(soup_id=newer.id, tag_id=optional_two.id),
            SoupTag(soup_id=older.id, tag_id=ids[2]),
            SoupTag(soup_id=older.id, tag_id=optional_one.id),
        ])
        competition = session.get(Competition, ids[5])
        competition.optional_tag_ids = [optional_one.id, optional_two.id]
        competition.competition_color = "#12AB34"
        session.flush()
        evaluate_soup_competitions(session, newer)
        evaluate_soup_competitions(session, older)
        optional_one_id = optional_one.id
        optional_two_id = optional_two.id
        older_id = older.id

    response = client.get(f"/api/competitions/{ids[5]}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["optional_tag_ids"] == [optional_one_id, optional_two_id]
    assert payload["competition_color"] == "#12AB34"
    assert [entry["soup_id"] for entry in payload["rankings"]["total"]] == [
        older_id,
        ids[4],
    ]
    assert [entry["soup_title"] for entry in payload["rankings"]["total"]] == [
        "更早发布",
        "参赛作品",
    ]
    assert {entry["soup_title"] for entry in payload["entries"]} == {
        "更早发布",
        "参赛作品",
    }
    groups = {group["tag_id"]: group for group in payload["rankings"]["groups"]}
    assert [entry["soup_id"] for entry in groups[optional_one_id]["entries"]] == [
        older_id,
        ids[4],
    ]
    assert [entry["soup_id"] for entry in groups[optional_two_id]["entries"]] == [
        ids[4],
    ]

    with Session(engine) as session:
        assert competition_colors_for_soups(session, [ids[4], older_id]) == {
            ids[4]: ["#12AB34"],
            older_id: ["#12AB34"],
        }


def test_create_competition_resolves_optional_custom_tag_and_normalizes_color():
    client, engine, ids = _setup()
    response = client.post(
        "/api/competitions",
        json={
            "name": "分组赛",
            "description": "说明",
            "start_time": "2026-08-08T00:00:00",
            "end_time": "2026-08-09T00:00:00",
            "required_tag_ids": [ids[2]],
            "optional_custom_tags": ["支线谜题"],
            "competition_color": "#abcdef",
        },
    )

    assert response.status_code == 201
    assert response.json()["competition_color"] == "#ABCDEF"
    with Session(engine) as session:
        optional = session.exec(select(Tag).where(Tag.slug == "支线谜题")).one()
        assert response.json()["optional_tag_ids"] == [optional.id]


def test_competition_detail_returns_required_tag_names():
    client, _engine, ids = _setup()

    response = client.get(f"/api/competitions/{ids[5]}")

    assert response.status_code == 200
    assert response.json()["required_tags"] == [
        {"id": ids[2], "name": "原创"},
    ]


def test_competition_rejects_custom_role_conflict_invalid_color_and_tag_limit():
    client, _engine, ids = _setup()
    base_payload = {
        "name": "输入校验赛",
        "description": "说明",
        "start_time": "2026-08-08T00:00:00",
        "end_time": "2026-08-09T00:00:00",
        "required_tag_ids": [ids[2]],
    }

    conflict = client.post(
        "/api/competitions",
        json={
            **base_payload,
            "required_tag_ids": [],
            "custom_tags": ["同名标签"],
            "optional_custom_tags": [" 同名标签 "],
        },
    )
    invalid_color = client.post(
        "/api/competitions",
        json={**base_payload, "competition_color": "blue"},
    )
    too_many_optional = client.post(
        "/api/competitions",
        json={
            **base_payload,
            "optional_custom_tags": [f"可选标签 {index}" for index in range(11)],
        },
    )

    assert conflict.status_code == 422
    assert conflict.json()["detail"]["code"] == "COMPETITION_TAG_ROLE_CONFLICT"
    assert invalid_color.status_code == 422
    assert too_many_optional.status_code == 422
    assert too_many_optional.json()["detail"]["code"] == "TOO_MANY_TAGS"


def test_edit_competition_rebuilds_membership():
    client, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        evaluate_soup_competitions(session, soup)
        replacement = Tag(
            slug="替代必选",
            name="替代必选",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add(replacement)
        session.commit()
        session.refresh(replacement)
        replacement_id = replacement.id

    now = datetime.now(timezone.utc)
    response = client.put(
        f"/api/competitions/{ids[5]}",
        json={
            "name": "修改后的比赛",
            "description": "修改后的说明",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [replacement_id],
            "competition_color": "#13579B",
        },
    )

    assert response.status_code == 200
    assert response.json()["entries"] == []
    with Session(engine) as session:
        assert session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == ids[5]
            )
        ).all() == []


def test_legacy_edit_preserves_optional_groups_and_competition_color():
    client, engine, ids = _setup()
    with Session(engine) as session:
        optional = Tag(
            slug="兼容分组",
            name="兼容分组",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add(optional)
        session.flush()
        competition = session.get(Competition, ids[5])
        competition.optional_tag_ids = [optional.id]
        competition.competition_color = "#654321"
        session.commit()
        optional_id = optional.id

    now = datetime.now(timezone.utc)
    response = client.put(
        f"/api/competitions/{ids[5]}",
        json={
            "name": "旧客户端修改",
            "description": "仍然兼容",
            "start_time": (now - timedelta(hours=1)).isoformat(),
            "end_time": (now + timedelta(hours=1)).isoformat(),
            "required_tag_ids": [ids[2]],
            "score_type": "average",
            "top_n": 10,
            "custom_page_config": {},
        },
    )

    assert response.status_code == 200
    assert response.json()["optional_tag_ids"] == [optional_id]
    assert response.json()["competition_color"] == "#654321"


def test_settlement_freezes_optional_groups_and_live_scores():
    client, engine, ids = _setup()
    with Session(engine) as session:
        optional = Tag(
            slug="冻结分组",
            name="冻结分组",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add(optional)
        session.flush()
        soup = session.get(Soup, ids[4])
        soup.avg_rating = 6.5
        session.add(SoupTag(soup_id=soup.id, tag_id=optional.id))
        competition = session.get(Competition, ids[5])
        competition.optional_tag_ids = [optional.id]
        session.flush()
        evaluate_soup_competitions(session, soup)
        optional_id = optional.id

    live = client.get(f"/api/competitions/{ids[5]}").json()["rankings"]
    assert live["total"][0]["final_score"] == 6.5
    assert live["groups"][0]["entries"][0]["soup_id"] == ids[4]

    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        competition.end_time = datetime.utcnow() - timedelta(minutes=1)
        session.commit()
    settled = client.post(f"/api/competitions/{ids[5]}/settle")
    assert settled.status_code == 200

    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.avg_rating = 9.5
        session.delete(session.get(SoupTag, (ids[4], optional_id)))
        session.commit()

    frozen = client.get(f"/api/competitions/{ids[5]}").json()["rankings"]
    assert frozen == settled.json()["rankings"]
    assert frozen["total"][0]["final_score"] == 6.5
    assert frozen["groups"][0]["entries"][0]["soup_id"] == ids[4]


def test_competition_colors_are_ordered_deduplicated_and_removed_on_delete():
    client, engine, ids = _setup()
    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        first = session.get(Competition, ids[5])
        first.competition_color = "#abcdef"
        first.start_time = soup.created_at - timedelta(hours=2)
        second = Competition(
            creator_uid=ids[0],
            name="同色比赛",
            description="比赛",
            start_time=soup.created_at - timedelta(hours=1),
            end_time=soup.created_at + timedelta(hours=1),
            required_tag_ids=[ids[2]],
            competition_color="#ABCDEF",
            status=CompetitionStatus.ONGOING,
        )
        third = Competition(
            creator_uid=ids[0],
            name="第二颜色比赛",
            description="比赛",
            start_time=soup.created_at - timedelta(minutes=30),
            end_time=soup.created_at + timedelta(hours=1),
            required_tag_ids=[ids[2]],
            competition_color="#123456",
            status=CompetitionStatus.ONGOING,
        )
        session.add_all([second, third])
        session.flush()
        session.add_all([
            CompetitionEntry(
                competition_id=first.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
            ),
            CompetitionEntry(
                competition_id=second.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
            ),
            CompetitionEntry(
                competition_id=third.id,
                soup_id=soup.id,
                author_uid=soup.author_uid,
            ),
        ])
        session.commit()
        second_id = second.id
        third_id = third.id

        assert competition_colors_for_soups(session, [soup.id]) == {
            soup.id: ["#ABCDEF", "#123456"],
        }

    assert client.delete(f"/api/competitions/{third_id}").status_code == 204
    with Session(engine) as session:
        assert competition_colors_for_soups(session, [ids[4]]) == {
            ids[4]: ["#ABCDEF"],
        }

    assert client.delete(f"/api/competitions/{second_id}").status_code == 204
    assert client.delete(f"/api/competitions/{ids[5]}").status_code == 204
    with Session(engine) as session:
        assert competition_colors_for_soups(session, [ids[4]]) == {ids[4]: []}


def _make_independent_competition_ready_for_judging(engine, ids):
    with Session(engine) as session:
        competition = session.get(Competition, ids[5])
        soup = session.get(Soup, ids[4])
        competition.score_type = "independent"
        evaluate_soup_competitions(session, soup)
        competition.end_time = datetime.utcnow() - timedelta(hours=1)
        competition.scoring_at = datetime.utcnow() - timedelta(minutes=30)
        entry = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition.id
            )
        ).one()
        entry.final_score = 0
        session.commit()
        return competition.id, entry.id


def test_independent_competition_requires_valid_scoring_date():
    client, _engine, ids = _setup()
    base = {
        "name": "独评日期校验",
        "description": "说明",
        "start_time": "2026-08-08T00:00:00+08:00",
        "end_time": "2026-08-09T00:00:00+08:00",
        "required_tag_ids": [ids[2]],
        "score_type": "independent",
    }

    missing = client.post("/api/competitions", json=base)
    too_early = client.post(
        "/api/competitions",
        json={**base, "scoring_at": "2026-08-08T23:59:59+08:00"},
    )
    average_with_date = client.post(
        "/api/competitions",
        json={
            **base,
            "score_type": "average",
            "scoring_at": "2026-08-09T00:00:00+08:00",
        },
    )

    assert missing.status_code == 422
    assert too_early.status_code == 422
    assert average_with_date.status_code == 422


def test_independent_scores_are_private_until_complete_settlement():
    client, engine, ids = _setup()
    competition_id, entry_id = _make_independent_competition_ready_for_judging(
        engine,
        ids,
    )

    public_before = client.get(f"/api/competitions/{competition_id}")
    judging_before = client.get(f"/api/competitions/{competition_id}/judging")
    incomplete = client.post(f"/api/competitions/{competition_id}/settle")
    saved = client.put(
        f"/api/competitions/{competition_id}/entries/{entry_id}/judge-score",
        json={"score": 7.5},
    )
    public_during = client.get(f"/api/competitions/{competition_id}")

    assert public_before.status_code == 200
    assert public_before.json()["rankings"] == {"total": [], "groups": []}
    assert public_before.json()["entries"][0]["final_score"] is None
    assert "judge_score" not in public_before.json()["entries"][0]
    assert judging_before.json()["scored_count"] == 0
    assert incomplete.status_code == 409
    assert incomplete.json()["detail"] == {
        "code": "INDEPENDENT_SCORING_INCOMPLETE",
        "message": "还有 1 件作品未完成比赛方评分",
        "missing_count": 1,
    }
    assert saved.status_code == 200
    assert saved.json()["judge_score"] == 7.5
    assert saved.json()["judged_by_uid"] == ids[0]
    assert public_during.json()["rankings"] == {"total": [], "groups": []}
    assert public_during.json()["entries"][0]["final_score"] is None

    with Session(engine) as session:
        soup = session.get(Soup, ids[4])
        soup.avg_rating = 10.0
        session.commit()

    settled = client.post(f"/api/competitions/{competition_id}/settle")

    assert settled.status_code == 200
    assert settled.json()["rankings"]["total"][0]["final_score"] == 7.5
    assert settled.json()["entries"][0]["final_score"] == 7.5


def test_independent_competition_exposes_configured_optional_group_names():
    client, engine, ids = _setup()
    competition_id, _entry_id = _make_independent_competition_ready_for_judging(
        engine,
        ids,
    )
    with Session(engine) as session:
        optional = Tag(
            slug="独评分组",
            name="独评分组",
            kind=TagKind.SYSTEM,
            status=TagStatus.ACTIVE,
        )
        session.add(optional)
        session.flush()
        competition = session.get(Competition, competition_id)
        competition.optional_tag_ids = [optional.id]
        session.commit()
        optional_id = optional.id

    response = client.get(f"/api/competitions/{competition_id}")

    assert response.status_code == 200
    assert response.json()["rankings"] == {"total": [], "groups": []}
    assert response.json()["optional_tags"] == [
        {"id": optional_id, "name": "独评分组"},
    ]


def test_independent_judging_enforces_opening_score_format_and_permission():
    client, engine, ids = _setup()
    competition_id, entry_id = _make_independent_competition_ready_for_judging(
        engine,
        ids,
    )
    with Session(engine) as session:
        competition = session.get(Competition, competition_id)
        competition.scoring_at = datetime.utcnow() + timedelta(hours=1)
        session.commit()

    early = client.put(
        f"/api/competitions/{competition_id}/entries/{entry_id}/judge-score",
        json={"score": 8.0},
    )
    invalid = client.put(
        f"/api/competitions/{competition_id}/entries/{entry_id}/judge-score",
        json={"score": 8.2},
    )

    async def override_non_owner():
        with Session(engine) as session:
            return session.get(User, ids[1])

    client.app.dependency_overrides[get_current_active_user] = override_non_owner
    forbidden = client.get(f"/api/competitions/{competition_id}/judging")

    assert early.status_code == 409
    assert early.json()["detail"]["code"] == "INDEPENDENT_SCORING_NOT_OPEN"
    assert invalid.status_code == 422
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "COMPETITION_JUDGING_FORBIDDEN"


def test_independent_judging_locks_membership_configuration_after_first_score():
    client, engine, ids = _setup()
    competition_id, entry_id = _make_independent_competition_ready_for_judging(
        engine,
        ids,
    )
    assert client.put(
        f"/api/competitions/{competition_id}/entries/{entry_id}/judge-score",
        json={"score": 8.0},
    ).status_code == 200

    with Session(engine) as session:
        competition = session.get(Competition, competition_id)
        scoring_at = competition.scoring_at.replace(tzinfo=timezone.utc).isoformat()

    response = client.put(
        f"/api/competitions/{competition_id}",
        json={
            "name": "试图改范围",
            "description": "说明",
            "start_time": (
                datetime.now(timezone.utc) - timedelta(hours=3)
            ).isoformat(),
            "end_time": (
                datetime.now(timezone.utc) - timedelta(hours=1)
            ).isoformat(),
            "required_tag_ids": [ids[2]],
            "score_type": "independent",
            "scoring_at": scoring_at,
            "top_n": 10,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INDEPENDENT_SCORING_LOCKED"


def test_independent_judging_freezes_entry_membership_after_first_score():
    client, engine, ids = _setup()
    competition_id, entry_id = _make_independent_competition_ready_for_judging(
        engine,
        ids,
    )
    assert client.put(
        f"/api/competitions/{competition_id}/entries/{entry_id}/judge-score",
        json={"score": 8.0},
    ).status_code == 200

    with Session(engine) as session:
        competition = session.get(Competition, competition_id)
        original_soup = session.get(Soup, ids[4])
        original_tag = session.exec(
            select(SoupTag).where(
                SoupTag.soup_id == original_soup.id,
                SoupTag.tag_id == ids[2],
            )
        ).one()
        session.delete(original_tag)
        session.flush()
        assert evaluate_soup_competitions(session, original_soup)[0].id == entry_id

        new_soup = Soup(
            author_uid=ids[1],
            title="评分开始后的作品",
            puzzle="谜面",
            solution="汤底",
            genre="本格",
            soup_color="清汤",
            main_player_count=1,
            secondary_player_count=0,
            created_at=competition.start_time
            + (competition.end_time - competition.start_time) / 2,
        )
        session.add(new_soup)
        session.flush()
        session.add(SoupTag(soup_id=new_soup.id, tag_id=ids[2]))
        session.flush()
        assert evaluate_soup_competitions(session, new_soup) == []

        entries = session.exec(
            select(CompetitionEntry).where(
                CompetitionEntry.competition_id == competition_id
            )
        ).all()
        assert [entry.id for entry in entries] == [entry_id]
