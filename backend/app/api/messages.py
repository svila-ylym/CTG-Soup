from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.auth import get_current_active_user
from app.models.database import (
    Blacklist,
    DirectConversation,
    PrivateMessage,
    User,
    get_db,
)
from app.schemas.chat import (
    ChatMessageResponse,
    ConversationCreate,
    ConversationPageResponse,
    ConversationResponse,
    MessageCreate,
    MessageCursorPage,
    ReadConversationRequest,
    ReadConversationResponse,
)
from app.schemas.community import PrivateMessageCreate, PrivateMessageResponse
from app.services.message_gateway import message_gateway
from app.services.levels import level_band, level_progress
from app.services.user_display import user_display_fields

router = APIRouter()


def canonical_pair(first_uid: int, second_uid: int) -> tuple[int, int]:
    if first_uid == second_uid:
        raise ValueError("cannot create a direct conversation with self")
    return min(first_uid, second_uid), max(first_uid, second_uid)


def _user_payload(db: Session, user: User) -> dict:
    progress = level_progress(user.points)
    return {
        "uid": user.uid,
        "username": user.username,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "level": progress.level,
        "level_band": level_band(progress.level),
        **user_display_fields(db, user),
    }


def _message_payload(message: PrivateMessage) -> dict:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sender_uid": message.sender_uid,
        "receiver_uid": message.receiver_uid,
        "content": message.content,
        "is_read": message.is_read,
        "created_at": message.created_at,
    }


def _legacy_message_payload(message: PrivateMessage, db: Session) -> dict:
    return {
        **_message_payload(message),
        "sender": _user_payload(db, db.get(User, message.sender_uid)),
        "receiver": _user_payload(db, db.get(User, message.receiver_uid)),
    }


def _conversation_for_member(
    db: Session,
    conversation_id: int,
    user_uid: int,
) -> DirectConversation:
    conversation = db.get(DirectConversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if user_uid not in {conversation.low_uid, conversation.high_uid}:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    return conversation


def _other_uid(conversation: DirectConversation, current_uid: int) -> int:
    return (
        conversation.high_uid
        if conversation.low_uid == current_uid
        else conversation.low_uid
    )


def _blocked(db: Session, first_uid: int, second_uid: int) -> bool:
    return db.exec(
        select(Blacklist).where(
            (
                (Blacklist.blocker_uid == first_uid)
                & (Blacklist.blocked_uid == second_uid)
            )
            | (
                (Blacklist.blocker_uid == second_uid)
                & (Blacklist.blocked_uid == first_uid)
            )
        )
    ).first() is not None


def _get_or_create_conversation(
    db: Session,
    current_uid: int,
    other_uid: int,
) -> DirectConversation:
    try:
        low_uid, high_uid = canonical_pair(current_uid, other_uid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="不能与自己创建会话") from exc
    if db.get(User, other_uid) is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    existing = db.exec(
        select(DirectConversation).where(
            DirectConversation.low_uid == low_uid,
            DirectConversation.high_uid == high_uid,
        )
    ).first()
    if existing is not None:
        return existing

    conversation = DirectConversation(low_uid=low_uid, high_uid=high_uid)
    db.add(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        conversation = db.exec(
            select(DirectConversation).where(
                DirectConversation.low_uid == low_uid,
                DirectConversation.high_uid == high_uid,
            )
        ).one()
    else:
        db.refresh(conversation)
    return conversation


def _conversation_payload(
    db: Session,
    conversation: DirectConversation,
    current_uid: int,
) -> dict:
    other = db.get(User, _other_uid(conversation, current_uid))
    last_message = db.exec(
        select(PrivateMessage)
        .where(PrivateMessage.conversation_id == conversation.id)
        .order_by(PrivateMessage.id.desc())
        .limit(1)
    ).first()
    unread_count = db.exec(
        select(func.count())
        .select_from(PrivateMessage)
        .where(
            PrivateMessage.conversation_id == conversation.id,
            PrivateMessage.receiver_uid == current_uid,
            PrivateMessage.is_read == False,
            PrivateMessage.receiver_deleted == False,
        )
    ).one()
    return {
        "id": conversation.id,
        "other_user": _user_payload(db, other),
        "last_message": _message_payload(last_message) if last_message else None,
        "unread_count": unread_count,
        "last_message_at": conversation.last_message_at,
        "created_at": conversation.created_at,
    }


def _send(
    db: Session,
    conversation: DirectConversation,
    sender: User,
    content: str,
) -> PrivateMessage:
    receiver_uid = _other_uid(conversation, sender.uid)
    if _blocked(db, sender.uid, receiver_uid):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "MESSAGE_BLOCKED", "message": "双方存在拉黑关系"},
        )
    message = PrivateMessage(
        conversation_id=conversation.id,
        sender_uid=sender.uid,
        receiver_uid=receiver_uid,
        content=content,
    )
    db.add(message)
    db.flush()
    conversation.last_message_at = message.created_at
    db.commit()
    db.refresh(message)
    return message


@router.get("/conversations", response_model=ConversationPageResponse)
def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversations = db.exec(
        select(DirectConversation)
        .where(
            (DirectConversation.low_uid == current_user.uid)
            | (DirectConversation.high_uid == current_user.uid)
        )
        .order_by(
            DirectConversation.last_message_at.desc(),
            DirectConversation.id.desc(),
        )
    ).all()
    return {
        "items": [
            _conversation_payload(db, conversation, current_user.uid)
            for conversation in conversations
        ],
        "total": len(conversations),
    }


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = _get_or_create_conversation(db, current_user.uid, data.user_uid)
    return _conversation_payload(db, conversation, current_user.uid)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageCursorPage,
)
def list_messages(
    conversation_id: int,
    before_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _conversation_for_member(db, conversation_id, current_user.uid)
    query = select(PrivateMessage).where(
        PrivateMessage.conversation_id == conversation_id,
        (
            (
                (PrivateMessage.sender_uid == current_user.uid)
                & (PrivateMessage.sender_deleted == False)
            )
            | (
                (PrivateMessage.receiver_uid == current_user.uid)
                & (PrivateMessage.receiver_deleted == False)
            )
        ),
    )
    if before_id is not None:
        query = query.where(PrivateMessage.id < before_id)
    rows = db.exec(query.order_by(PrivateMessage.id.desc()).limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [_message_payload(message) for message in reversed(rows)],
        "next_cursor": rows[-1].id if has_more and rows else None,
    }


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_conversation_message(
    conversation_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = _conversation_for_member(db, conversation_id, current_user.uid)
    message = _send(db, conversation, current_user, data.content)
    await message_gateway.broadcast(
        conversation_id,
        {"type": "message.created", **_message_payload(message)},
        recipient_uids={conversation.low_uid, conversation.high_uid},
    )
    return _message_payload(message)


@router.put(
    "/conversations/{conversation_id}/read",
    response_model=ReadConversationResponse,
)
async def read_conversation(
    conversation_id: int,
    data: ReadConversationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = _conversation_for_member(db, conversation_id, current_user.uid)
    valid_message_id: int | None = None
    if data.message_id is not None:
        selected_message = db.get(PrivateMessage, data.message_id)
        if selected_message is None or selected_message.conversation_id != conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "MESSAGE_NOT_FOUND", "message": "消息不存在"},
            )
        if selected_message.receiver_uid != current_user.uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "MESSAGE_READ_FORBIDDEN",
                    "message": "只能标记收到的消息",
                },
            )
        valid_message_id = selected_message.id
    query = select(PrivateMessage).where(
        PrivateMessage.conversation_id == conversation_id,
        PrivateMessage.receiver_uid == current_user.uid,
        PrivateMessage.is_read == False,
    )
    if valid_message_id is not None:
        query = query.where(PrivateMessage.id <= valid_message_id)
    messages = db.exec(query).all()
    for message in messages:
        message.is_read = True
    db.commit()
    last_read_message_id = max(
        (message.id for message in messages),
        default=valid_message_id,
    )
    if last_read_message_id is not None:
        await message_gateway.broadcast(
            conversation_id,
            {
                "type": "message.read",
                "conversation_id": conversation_id,
                "message_id": last_read_message_id,
                "reader_uid": current_user.uid,
            },
            recipient_uids={conversation.low_uid, conversation.high_uid},
        )
    return {
        "conversation_id": conversation_id,
        "last_read_message_id": last_read_message_id,
        "read_count": len(messages),
    }


@router.post("", response_model=PrivateMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_legacy_message(
    data: PrivateMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    conversation = _get_or_create_conversation(db, current_user.uid, data.receiver_uid)
    message = _send(db, conversation, current_user, data.content.strip())
    await message_gateway.broadcast(
        conversation.id,
        {"type": "message.created", **_message_payload(message)},
        recipient_uids={conversation.low_uid, conversation.high_uid},
    )
    return _legacy_message_payload(message, db)
