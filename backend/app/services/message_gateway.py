"""Realtime delivery for conversational messages.

Redis is used only as a cross-process transport.  Local delivery remains
available when Redis is missing or unavailable, which keeps chat usable in
development and during an optional dependency outage.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None

from fastapi import WebSocket

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class MessageGateway:
    channel = "ctg:messages"

    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)
        self._typing: dict[tuple[int, int], tuple[asyncio.Task[Any], set[int]]] = {}
        self._lock = asyncio.Lock()
        self._redis = self._new_redis()
        self._redis_status = "disabled" if self._redis is None else "unknown"
        self._subscriber_task: asyncio.Task[Any] | None = None
        self._instance_id = uuid.uuid4().hex

    @staticmethod
    def _new_redis() -> Any:
        settings = get_settings()
        if redis is None or not settings.REDIS_URL:
            return None
        try:
            return redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
                decode_responses=True,
            )
        except Exception:
            return None

    @property
    def health_status(self) -> dict[str, str]:
        if self._redis is None:
            return {"message_gateway": "memory", "message_gateway_adapter": "memory"}
        return {
            "message_gateway": "redis" if self._redis_status == "available" else "memory",
            "message_gateway_adapter": self._redis_status,
        }

    def probe(self) -> str:
        if self._redis is None:
            self._redis_status = "disabled"
            return self._redis_status
        try:
            self._redis.ping()
        except Exception:
            self._redis_status = "degraded"
        else:
            self._redis_status = "available"
        return self._redis_status

    async def register(self, user_uid: int, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections[user_uid].add(websocket)
            self._ensure_subscriber()

    async def unregister(self, user_uid: int, websocket: WebSocket) -> None:
        stop_events: list[tuple[int, set[int]]] = []
        async with self._lock:
            sockets = self._connections.get(user_uid)
            if sockets is not None:
                sockets.discard(websocket)
                if not sockets:
                    self._connections.pop(user_uid, None)
                    for key, lease in list(self._typing.items()):
                        if key[1] == user_uid:
                            lease[0].cancel()
                            self._typing.pop(key, None)
                            stop_events.append((key[0], lease[1]))
        for conversation_id, recipient_uids in stop_events:
            await self.broadcast(
                conversation_id,
                {"type": "typing.stop", "conversation_id": conversation_id, "user_uid": user_uid},
                exclude_uid=user_uid,
                recipient_uids=recipient_uids,
            )

    def _ensure_subscriber(self) -> None:
        if self._redis is not None and self._subscriber_task is None:
            try:
                loop = asyncio.get_running_loop()
                self._subscriber_task = loop.create_task(self._listen_redis())
            except RuntimeError:
                pass

    @staticmethod
    def _jsonable(event: dict[str, Any]) -> dict[str, Any]:
        result = dict(event)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result

    async def _broadcast_local(
        self,
        conversation_id: int,
        event: dict[str, Any],
        *,
        exclude_uid: int | None = None,
        recipient_uids: set[int] | None = None,
    ) -> None:
        payload = self._jsonable(event)
        recipients: set[WebSocket] = set()
        async with self._lock:
            for uid, sockets in self._connections.items():
                if uid != exclude_uid and (recipient_uids is None or uid in recipient_uids):
                    recipients.update(sockets)
        for websocket in recipients:
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.debug("stale message websocket", exc_info=True)

    async def broadcast(self, conversation_id: int, event: dict[str, Any], *, recipient_uids: set[int], exclude_uid: int | None = None) -> None:
        payload = self._jsonable(event)
        await self._broadcast_local(conversation_id, payload, recipient_uids=recipient_uids, exclude_uid=exclude_uid)
        if self._redis is not None:
            try:
                self._redis.publish(self.channel, json.dumps({"origin": self._instance_id, "conversation_id": conversation_id, "event": payload, "recipient_uids": list(recipient_uids), "exclude_uid": exclude_uid}))
                self._redis_status = "available"
            except Exception:
                self._redis_status = "degraded"

    async def typing_start(self, conversation_id: int, user_uid: int, recipient_uids: set[int]) -> None:
        key = (conversation_id, user_uid)
        previous = self._typing.pop(key, None)
        if previous:
            previous[0].cancel()
        self._typing[key] = (asyncio.create_task(self._typing_expiry(key)), set(recipient_uids))
        await self.broadcast(conversation_id, {"type": "typing.start", "conversation_id": conversation_id, "user_uid": user_uid}, recipient_uids=recipient_uids, exclude_uid=user_uid)

    async def typing_stop(self, conversation_id: int, user_uid: int, recipient_uids: set[int]) -> None:
        lease = self._typing.pop((conversation_id, user_uid), None)
        if lease:
            lease[0].cancel()
        await self.broadcast(conversation_id, {"type": "typing.stop", "conversation_id": conversation_id, "user_uid": user_uid}, recipient_uids=recipient_uids, exclude_uid=user_uid)

    async def _typing_expiry(self, key: tuple[int, int]) -> None:
        try:
            await asyncio.sleep(5)
            lease = self._typing.pop(key, None)
            if lease is not None:
                await self.broadcast(key[0], {"type": "typing.stop", "conversation_id": key[0], "user_uid": key[1]}, exclude_uid=key[1], recipient_uids=lease[1])
        except asyncio.CancelledError:
            return

    async def _listen_redis(self) -> None:
        retry_delay = 0.5
        try:
            while self._connections and self._redis is not None:
                pubsub = None
                try:
                    pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
                    pubsub.subscribe(self.channel)
                    while self._connections:
                        message = await asyncio.to_thread(pubsub.get_message, timeout=1.0)
                        if not message or message.get("type") != "message":
                            continue
                        data = json.loads(message["data"])
                        if data.get("origin") == self._instance_id:
                            continue
                        await self._broadcast_local(
                            data["conversation_id"],
                            data["event"],
                            recipient_uids=set(data.get("recipient_uids", [])),
                            exclude_uid=data.get("exclude_uid"),
                        )
                    retry_delay = 0.5
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self._redis_status = "degraded"
                    logger.debug("message Redis subscriber stopped", exc_info=True)
                    if self._connections:
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 5.0)
                finally:
                    if pubsub is not None:
                        try:
                            pubsub.unsubscribe(self.channel)
                        except Exception:
                            logger.debug("message Redis unsubscribe failed", exc_info=True)
                        try:
                            pubsub.close()
                        except Exception:
                            logger.debug("message Redis pubsub close failed", exc_info=True)
        finally:
            self._subscriber_task = None


message_gateway = MessageGateway()
