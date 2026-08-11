"""Authenticated WebSocket endpoint for conversational messaging."""

from __future__ import annotations

import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.api.auth import _resolve_user_from_token
from app.db import engine
from app.models.database import DirectConversation, PrivateMessage, UserStatus
from app.services.message_gateway import message_gateway
from app.services.ota import maintenance_state_path

router = APIRouter()


async def _error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json({"type": "presence.error", "code": code, "message": message})


async def _auth_failure(websocket: WebSocket, code: str, message: str) -> None:
    try:
        await _error(websocket, code, message)
    except Exception:
        pass
    try:
        await websocket.close(code=1008)
    except Exception:
        # The peer may have disconnected while the auth error was sent.
        pass


def _conversation(db: Session, conversation_id: int, uid: int) -> DirectConversation | None:
    conversation = db.get(DirectConversation, conversation_id)
    if conversation is None or uid not in {conversation.low_uid, conversation.high_uid}:
        return None
    return conversation


@router.websocket("/ws/messages")
async def message_socket(websocket: WebSocket) -> None:
    if maintenance_state_path().is_file():
        await websocket.close(code=1013, reason="系统维护中")
        return
    await websocket.accept()
    user_uid: int | None = None
    try:
        try:
            frame = await asyncio.wait_for(websocket.receive_json(), timeout=5)
        except asyncio.TimeoutError:
            await _auth_failure(websocket, "WS_AUTH_REQUIRED", "首帧必须是认证事件")
            return
        except WebSocketDisconnect:
            return
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, RuntimeError):
            await _auth_failure(websocket, "WS_AUTH_REQUIRED", "首帧必须是认证事件")
            return
        if (
            not isinstance(frame, dict)
            or frame.get("type") != "auth"
            or not isinstance(frame.get("token"), str)
        ):
            await _auth_failure(websocket, "WS_AUTH_REQUIRED", "首帧必须是认证事件")
            return
        try:
            with Session(engine) as db:
                user = _resolve_user_from_token(frame["token"], db)
                if user.status != UserStatus.ACTIVE:
                    await _auth_failure(websocket, "WS_AUTH_INACTIVE", "账户未激活")
                    return
                user_uid = user.uid
        except Exception:
            await _auth_failure(websocket, "WS_AUTH_INVALID", "无法验证凭据")
            return
        if maintenance_state_path().is_file():
            await websocket.close(code=1013, reason="系统维护中")
            return
        await message_gateway.register(user_uid, websocket)
        while True:
            if maintenance_state_path().is_file():
                await websocket.close(code=1013, reason="系统维护中")
                break
            try:
                event = await asyncio.wait_for(websocket.receive_json(), timeout=1)
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except (KeyError, TypeError, ValueError, UnicodeDecodeError, RuntimeError):
                await _error(websocket, "INVALID_EVENT", "事件格式无效")
                continue
            if maintenance_state_path().is_file():
                await websocket.close(code=1013, reason="系统维护中")
                break
            if not isinstance(event, dict):
                await _error(websocket, "INVALID_EVENT", "事件格式无效")
                continue
            event_type = event.get("type")
            conversation_id = event.get("conversation_id")
            if not isinstance(conversation_id, int):
                await _error(websocket, "CONVERSATION_FORBIDDEN", "无权访问此会话")
                continue
            with Session(engine) as db:
                conversation = _conversation(db, conversation_id, user_uid)
                if conversation is None:
                    await _error(websocket, "CONVERSATION_FORBIDDEN", "无权访问此会话")
                    continue
                pair = {conversation.low_uid, conversation.high_uid}
                if event_type in {"typing.start", "typing.stop"}:
                    if event_type == "typing.start":
                        await message_gateway.typing_start(conversation_id, user_uid, pair)
                    else:
                        await message_gateway.typing_stop(conversation_id, user_uid, pair)
                    continue
                if event_type == "message.read":
                    message_id = event.get("message_id")
                    if not isinstance(message_id, int):
                        await _error(websocket, "MESSAGE_ID_INVALID", "消息 ID 无效")
                        continue
                    message = db.get(PrivateMessage, message_id)
                    if message is None or message.conversation_id != conversation_id:
                        await _error(websocket, "MESSAGE_NOT_FOUND", "消息不存在")
                        continue
                    if message.receiver_uid != user_uid:
                        await _error(websocket, "MESSAGE_READ_FORBIDDEN", "只能标记收到的消息")
                        continue
                    unread_messages = db.exec(
                        select(PrivateMessage).where(
                            PrivateMessage.conversation_id == conversation_id,
                            PrivateMessage.receiver_uid == user_uid,
                            PrivateMessage.id <= message_id,
                            PrivateMessage.is_read == False,
                        )
                    ).all()
                    for unread_message in unread_messages:
                        unread_message.is_read = True
                    if maintenance_state_path().is_file():
                        await websocket.close(code=1013, reason="系统维护中")
                        break
                    db.commit()
                    await message_gateway.broadcast(conversation_id, {"type": "message.read", "conversation_id": conversation_id, "message_id": message_id, "reader_uid": user_uid}, recipient_uids=pair)
                    continue
                await _error(websocket, "INVALID_EVENT", "不支持的事件类型")
    finally:
        if user_uid is not None:
            await message_gateway.unregister(user_uid, websocket)
