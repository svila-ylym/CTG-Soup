"""Private system messages sent by root users."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path, PurePath
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_current_root_user
from app.core.config import get_settings
from app.models.database import (
    MessageAttachment,
    OperationLog,
    SystemMessage,
    SystemMessageRecipient,
    User,
    UserRole,
    UserStatus,
    get_db,
)
from app.schemas.system_messages import (
    MarkdownPreviewRequest,
    MarkdownPreviewResponse,
    MessageAttachmentResponse,
    SystemMessageCreate,
    SystemMessageDetail,
    SystemMessagePage,
    SystemMessageSendResponse,
)
from app.services.safe_markdown import render_safe_markdown
from app.services.message_gateway import message_gateway


router = APIRouter()
admin_router = APIRouter()
settings = get_settings()

MAX_ATTACHMENT_COUNT = 5
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 25 * 1024 * 1024
ALLOWED_ATTACHMENT_TYPES = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "text/plain": {".txt"},
    "application/zip": {".zip"},
}


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _private_root() -> Path:
    directory = Path(settings.PRIVATE_STORAGE_DIR)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _attachment_path(attachment: MessageAttachment) -> Path:
    root = _private_root()
    path = (root / attachment.storage_key).resolve()
    if root != path and root not in path.parents:
        raise _api_error(404, "ATTACHMENT_NOT_FOUND", "附件不存在")
    return path


def _attachment_payload(attachment: MessageAttachment) -> dict:
    return {
        "id": attachment.id,
        "original_name": attachment.original_name,
        "mime_type": attachment.mime_type,
        "size": attachment.size,
        "sha256": attachment.sha256,
        "created_at": attachment.created_at,
    }


def _message_access(
    db: Session,
    message_id: int,
    current_user: User,
) -> tuple[SystemMessage, SystemMessageRecipient | None]:
    message = db.get(SystemMessage, message_id)
    if message is None:
        raise _api_error(404, "SYSTEM_MESSAGE_NOT_FOUND", "系统消息不存在")
    recipient = db.exec(
        select(SystemMessageRecipient).where(
            SystemMessageRecipient.system_message_id == message_id,
            SystemMessageRecipient.user_uid == current_user.uid,
        )
    ).first()
    if recipient is None and current_user.role != UserRole.ROOT:
        raise _api_error(403, "SYSTEM_MESSAGE_FORBIDDEN", "无权查看此系统消息")
    return message, recipient


def _message_detail_payload(
    db: Session,
    message: SystemMessage,
    recipient: SystemMessageRecipient | None,
) -> dict:
    attachments = db.exec(
        select(MessageAttachment)
        .where(MessageAttachment.system_message_id == message.id)
        .order_by(MessageAttachment.id)
    ).all()
    return {
        "id": message.id,
        "title": message.title,
        "sender_uid": message.sender_uid,
        "is_read": recipient is not None and recipient.read_at is not None,
        "read_at": recipient.read_at if recipient else None,
        "attachment_count": len(attachments),
        "created_at": message.created_at,
        "markdown": message.markdown,
        "rendered_html": message.rendered_html,
        "attachments": [_attachment_payload(item) for item in attachments],
    }


@router.get("", response_model=SystemMessagePage)
def list_system_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    recipient_filters = [SystemMessageRecipient.user_uid == current_user.uid]
    if unread_only:
        recipient_filters.append(SystemMessageRecipient.read_at.is_(None))
    base = (
        select(SystemMessageRecipient, SystemMessage)
        .join(
            SystemMessage,
            SystemMessage.id == SystemMessageRecipient.system_message_id,
        )
        .where(*recipient_filters)
    )
    total = db.exec(
        select(func.count())
        .select_from(SystemMessageRecipient)
        .where(*recipient_filters)
    ).one()
    rows = db.exec(
        base.order_by(SystemMessage.created_at.desc(), SystemMessage.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    message_ids = [message.id for _, message in rows]
    attachment_counts = {
        message_id: count
        for message_id, count in (
            db.exec(
                select(
                    MessageAttachment.system_message_id,
                    func.count(MessageAttachment.id),
                )
                .where(MessageAttachment.system_message_id.in_(message_ids))
                .group_by(MessageAttachment.system_message_id)
            ).all()
            if message_ids
            else []
        )
    }
    return {
        "items": [
            {
                "id": message.id,
                "title": message.title,
                "sender_uid": message.sender_uid,
                "is_read": recipient.read_at is not None,
                "attachment_count": attachment_counts.get(message.id, 0),
                "created_at": message.created_at,
            }
            for recipient, message in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get(
    "/attachments/{attachment_id}",
    response_class=FileResponse,
)
def download_system_message_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    attachment = db.get(MessageAttachment, attachment_id)
    if attachment is None or attachment.system_message_id is None:
        raise _api_error(404, "ATTACHMENT_NOT_FOUND", "附件不存在")
    if current_user.role != UserRole.ROOT:
        recipient = db.exec(
            select(SystemMessageRecipient).where(
                SystemMessageRecipient.system_message_id == attachment.system_message_id,
                SystemMessageRecipient.user_uid == current_user.uid,
            )
        ).first()
        if recipient is None:
            raise _api_error(403, "ATTACHMENT_FORBIDDEN", "无权下载此附件")
    path = _attachment_path(attachment)
    if not path.is_file():
        raise _api_error(404, "ATTACHMENT_NOT_FOUND", "附件不存在")
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )


@router.get("/{message_id}", response_model=SystemMessageDetail)
def get_system_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    message, recipient = _message_access(db, message_id, current_user)
    return _message_detail_payload(db, message, recipient)


@router.put("/{message_id}/read", response_model=SystemMessageDetail)
def read_system_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    message, recipient = _message_access(db, message_id, current_user)
    if recipient is None:
        raise _api_error(403, "SYSTEM_MESSAGE_FORBIDDEN", "根用户预览不能标记已读")
    if recipient.read_at is None:
        recipient.read_at = datetime.utcnow()
        db.commit()
        db.refresh(recipient)
    return _message_detail_payload(db, message, recipient)


def _validated_uploads(files: list[UploadFile]) -> list[tuple[str, str, str, bytes]]:
    if not files or len(files) > MAX_ATTACHMENT_COUNT:
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ATTACHMENT_LIMIT_EXCEEDED",
            "每条消息最多上传 5 个附件",
        )
    validated: list[tuple[str, str, str, bytes]] = []
    total_size = 0
    for file in files:
        original_name = PurePath((file.filename or "").replace("\\", "/")).name.strip()
        mime_type = (file.content_type or "").lower()
        suffix = PurePath(original_name).suffix.lower()
        if (
            not original_name
            or mime_type not in ALLOWED_ATTACHMENT_TYPES
            or suffix not in ALLOWED_ATTACHMENT_TYPES[mime_type]
        ):
            raise _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "ATTACHMENT_TYPE_INVALID",
                "附件类型不受支持",
            )
        content = file.file.read(MAX_ATTACHMENT_BYTES + 1)
        size = len(content)
        total_size += size
        if size <= 0 or size > MAX_ATTACHMENT_BYTES or total_size > MAX_TOTAL_ATTACHMENT_BYTES:
            raise _api_error(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "ATTACHMENT_LIMIT_EXCEEDED",
                "单个附件不能超过 10 MiB，总大小不能超过 25 MiB",
            )
        validated.append((original_name, mime_type, suffix, content))
    return validated


def _store_attachments(
    db: Session,
    uploader: User,
    files: list[UploadFile],
) -> list[MessageAttachment]:
    validated = _validated_uploads(files)
    root = _private_root()
    stored: list[tuple[MessageAttachment, Path]] = []
    try:
        for original_name, mime_type, suffix, content in validated:
            storage_key = f"system-messages/{uploader.uid}/{uuid4().hex}{suffix}"
            destination = (root / storage_key).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            attachment = MessageAttachment(
                uploader_uid=uploader.uid,
                storage_key=storage_key,
                original_name=original_name,
                mime_type=mime_type,
                size=len(content),
                sha256=sha256(content).hexdigest(),
            )
            db.add(attachment)
            stored.append((attachment, destination))
        db.commit()
        for attachment, _ in stored:
            db.refresh(attachment)
        return [attachment for attachment, _ in stored]
    except Exception:
        db.rollback()
        for _, destination in stored:
            destination.unlink(missing_ok=True)
        raise


@admin_router.post(
    "/preview",
    response_model=MarkdownPreviewResponse,
)
def preview_system_message(
    data: MarkdownPreviewRequest,
    current_user: User = Depends(get_current_root_user),
):
    return {"rendered_html": render_safe_markdown(data.markdown)}


@admin_router.post(
    "/attachments",
    response_model=MessageAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_system_message_attachment(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    return _store_attachments(db, current_user, [file])[0]


@admin_router.post(
    "/attachments/batch",
    response_model=list[MessageAttachmentResponse],
    status_code=status.HTTP_201_CREATED,
)
def upload_system_message_attachments(
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    return _store_attachments(db, current_user, files)


def _selected_recipients(
    db: Session,
    data: SystemMessageCreate,
) -> list[User]:
    statement = select(User).where(User.status == UserStatus.ACTIVE)
    if data.recipient_mode == "selected":
        if not data.recipient_uids:
            raise _api_error(422, "RECIPIENT_REQUIRED", "请至少选择一个收件人")
        statement = statement.where(User.uid.in_(data.recipient_uids))
    users = db.exec(statement.order_by(User.uid)).all()
    if data.recipient_mode == "selected" and {user.uid for user in users} != set(data.recipient_uids):
        raise _api_error(422, "RECIPIENT_INVALID", "收件人不存在或未激活")
    if not users:
        raise _api_error(422, "RECIPIENT_REQUIRED", "没有可用的收件人")
    return users


def _selected_attachments(
    db: Session,
    root_user: User,
    attachment_ids: list[int],
) -> list[MessageAttachment]:
    if not attachment_ids:
        return []
    attachments = db.exec(
        select(MessageAttachment)
        .where(MessageAttachment.id.in_(attachment_ids))
        .order_by(MessageAttachment.id)
        .with_for_update()
    ).all()
    if (
        len(attachments) != len(attachment_ids)
        or any(
            attachment.uploader_uid != root_user.uid
            or attachment.system_message_id is not None
            for attachment in attachments
        )
    ):
        raise _api_error(403, "ATTACHMENT_NOT_OWNED", "附件不存在、已使用或不属于当前用户")
    if (
        len(attachments) > MAX_ATTACHMENT_COUNT
        or any(item.size > MAX_ATTACHMENT_BYTES for item in attachments)
        or sum(item.size for item in attachments) > MAX_TOTAL_ATTACHMENT_BYTES
    ):
        raise _api_error(422, "ATTACHMENT_LIMIT_EXCEEDED", "附件数量或大小超过限制")
    return attachments


@admin_router.post(
    "",
    response_model=SystemMessageSendResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_system_message(
    data: SystemMessageCreate,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    recipients = _selected_recipients(db, data)
    attachments = _selected_attachments(db, current_user, data.attachment_ids)
    message = SystemMessage(
        sender_uid=current_user.uid,
        title=data.title,
        markdown=data.markdown,
        rendered_html=render_safe_markdown(data.markdown),
        recipient_mode=data.recipient_mode,
    )
    db.add(message)
    db.flush()
    for user in recipients:
        db.add(
            SystemMessageRecipient(
                system_message_id=message.id,
                user_uid=user.uid,
            )
        )
    for attachment in attachments:
        attachment.system_message_id = message.id
    db.add(
        OperationLog(
            operator_uid=current_user.uid,
            operator_roles=[current_user.role.value],
            action_type="send_system_message",
            target_type="system_message",
            target_id=message.id,
            details={
                "recipient_mode": data.recipient_mode,
                "recipient_count": len(recipients),
                "attachment_count": len(attachments),
            },
        )
    )
    db.commit()
    db.refresh(message)
    await message_gateway.broadcast(
        message.id,
        {
            "type": "system_message.created",
            "system_message_id": message.id,
            "created_at": message.created_at,
        },
        recipient_uids={user.uid for user in recipients},
    )
    return {
        "id": message.id,
        "title": message.title,
        "recipient_mode": message.recipient_mode,
        "recipient_count": len(recipients),
        "attachment_count": len(attachments),
        "created_at": message.created_at,
    }
