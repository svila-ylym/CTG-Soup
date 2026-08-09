from types import SimpleNamespace

from app.services import dependency_health


class _RedisProbe:
    def __init__(self, error=None):
        self.error = error

    def ping(self):
        if self.error:
            raise self.error
        return True


class _Limiter:
    def __init__(self, redis_client):
        self._redis_client = redis_client
        self._redis_status = "unknown"

    @property
    def health_status(self):
        return {
            "redis": self._redis_status,
            "fallback": "active" if self._redis_status != "available" else "standby",
        }

    def probe(self):
        if self._redis_client is None:
            self._redis_status = "disabled"
            return self._redis_status
        try:
            self._redis_client.ping()
        except OSError:
            self._redis_status = "degraded"
        else:
            self._redis_status = "available"
        return self._redis_status


def test_optional_dependency_status_probes_redis_and_elasticsearch(monkeypatch):
    monkeypatch.setattr(
        dependency_health,
        "rate_limiter",
        _Limiter(_RedisProbe()),
    )
    monkeypatch.setattr(
        dependency_health,
        "get_settings",
        lambda: SimpleNamespace(ELASTICSEARCH_URL="http://search.local"),
    )
    monkeypatch.setattr(dependency_health, "_probe_elasticsearch", lambda url: "available")

    assert dependency_health.optional_dependency_status() == {
        "redis": "available",
        "fallback": "standby",
        "elasticsearch": "available",
    }


def test_optional_dependency_status_marks_unreachable_services_degraded(monkeypatch):
    monkeypatch.setattr(
        dependency_health,
        "rate_limiter",
        _Limiter(_RedisProbe(OSError("connection refused"))),
    )
    monkeypatch.setattr(
        dependency_health,
        "get_settings",
        lambda: SimpleNamespace(ELASTICSEARCH_URL="http://search.local"),
    )
    monkeypatch.setattr(dependency_health, "_probe_elasticsearch", lambda url: "degraded")

    result = dependency_health.optional_dependency_status()

    assert result["redis"] == "degraded"
    assert result["fallback"] == "active"
    assert result["elasticsearch"] == "degraded"


def test_optional_dependency_status_reports_disabled_services(monkeypatch):
    limiter = _Limiter(None)
    limiter._redis_client = None
    limiter._redis_status = "disabled"
    monkeypatch.setattr(dependency_health, "rate_limiter", limiter)
    monkeypatch.setattr(
        dependency_health,
        "get_settings",
        lambda: SimpleNamespace(ELASTICSEARCH_URL=""),
    )

    assert dependency_health.optional_dependency_status() == {
        "redis": "disabled",
        "fallback": "active",
        "elasticsearch": "disabled",
    }
