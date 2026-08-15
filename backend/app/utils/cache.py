"""Small, failure-tolerant Redis cache helpers."""

from __future__ import annotations

import hashlib
import json
import logging
from threading import Lock
from time import monotonic
from typing import Any, Dict, List, Optional, Union

import redis
from redis.exceptions import RedisError

from app.core.config import get_settings


JSONValue = Union[None, bool, int, float, str, List["JSONValue"], Dict[str, "JSONValue"]]
_CACHE_ERRORS = (RedisError, OSError, ConnectionError)
_logger = logging.getLogger(__name__)
_settings = get_settings()
_redis_client: Optional[redis.Redis] = None
_redis_retry_at = 0.0
_redis_lock = Lock()


def _close_client(client: Optional[redis.Redis]) -> None:
    if client is None:
        return
    try:
        client.close()
    except _CACHE_ERRORS:
        pass


def _mark_redis_unavailable(operation: str, error: BaseException) -> None:
    global _redis_client, _redis_retry_at
    client = _redis_client
    _redis_client = None
    _redis_retry_at = monotonic() + _settings.REDIS_CACHE_RETRY_SECONDS
    _close_client(client)
    _logger.warning(
        "Redis cache %s failed (%s); using database fallback",
        operation,
        type(error).__name__,
    )


def _reset_cache_state() -> None:
    """Reset process-local state. Intended for tests and controlled reloads."""
    global _redis_client, _redis_retry_at
    with _redis_lock:
        client = _redis_client
        _redis_client = None
        _redis_retry_at = 0.0
        _close_client(client)


def get_redis() -> Optional[redis.Redis]:
    """Return a healthy client, or ``None`` while disabled/unavailable."""
    global _redis_client
    if not _settings.REDIS_CACHE_ENABLED or not _settings.REDIS_URL:
        return None
    if _redis_client is not None:
        return _redis_client
    if monotonic() < _redis_retry_at:
        return None

    with _redis_lock:
        if _redis_client is not None:
            return _redis_client
        if monotonic() < _redis_retry_at:
            return None
        client: Optional[redis.Redis] = None
        try:
            client = redis.Redis.from_url(
                _settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=_settings.REDIS_CACHE_CONNECT_TIMEOUT_SECONDS,
                socket_timeout=_settings.REDIS_CACHE_SOCKET_TIMEOUT_SECONDS,
                health_check_interval=30,
                retry_on_timeout=False,
            )
            client.ping()
        except _CACHE_ERRORS as error:
            _close_client(client)
            _mark_redis_unavailable("connect", error)
            return None
        _redis_client = client
        return _redis_client


def generate_cache_key(namespace: str, **parameters: JSONValue) -> str:
    """Generate a stable, compact key from JSON-safe parameters."""
    if not namespace or any(not segment for segment in namespace.split(":")):
        raise ValueError("cache namespace must contain non-empty segments")
    payload = json.dumps(
        parameters,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"ctg:v1:{namespace}:{digest}"


def cache_get(key: str) -> Optional[Any]:
    """Read and decode a JSON cache value."""
    client = get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
    except _CACHE_ERRORS as error:
        _mark_redis_unavailable("get", error)
        return None
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        _logger.warning("Redis cache contained invalid JSON; dropping key")
        try:
            client.delete(key)
        except _CACHE_ERRORS as error:
            _mark_redis_unavailable("delete-invalid", error)
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Encode and store a JSON value with an explicit expiry."""
    effective_ttl = _settings.REDIS_CACHE_DEFAULT_TTL if ttl is None else ttl
    if isinstance(effective_ttl, bool) or effective_ttl <= 0:
        return False
    try:
        serialized = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        _logger.warning("Redis cache skipped a non-JSON-serializable value")
        return False

    client = get_redis()
    if client is None:
        return False
    try:
        client.setex(key, effective_ttl, serialized)
    except _CACHE_ERRORS as error:
        _mark_redis_unavailable("set", error)
        return False
    return True


def cache_delete(key: str) -> bool:
    """Delete a cache key without affecting the calling business operation."""
    client = get_redis()
    if client is None:
        return False
    try:
        client.delete(key)
    except _CACHE_ERRORS as error:
        _mark_redis_unavailable("delete", error)
        return False
    return True


def cache_delete_pattern(pattern: str, batch_size: int = 100) -> bool:
    """Delete matching keys incrementally without Redis ``KEYS``."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    client = get_redis()
    if client is None:
        return False
    pending: List[str] = []
    try:
        for key in client.scan_iter(match=pattern, count=batch_size):
            pending.append(key)
            if len(pending) >= batch_size:
                client.delete(*pending)
                pending.clear()
        if pending:
            client.delete(*pending)
    except _CACHE_ERRORS as error:
        _mark_redis_unavailable("scan-delete", error)
        return False
    return True
