"""Redis 缓存服务 - 汤吧社区"""
import json
import redis
from typing import Any, Optional
from datetime import timedelta
from functools import wraps
import hashlib

from app.core.config import get_settings

_settings = get_settings()

_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """获取 Redis 客户端实例"""
    global _redis_client
    if not _settings.REDIS_CACHE_ENABLED:
        return None
    
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                _settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            _redis_client.ping()
        except Exception:
            _redis_client = None
    return _redis_client


def cache_get(key: str) -> Optional[Any]:
    """从缓存获取数据"""
    client = get_redis()
    if not client:
        return None
    try:
        value = client.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """设置缓存数据"""
    client = get_redis()
    if not client:
        return False
    try:
        ttl = ttl or _settings.REDIS_CACHE_DEFAULT_TTL
        serialized = json.dumps(value, ensure_ascii=False, default=str)
        client.setex(key, ttl, serialized)
        return True
    except Exception:
        return False


def cache_delete(key: str) -> bool:
    """删除缓存"""
    client = get_redis()
    if not client:
        return False
    try:
        client.delete(key)
        return True
    except Exception:
        return False


def cache_delete_pattern(pattern: str) -> bool:
    """批量删除匹配模式的缓存"""
    client = get_redis()
    if not client:
        return False
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
        return True
    except Exception:
        return False


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """生成缓存键"""
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    key_string = ":".join(key_parts)
    return f"soup:{key_string}"


def cached(ttl: Optional[int] = None, prefix: str = "data"):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            client = get_redis()
            if not client:
                return await func(*args, **kwargs)
            
            cache_key = generate_cache_key(prefix, func.__name__, *args, **kwargs)
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            client = get_redis()
            if not client:
                return func(*args, **kwargs)
            
            cache_key = generate_cache_key(prefix, func.__name__, *args, **kwargs)
            cached_value = cache_get(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            cache_set(cache_key, result, ttl)
            return result
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator
