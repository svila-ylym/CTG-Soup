from app.services.rate_limiter import RateLimiter


class _UnavailableRedis:
    def ping(self):
        raise ConnectionError("Redis is unavailable")

    def eval(self, *args, **kwargs):
        raise ConnectionError("Redis is unavailable")


class _Redis:
    def __init__(self):
        self.count = 0
        self.key = None

    def eval(self, _script, _keys, key, _window_seconds):
        self.key = key
        self.count += 1
        return self.count

    def ping(self):
        return True


def test_rate_limiter_uses_process_fallback_when_redis_is_unavailable():
    limiter = RateLimiter(redis_client=_UnavailableRedis())

    assert limiter.allow("email", "person@example.com", limit=2, window_seconds=60)
    assert limiter.allow("email", "person@example.com", limit=2, window_seconds=60)
    assert not limiter.allow("email", "person@example.com", limit=2, window_seconds=60)
    assert limiter.health_status["redis"] == "degraded"


def test_rate_limiter_uses_redis_counter_when_available():
    redis_client = _Redis()
    limiter = RateLimiter(redis_client=redis_client)

    assert limiter.allow("ip", "203.0.113.8", limit=1, window_seconds=60)
    assert not limiter.allow("ip", "203.0.113.8", limit=1, window_seconds=60)
    assert redis_client.key == "rate-limit:ip:203.0.113.8"
    assert limiter.health_status["redis"] == "available"


def test_rate_limiter_probe_refreshes_dependency_status_without_counting():
    available = RateLimiter(redis_client=_Redis())
    unavailable = RateLimiter(redis_client=_UnavailableRedis())
    disabled = RateLimiter(redis_client=None)

    assert available.probe() == "available"
    assert unavailable.probe() == "degraded"
    assert disabled.probe() == "disabled"
    assert available._redis_client.count == 0
