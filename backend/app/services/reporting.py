"""Report target validation and admin-facing target metadata."""
from dataclasses import dataclass

from sqlmodel import Session

from app.models.database import (
    Comment,
    CommentTargetType,
    Post,
    PrivateMessage,
    ReportTargetType,
    Soup,
    User,
)


class ReportTargetError(ValueError):
    def __init__(self, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ReportTargetInfo:
    target_type: ReportTargetType
    target_id: int
    author_uid: int | None
    url: str | None
    exists: bool = True
    preview: str | None = None


def _preview(value: str, limit: int = 800) -> str:
    normalized = value.strip()
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}…"


def _target_type(value: str | ReportTargetType) -> ReportTargetType:
    try:
        return ReportTargetType(value)
    except ValueError as exc:
        raise ReportTargetError("REPORT_TARGET_TYPE_INVALID", "举报目标类型无效", 422) from exc


def inspect_report_target(
    db: Session,
    target_type: str | ReportTargetType,
    target_id: int,
) -> ReportTargetInfo:
    """Resolve a target without applying reporter-specific authorization."""
    resolved_type = _target_type(target_type)

    if resolved_type == ReportTargetType.POST:
        target = db.get(Post, target_id)
        return ReportTargetInfo(
            resolved_type,
            target_id,
            target.author_uid if target else None,
            f"/posts/{target_id}",
            bool(target and target.status != "deleted"),
            _preview(f"{target.title}\n{target.content}") if target else None,
        )

    if resolved_type == ReportTargetType.COMMENT:
        target = db.get(Comment, target_id)
        url = None
        parent_exists = False
        if target:
            prefix = "posts" if target.target_type == CommentTargetType.POST else "soups"
            url = f"/{prefix}/{target.target_id}#comment-{target_id}"
            if target.target_type == CommentTargetType.POST:
                parent = db.get(Post, target.target_id)
                parent_exists = bool(parent and parent.status == "published")
            else:
                parent = db.get(Soup, target.target_id)
                parent_exists = bool(parent and parent.status != "deleted")
        return ReportTargetInfo(
            resolved_type,
            target_id,
            target.author_uid if target else None,
            url,
            bool(target and target.status != "deleted" and parent_exists),
            _preview(target.content) if target else None,
        )

    if resolved_type == ReportTargetType.SOUP:
        target = db.get(Soup, target_id)
        return ReportTargetInfo(
            resolved_type,
            target_id,
            target.author_uid if target else None,
            f"/soups/{target_id}",
            bool(target and target.status != "deleted"),
            _preview(f"{target.title}\n{target.puzzle}") if target else None,
        )

    if resolved_type == ReportTargetType.MESSAGE:
        target = db.get(PrivateMessage, target_id)
        preview = None
        if target:
            preview = _preview(
                f"发件人 UID {target.sender_uid} → 收件人 UID {target.receiver_uid}\n{target.content}"
            )
        return ReportTargetInfo(
            resolved_type,
            target_id,
            target.sender_uid if target else None,
            None,
            target is not None,
            preview,
        )

    target = db.get(User, target_id)
    return ReportTargetInfo(
        resolved_type,
        target_id,
        target.uid if target else None,
        f"/profile/{target_id}",
        target is not None,
        _preview(f"@{target.username} · {target.nickname}\n{target.bio or ''}") if target else None,
    )


def validate_report_target(
    db: Session,
    target_type: str | ReportTargetType,
    target_id: int,
    reporter_uid: int,
) -> ReportTargetInfo:
    info = inspect_report_target(db, target_type, target_id)
    if not info.exists:
        raise ReportTargetError("REPORT_TARGET_NOT_FOUND", "举报目标不存在或已删除", 404)

    if info.target_type == ReportTargetType.MESSAGE:
        message = db.get(PrivateMessage, target_id)
        if message is None or message.receiver_uid != reporter_uid or message.receiver_deleted:
            raise ReportTargetError("REPORT_MESSAGE_FORBIDDEN", "只能举报自己收到的私信", 403)

    if info.author_uid == reporter_uid:
        raise ReportTargetError("SELF_REPORT_FORBIDDEN", "不能举报自己发布的内容或账号", 400)
    return info
