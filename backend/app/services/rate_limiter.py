"""Redis-backed request limiting with a safe in-process fallback."""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Deque, Dict, Optional, Tuple

try:
    import redis
except ImportError:
    redis = None

from app.core.config import get_settings


_INCREMENT_WITH_EXPIRY = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""
_AUTO_REDIS = object()


class RateLimiter:
    """Allow a bounded number of actions in a time window."""

    def __init__(self, redis_client: Any = _AUTO_REDIS) -> None:
        self._redis_client = self._new_redis_client() if redis_client is _AUTO_REDIS else redis_client
        self._fallback: Dict[Tuple[str, str], Deque[datetime]] = defaultdict(deque)
        self._fallback_lock = Lock()
        self._redis_status = "unknown" if self._redis_client is not None else "disabled"

    @staticmethod
    def _new_redis_client() -> Optional[Any]:
        redis_url = get_settings().REDIS_URL
        if not redis_url or redis is None:
            return None
        return redis.Redis.from_url(redis_url, socket_connect_timeout=0.2, socket_timeout=0.2)

    @property
    def health_status(self) -> Dict[str, str]:
        return {
            "redis": self._redis_status,
            "fallback": "active" if self._redis_status != "available" else "standby",
        }

    def probe(self) -> str:
        if self._redis_client is None:
            self._redis_status = "disabled"
            return self._redis_status
        try:
            self._redis_client.ping()
        except (getattr(redis, "RedisError", Exception), OSError, ConnectionError):
            self._redis_status = "degraded"
        else:
            self._redis_status = "available"
        return self._redis_status

    def allow(self, scope: str, key: str, limit: int, window_seconds: int) -> bool:
        if limit < 1 or window_seconds < 1:
            raise ValueError("limit and window_seconds must be positive")

        if self._redis_client is not None:
            try:
                count = self._redis_client.eval(
                    _INCREMENT_WITH_EXPIRY,
                    1,
                    f"rate-limit:{scope}:{key}",
                    window_seconds,
                )
                self._redis_status = "available"
                return int(count) <= limit
            except (getattr(redis, "RedisError", Exception), OSError, ConnectionError):
                self._redis_status = "degraded"

        return self._allow_with_fallback(scope, key, limit, window_seconds)

    def _allow_with_fallback(
        self,
        scope: str,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        bucket_key = (scope, key)
        with self._fallback_lock:
            events = self._fallback[bucket_key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True


rate_limiter = RateLimiter()
