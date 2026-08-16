"""Server-side easter egg conditions and migration-free discovery claims."""

from __future__ import annotations

import base64
from datetime import datetime, time, timezone
import json
import logging
import secrets
from typing import Iterable
from zoneinfo import ZoneInfo

from fastapi import Response
from sqlalchemy import func, text
from sqlmodel import Session, select

from app.models.database import (
    Notification,
    NotificationType,
    OperationLog,
    Rating,
    Soup,
    User,
    UserStatus,
)


logger = logging.getLogger(__name__)

NOTICE_HEADER = "X-Easter-Egg"
PUBLIC_SOUP_STATUSES = ("published", "revealed")
CHINA_TIMEZONE = ZoneInfo("Asia/Shanghai")

MESSAGE_PHRASE = "企鹅你是大忠臣"
COMMENT_PHRASE = "海龟汤吧万岁"
SOUP_PHRASE = "吃什么"
SEARCH_PHRASE = "如何拿到彩蛋"
COMMENT_REQUEST_PHRASE = "我要彩蛋"

TRIGGER_DESCRIPTIONS = {
    "sunrise_login": "在北京时间 06:30 至 07:00 登录",
    "five_turtle_soups": "发布至少 5 碗公开鳖汤",
    "comment_phrase": f"在汤评论中发送“{COMMENT_PHRASE}”",
    "message_phrase": f"在私信中发送“{MESSAGE_PHRASE}”",
    "new_soup_phrase": f"发布标题、谜面或汤底包含“{SOUP_PHRASE}”的海龟汤",
    "rated_all_public_soups": "为除自己作品外的所有公开海龟汤评分",
    "exact_search": f"搜索“{SEARCH_PHRASE}”",
    "comment_request_phrase": f"在汤评论中发送“{COMMENT_REQUEST_PHRASE}”",
}


def contains_phrase(content: str, phrase: str) -> bool:
    return phrase in content


def is_sunrise_login(now: datetime | None = None) -> bool:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    local_time = current.astimezone(CHINA_TIMEZONE).time().replace(tzinfo=None)
    return time(6, 30) <= local_time < time(7, 0)


def has_five_turtle_soups(db: Session, user_uid: int) -> bool:
    count = db.exec(
        select(func.count())
        .select_from(Soup)
        .where(
            Soup.author_uid == user_uid,
            Soup.genre == "鳖汤",
            Soup.status.in_(PUBLIC_SOUP_STATUSES),
        )
    ).one()
    return count >= 5


def has_rated_all_public_soups(db: Session, user_uid: int) -> bool:
    eligible_filters = (
        Soup.status.in_(PUBLIC_SOUP_STATUSES),
        Soup.author_uid != user_uid,
    )
    eligible_count = db.exec(
        select(func.count()).select_from(Soup).where(*eligible_filters)
    ).one()
    if eligible_count == 0:
        return False
    rated_count = db.exec(
        select(func.count())
        .select_from(Rating)
        .join(Soup, Soup.id == Rating.soup_id)
        .where(Rating.user_uid == user_uid, *eligible_filters)
    ).one()
    return rated_count == eligible_count


def cumulative_egg_candidates(db: Session, user: User) -> list[tuple[int, str]]:
    candidates: list[tuple[int, str]] = []
    if has_five_turtle_soups(db, user.uid):
        candidates.append((2, "five_turtle_soups"))
    if has_rated_all_public_soups(db, user.uid):
        candidates.append((6, "rated_all_public_soups"))
    return candidates


def comment_egg_candidates(content: str) -> list[tuple[int, str]]:
    candidates: list[tuple[int, str]] = []
    if contains_phrase(content, COMMENT_PHRASE):
        candidates.append((3, "comment_phrase"))
    if contains_phrase(content, COMMENT_REQUEST_PHRASE):
        candidates.append((9, "comment_request_phrase"))
    return candidates


def _lock_egg(db: Session, egg_id: int) -> None:
    bind = db.get_bind()
    if getattr(bind.dialect, "name", "") == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:namespace, :egg_id)"),
            {"namespace": 0x435447, "egg_id": egg_id},
        )


def _discoverer_name(user: User) -> str:
    return user.nickname or user.username or f"UID {user.uid}"


def _trigger_description(trigger: str) -> str:
    return TRIGGER_DESCRIPTIONS.get(trigger, "完成隐藏条件")


def _existing_notice(db: Session, discovery: OperationLog, egg_id: int) -> dict:
    details = discovery.details or {}
    discoverer = db.get(User, discovery.operator_uid)
    discoverer_name = (
        details.get("discoverer_name")
        or (_discoverer_name(discoverer) if discoverer else f"UID {discovery.operator_uid}")
    )
    return {
        "egg_id": egg_id,
        "first_discovery": False,
        "discoverer_uid": discovery.operator_uid,
        "discoverer_name": discoverer_name,
        "prize": None,
        "achievement_method": _trigger_description(details.get("trigger", "")),
        "message": f"彩蛋 #{egg_id} 已由 {discoverer_name} 发现",
    }


def _queue_discovery_notifications(
    db: Session,
    discoverer: User,
    notices: list[dict],
) -> None:
    first_discoveries = [notice for notice in notices if notice["first_discovery"]]
    if not first_discoveries:
        return

    recipients = db.exec(
        select(User)
        .where(User.status == UserStatus.ACTIVE)
        .order_by(User.uid)
    ).all()
    for notice in first_discoveries:
        egg_id = notice["egg_id"]
        broadcast_content = (
            f"{notice['discoverer_name']}首次达成了彩蛋 #{egg_id}"
        )
        for recipient in recipients:
            if recipient.uid == discoverer.uid:
                title = f"首次达成彩蛋 #{egg_id}"
                content = (
                    f"你首次达成了彩蛋 #{egg_id}\n"
                    f"达成方式：{notice['achievement_method']}\n"
                    f"随机字符串：{notice['prize']}"
                )
            else:
                title = "全服彩蛋首达"
                content = broadcast_content
            db.add(
                Notification(
                    recipient_uid=recipient.uid,
                    notification_type=NotificationType.SYSTEM,
                    title=title,
                    content=content,
                    related_entity_type="easter_egg",
                    related_entity_id=egg_id,
                )
            )


def claim_eggs(
    db: Session,
    user: User,
    candidates: Iterable[tuple[int, str]],
) -> list[dict]:
    unique_candidates = {
        egg_id: trigger
        for egg_id, trigger in candidates
        if 1 <= egg_id <= 9
    }
    notices: list[dict] = []
    for egg_id in sorted(unique_candidates):
        _lock_egg(db, egg_id)
        existing = db.exec(
            select(OperationLog)
            .where(
                OperationLog.action_type == "discover_easter_egg",
                OperationLog.target_type == "easter_egg",
                OperationLog.target_id == egg_id,
            )
            .order_by(OperationLog.id)
        ).first()
        if existing is not None:
            notices.append(_existing_notice(db, existing, egg_id))
            continue

        prize = f"CTG-{secrets.token_urlsafe(12)}"
        discoverer_name = _discoverer_name(user)
        achievement_method = _trigger_description(unique_candidates[egg_id])
        db.add(
            OperationLog(
                operator_uid=user.uid,
                operator_roles=[user.role.value],
                action_type="discover_easter_egg",
                target_type="easter_egg",
                target_id=egg_id,
                details={
                    "prize": prize,
                    "discoverer_name": discoverer_name,
                    "trigger": unique_candidates[egg_id],
                    "achievement_method": achievement_method,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        )
        db.flush()
        notices.append(
            {
                "egg_id": egg_id,
                "first_discovery": True,
                "discoverer_uid": user.uid,
                "discoverer_name": discoverer_name,
                "prize": prize,
                "achievement_method": achievement_method,
                "message": (
                    f"发现彩蛋 #{egg_id}！你是全站第一位发现者，"
                    f"达成方式：{achievement_method}；随机字符串：{prize}"
                ),
            }
        )
    _queue_discovery_notifications(db, user, notices)
    db.commit()
    return notices


def attach_notices(response: Response, notices: list[dict]) -> None:
    if not notices:
        return
    payload = json.dumps(notices, ensure_ascii=False, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    response.headers[NOTICE_HEADER] = encoded.rstrip("=")


def safely_claim_and_attach(
    db: Session,
    user: User,
    response: Response,
    candidates: Iterable[tuple[int, str]],
) -> None:
    prepared = list(candidates)
    if not prepared:
        return
    try:
        attach_notices(response, claim_eggs(db, user, prepared))
    except Exception:
        db.rollback()
        logger.exception(
            "Easter egg evaluation failed user_uid=%s egg_ids=%s",
            user.uid,
            [egg_id for egg_id, _ in prepared],
        )
