from types import SimpleNamespace

from redis.exceptions import RedisError

from app.utils import cache


class FakeRedis:
    def __init__(self, value=None, keys=()):
        self.value = value
        self.keys = list(keys)
        self.set_calls = []
        self.delete_calls = []
        self.closed = False
        self.ping_count = 0

    def ping(self):
        self.ping_count += 1
        return True

    def get(self, key):
        return self.value

    def setex(self, key, ttl, value):
        self.set_calls.append((key, ttl, value))

    def delete(self, *keys):
        self.delete_calls.append(keys)

    def scan_iter(self, *, match, count):
        assert match == "ctg:v1:surveys:list:*"
        assert count == 2
        yield from self.keys

    def close(self):
        self.closed = True


def _settings(**overrides):
    values = {
        "REDIS_CACHE_ENABLED": True,
        "REDIS_URL": "redis://example.invalid/0",
        "REDIS_CACHE_DEFAULT_TTL": 300,
        "REDIS_CACHE_CONNECT_TIMEOUT_SECONDS": 0.25,
        "REDIS_CACHE_SOCKET_TIMEOUT_SECONDS": 0.5,
        "REDIS_CACHE_RETRY_SECONDS": 5.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _use_client(monkeypatch, client):
    cache._reset_cache_state()
    monkeypatch.setattr(cache, "_settings", _settings())
    monkeypatch.setattr(cache, "_redis_client", client)


def test_cache_key_is_stable_across_parameter_order():
    first = cache.generate_cache_key("surveys-list", page=2, status="active")
    second = cache.generate_cache_key("surveys-list", status="active", page=2)

    assert first == second
    assert first.startswith("ctg:v1:surveys-list:")
    assert len(first.rsplit(":", 1)[-1]) == 20


def test_cache_set_uses_compact_json_and_default_ttl(monkeypatch):
    client = FakeRedis()
    _use_client(monkeypatch, client)

    assert cache.cache_set("key", {"label": "海龟汤"}) is True
    assert client.set_calls == [("key", 300, '{"label":"海龟汤"}')]


def test_cache_set_rejects_non_json_values(monkeypatch):
    client = FakeRedis()
    _use_client(monkeypatch, client)

    assert cache.cache_set("key", object()) is False
    assert client.set_calls == []


def test_cache_get_deletes_corrupt_json(monkeypatch):
    client = FakeRedis(value="{broken")
    _use_client(monkeypatch, client)

    assert cache.cache_get("bad-key") is None
    assert client.delete_calls == [("bad-key",)]


def test_pattern_delete_uses_scan_batches(monkeypatch):
    client = FakeRedis(keys=("one", "two", "three", "four", "five"))
    _use_client(monkeypatch, client)

    assert cache.cache_delete_pattern("ctg:v1:surveys:list:*", batch_size=2) is True
    assert client.delete_calls == [
        ("one", "two"),
        ("three", "four"),
        ("five",),
    ]


def test_connection_failure_enters_cooldown(monkeypatch):
    cache._reset_cache_state()
    monkeypatch.setattr(cache, "_settings", _settings())
    monkeypatch.setattr(cache, "monotonic", lambda: 100.0)
    attempts = []

    def fail_from_url(*args, **kwargs):
        attempts.append((args, kwargs))
        raise RedisError("offline")

    monkeypatch.setattr(cache.redis.Redis, "from_url", staticmethod(fail_from_url))

    assert cache.get_redis() is None
    assert cache.get_redis() is None
    assert len(attempts) == 1
    assert cache._redis_retry_at == 105.0


def test_disabled_cache_never_constructs_client(monkeypatch):
    cache._reset_cache_state()
    monkeypatch.setattr(cache, "_settings", _settings(REDIS_CACHE_ENABLED=False))

    def unexpected(*args, **kwargs):
        raise AssertionError("disabled cache must not construct Redis")

    monkeypatch.setattr(cache.redis.Redis, "from_url", staticmethod(unexpected))

    assert cache.get_redis() is None
