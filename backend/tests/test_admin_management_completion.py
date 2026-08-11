from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.api import admin, competitions, posts, turtle_soups
from app.api.auth import (
    get_current_active_user,
    get_current_admin_user,
    get_current_root_user,
    get_current_user,
)
from app.models.database import (
    Competition,
    CompetitionEntry,
    CompetitionStatus,
    Comment,
    CommentTargetType,
    Notification,
    NotificationType,
    OperationLog,
    Post,
    PrivateMessage,
    Punishment,
    PunishmentType,
    Report,
    Soup,
    User,
    UserRole,
    UserStatus,
    get_db,
)
from app.services.punishments import sync_user_punishment_status


def _management_app():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        root = User(
            username="root-user",
            nickname="根用户",
            email="root@example.com",
            hashed_password="unused",
            role=UserRole.ROOT,
            status=UserStatus.ACTIVE,
        )
        moderator = User(
            username="moderator",
            nickname="管理员",
            email="moderator@example.com",
            hashed_password="unused",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        author = User(
            username="soup-author",
            nickname="作者",
            email="author@example.com",
            hashed_password="unused",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        reporter = User(
            username="reporter",
            nickname="举报人",
            email="reporter@example.com",
            hashed_password="unused",
            role=UserRole.USER,
            status=UserStatus.ACTIVE,
        )
        session.add_all([root, moderator, author, reporter])
        session.commit()
        for user in (root, moderator, author, reporter):
            session.refresh(user)

        private_message = PrivateMessage(
            sender_uid=author.uid,
            receiver_uid=reporter.uid,
            content="私信举报证据",
        )
        session.add(private_message)

        soup = Soup(
            author_uid=author.uid,
            title="待管理作品",
            puzzle="谜面",
            solution="汤底",
        )
        session.add(soup)
        post = Post(
            author_uid=author.uid,
            title="待管理帖子",
            content="帖子内容",
        )
        session.add(post)
        session.commit()
        session.refresh(soup)
        session.refresh(post)
        session.refresh(private_message)
        comment = Comment(
            author_uid=reporter.uid,
            target_type=CommentTargetType.POST,
            target_id=post.id,
            content="待删除评论",
        )
        session.add(comment)
        post.comment_count = 1
        session.commit()
        session.refresh(comment)

        now = datetime.utcnow()
        unsettled = Competition(
            creator_uid=moderator.uid,
            name="进行中比赛",
            description="比赛",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
            required_tag_ids=[1],
            status=CompetitionStatus.ONGOING,
        )
        settled = Competition(
            creator_uid=moderator.uid,
            name="已结算比赛",
            description="比赛",
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=1),
            required_tag_ids=[1],
            status=CompetitionStatus.COMPLETED,
            settled_at=now,
            result_snapshot={"entries": []},
        )
        session.add_all([unsettled, settled])
        session.commit()
        session.refresh(unsettled)
        session.refresh(settled)
        session.add_all([
            CompetitionEntry(
                competition_id=unsettled.id,
                soup_id=soup.id,
                author_uid=author.uid,
            ),
            CompetitionEntry(
                competition_id=settled.id,
                soup_id=soup.id,
                author_uid=author.uid,
            ),
        ])
        session.commit()
        ids = {
            "root": root.uid,
            "moderator": moderator.uid,
            "author": author.uid,
            "reporter": reporter.uid,
            "soup": soup.id,
            "post": post.id,
            "comment": comment.id,
            "message": private_message.id,
            "unsettled": unsettled.id,
            "settled": settled.id,
        }

    app = FastAPI()
    app.include_router(admin.router, prefix="/api/admin")
    app.include_router(competitions.router, prefix="/api/competitions")
    app.include_router(posts.router, prefix="/api/posts")
    app.include_router(turtle_soups.router, prefix="/api/turtle-soups")
    current = {"user": ids["reporter"], "active": ids["author"]}

    def override_db():
        with Session(engine) as session:
            yield session

    def user(uid_key: str):
        async def dependency():
            with Session(engine) as session:
                return session.get(User, ids[uid_key])
        return dependency

    async def override_user():
        with Session(engine) as session:
            return session.get(User, current["user"])

    async def override_active():
        with Session(engine) as session:
            return session.get(User, current["active"])

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_active_user] = override_active
    app.dependency_overrides[get_current_admin_user] = user("moderator")
    app.dependency_overrides[get_current_root_user] = user("root")
    return TestClient(app), engine, ids, current


def test_reports_validate_targets_reject_duplicates_and_notify_reporter():
    client, engine, ids, _current = _management_app()

    self_report = client.post(
        "/api/admin/reports",
        json={"target_type": "user", "target_id": ids["reporter"], "reason": "测试自我举报"},
    )
    assert self_report.status_code == 400

    created = client.post(
        "/api/admin/reports",
        json={"target_type": "soup", "target_id": ids["soup"], "reason": "内容违规"},
    )
    assert created.status_code == 201
    duplicate = client.post(
        "/api/admin/reports",
        json={"target_type": "soup", "target_id": ids["soup"], "reason": "重复举报"},
    )
    assert duplicate.status_code == 409

    message_report = client.post(
        "/api/admin/reports",
        json={"target_type": "message", "target_id": ids["message"], "reason": "私信骚扰"},
    )
    assert message_report.status_code == 201
    report_list = client.get("/api/admin/reports", params={"page_size": 100})
    message_item = next(
        item for item in report_list.json()["items"] if item["id"] == message_report.json()["id"]
    )
    assert "私信举报证据" in message_item["target_preview"]
    assert message_item["target_url"] is None

    decision = client.post(
        f"/api/admin/reports/{created.json()['id']}/decision",
        json={"accepted": True, "result": "已核实并处理"},
    )
    assert decision.status_code == 200
    duplicate_decision = client.post(
        f"/api/admin/reports/{created.json()['id']}/decision",
        json={"accepted": False, "result": "重复处理"},
    )
    assert duplicate_decision.status_code == 400
    with Session(engine) as session:
        report = session.get(Report, created.json()["id"])
        notifications = session.exec(
            select(Notification).where(
                Notification.recipient_uid == ids["reporter"],
                Notification.notification_type == NotificationType.REPORT_RESULT,
                Notification.title == "举报处理结果",
            )
        ).all()
        assert report.handle_result == "已核实并处理"
        assert len(notifications) == 1
        assert "已采纳" in notifications[0].content


def test_permission_group_membership_routes_require_root():
    membership_routes = [
        route
        for route in admin.router.routes
        if isinstance(route, APIRoute)
        and route.path == "/permission-groups/{group_id}/members/{uid}"
    ]
    assert len(membership_routes) == 2
    for route in membership_routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_current_root_user in dependency_calls


def test_expired_status_punishment_restores_user_status():
    _client, engine, ids, _current = _management_app()
    now = datetime.utcnow()
    with Session(engine) as session:
        target = session.get(User, ids["author"])
        target.status = UserStatus.BANNED
        target.token_version = 1
        session.add(Punishment(
            target_uid=target.uid,
            operator_uid=ids["moderator"],
            punishment_type=PunishmentType.BAN,
            reason="已到期封禁",
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1),
        ))
        session.commit()

        assert sync_user_punishment_status(session, target, now) is True
        assert target.status == UserStatus.ACTIVE
        assert target.token_version == 1


def test_ban_is_immediate_protects_root_and_can_be_revoked():
    client, engine, ids, _current = _management_app()

    root_status_result = client.put(
        f"/api/admin/users/{ids['root']}",
        json={"role": "root", "status": "banned"},
    )
    assert root_status_result.status_code == 400

    direct_ban = client.put(
        f"/api/admin/users/{ids['author']}",
        json={"role": "user", "status": "banned"},
    )
    assert direct_ban.status_code == 400

    root_result = client.post(
        "/api/admin/punish",
        json={"target_uid": ids["root"], "punishment_type": "ban", "reason": "不应成功"},
    )
    assert root_result.status_code == 403

    banned = client.post(
        "/api/admin/punish",
        json={"target_uid": ids["author"], "punishment_type": "ban", "reason": "严重违规"},
    )
    assert banned.status_code == 200
    silenced = client.post(
        "/api/admin/punish",
        json={"target_uid": ids["author"], "punishment_type": "silence", "reason": "同时禁言"},
    )
    assert silenced.status_code == 200
    duplicate = client.post(
        "/api/admin/punish",
        json={"target_uid": ids["author"], "punishment_type": "ban", "reason": "重复处罚"},
    )
    assert duplicate.status_code == 409

    punishment_id = banned.json()["id"]
    with Session(engine) as session:
        target = session.get(User, ids["author"])
        assert target.status == UserStatus.BANNED
        assert target.token_version == 1

    revoked = client.post(
        f"/api/admin/punish/{punishment_id}/revoke",
        json={"revoke_reason": "复核后撤销"},
    )
    assert revoked.status_code == 200
    with Session(engine) as session:
        target = session.get(User, ids["author"])
        punishment = session.get(Punishment, punishment_id)
        assert target.status == UserStatus.SILENCED
        assert target.token_version == 2
        assert punishment.is_revoked is True

    revoked_silence = client.post(
        f"/api/admin/punish/{silenced.json()['id']}/revoke",
        json={"revoke_reason": "禁言一并撤销"},
    )
    assert revoked_silence.status_code == 200
    with Session(engine) as session:
        target = session.get(User, ids["author"])
        assert target.status == UserStatus.ACTIVE
        assert target.token_version == 3


def test_admin_cannot_revoke_self_peer_admin_or_root_punishments():
    client, engine, ids, _current = _management_app()
    with Session(engine) as session:
        peer = User(
            username="peer-admin",
            nickname="同级管理员",
            email="peer-admin@example.com",
            hashed_password="unused",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        session.add(peer)
        session.commit()
        session.refresh(peer)
        punishments = [
            Punishment(
                target_uid=target_uid,
                operator_uid=ids["root"],
                punishment_type=PunishmentType.RATE_LIMIT,
                reason="权限边界测试",
                start_time=datetime.utcnow(),
            )
            for target_uid in (ids["moderator"], peer.uid, ids["root"])
        ]
        session.add_all(punishments)
        session.commit()
        for punishment in punishments:
            session.refresh(punishment)
        punishment_ids = [punishment.id for punishment in punishments]

    responses = [
        client.post(
            f"/api/admin/punish/{punishment_id}/revoke",
            json={"revoke_reason": "无权撤销"},
        )
        for punishment_id in punishment_ids
    ]

    assert [response.status_code for response in responses] == [400, 403, 403]


def test_soup_delete_preserves_frozen_results_and_competition_delete_cleans_entries():
    client, engine, ids, _current = _management_app()

    deleted_soup = client.delete(f"/api/turtle-soups/{ids['soup']}")
    assert deleted_soup.status_code == 204
    with Session(engine) as session:
        soup = session.get(Soup, ids["soup"])
        entries = session.exec(select(CompetitionEntry)).all()
        assert soup.status == "deleted"
        assert [entry.competition_id for entry in entries] == [ids["settled"]]

    deleted_competition = client.delete(f"/api/competitions/{ids['settled']}")
    assert deleted_competition.status_code == 204
    with Session(engine) as session:
        assert session.get(Competition, ids["settled"]) is None
        assert session.exec(select(CompetitionEntry)).all() == []
        actions = session.exec(
            select(OperationLog.action_type, OperationLog.target_type)
        ).all()
        assert ("delete", "soup") in actions
        assert ("delete", "competition") in actions


def test_admin_can_soft_delete_post_and_comment_with_audit_logs():
    client, engine, ids, current = _management_app()
    current["active"] = ids["moderator"]

    deleted_comment = client.delete(
        f"/api/posts/{ids['post']}/comments/{ids['comment']}"
    )
    assert deleted_comment.status_code == 204
    deleted_post = client.delete(f"/api/posts/{ids['post']}")
    assert deleted_post.status_code == 204

    with Session(engine) as session:
        assert session.get(Post, ids["post"]).status == "deleted"
        assert session.get(Comment, ids["comment"]).status == "deleted"
        targets = session.exec(select(OperationLog.target_type)).all()
        assert "post" in targets
        assert "comment" in targets
