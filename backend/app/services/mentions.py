"""Parse mention spans and synchronize recipients inside content transactions."""

from dataclasses import dataclass
import re

from sqlmodel import Session, select

from app.models.database import (
    Comment,
    Mention,
    MentionTargetType,
    Notification,
    NotificationType,
    User,
)
from app.services.notification_dispatch import notify_user


MENTION_RE = re.compile(r"(?<!\S)@([^\s@]+)(?=\s|$)")


@dataclass(frozen=True)
class ParsedMention:
    username: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class MentionRef:
    uid: int
    username: str
    start_offset: int
    end_offset: int


def parse_mentions(text: str) -> list[ParsedMention]:
    return [
        ParsedMention(match.group(1), match.start(), match.end())
        for match in MENTION_RE.finditer(text)
    ]


def _notification_target(
    db: Session,
    target_type: MentionTargetType,
    target_id: int,
) -> tuple[str, int]:
    if target_type == MentionTargetType.POST:
        return "post", target_id
    comment = db.get(Comment, target_id)
    if comment is None:
        return "comment", target_id
    return comment.target_type.value, comment.target_id


def mention_refs(
    db: Session,
    target_type: MentionTargetType | str,
    target_id: int,
) -> list[MentionRef]:
    normalized_type = MentionTargetType(target_type)
    rows = db.exec(
        select(Mention, User)
        .join(User, User.uid == Mention.mentioned_uid)
        .where(
            Mention.target_type == normalized_type,
            Mention.target_id == target_id,
        )
        .order_by(Mention.start_offset, Mention.id)
    ).all()
    return [
        MentionRef(
            uid=user.uid,
            username=user.username,
            start_offset=mention.start_offset,
            end_offset=mention.end_offset,
        )
        for mention, user in rows
    ]


def sync_mentions(
    db: Session,
    actor_uid: int,
    target_type: MentionTargetType | str,
    target_id: int,
    text: str,
) -> list[MentionRef]:
    normalized_type = MentionTargetType(target_type)
    parsed = parse_mentions(text)
    first_by_username: dict[str, ParsedMention] = {}
    for mention in parsed:
        first_by_username.setdefault(mention.username, mention)

    users = db.exec(
        select(User).where(User.username.in_(tuple(first_by_username)))
    ).all() if first_by_username else []
    desired: dict[int, tuple[User, ParsedMention]] = {
        user.uid: (user, first_by_username[user.username])
        for user in users
        if user.uid != actor_uid
    }
    existing_rows = db.exec(
        select(Mention).where(
            Mention.target_type == normalized_type,
            Mention.target_id == target_id,
        )
    ).all()
    existing = {mention.mentioned_uid: mention for mention in existing_rows}

    for mentioned_uid, mention in existing.items():
        if mentioned_uid not in desired:
            db.delete(mention)

    actor = db.get(User, actor_uid)
    notification_type, notification_id = _notification_target(
        db,
        normalized_type,
        target_id,
    )
    for mentioned_uid, (user, parsed_mention) in desired.items():
        mention = existing.get(mentioned_uid)
        if mention is None:
            db.add(
                Mention(
                    actor_uid=actor_uid,
                    mentioned_uid=mentioned_uid,
                    target_type=normalized_type,
                    target_id=target_id,
                    start_offset=parsed_mention.start_offset,
                    end_offset=parsed_mention.end_offset,
                )
            )
            notify_user(
                db,
                user,
                NotificationType.MENTION,
                "有人提到了你",
                f"{actor.nickname if actor else '一位用户'} 在内容中提到了你",
                related_entity_type=notification_type,
                related_entity_id=notification_id,
            )
        else:
            mention.actor_uid = actor_uid
            mention.start_offset = parsed_mention.start_offset
            mention.end_offset = parsed_mention.end_offset

    db.flush()
    return mention_refs(db, normalized_type, target_id)


def notify_comment_reply(
    db: Session,
    actor_uid: int,
    parent: Comment,
    mentioned_uids: set[int],
) -> None:
    if parent.author_uid == actor_uid or parent.author_uid in mentioned_uids:
        return
    actor = db.get(User, actor_uid)
    db.add(
        Notification(
            recipient_uid=parent.author_uid,
            notification_type=NotificationType.COMMENT_REPLY,
            title="你的评论收到回复",
            content=f"{actor.nickname if actor else '一位用户'} 回复了你的评论",
            related_entity_type=parent.target_type.value,
            related_entity_id=parent.target_id,
        )
    )
