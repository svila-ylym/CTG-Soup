"""Health information for optional dependencies."""

from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings
from app.services.rate_limiter import rate_limiter
from app.services.message_gateway import message_gateway


def _probe_elasticsearch(url: str) -> str:
    try:
        request = Request(url.rstrip("/"), method="GET")
        with urlopen(request, timeout=0.3) as response:
            return "available" if response.status < 500 else "degraded"
    except HTTPError as exc:
        return "available" if exc.code < 500 else "degraded"
    except (OSError, TimeoutError, URLError, ValueError):
        return "degraded"


def optional_dependency_status() -> Dict[str, str]:
    """Return diagnostic state without making optional outages fatal."""
    rate_limiter.probe()
    message_gateway.probe()
    status = rate_limiter.health_status
    elasticsearch_url = get_settings().ELASTICSEARCH_URL
    status["elasticsearch"] = (
        _probe_elasticsearch(elasticsearch_url) if elasticsearch_url else "disabled"
    )
    status.update(message_gateway.health_status)
    return status
