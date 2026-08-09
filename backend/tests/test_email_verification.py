from datetime import datetime, timedelta

import pytest

from app.core.config import Settings
from app.services.email_verification import (
    hash_verification_token,
    new_verification_token,
    verification_expiry,
)


def test_verification_tokens_are_opaque_and_unique():
    first = new_verification_token()
    second = new_verification_token()

    assert len(first) >= 40
    assert first != second


def test_verification_token_hash_is_deterministic_and_not_plaintext():
    token = "verification-token"

    digest = hash_verification_token(token)

    assert digest == hash_verification_token(token)
    assert digest != token
    assert len(digest) == 64


def test_verification_expiry_uses_configured_minutes():
    now = datetime(2026, 8, 8, 12, 0, 0)

    assert verification_expiry(now, minutes=30) == now + timedelta(minutes=30)


def test_pending_email_status_is_available():
    from app.models.models import UserStatus

    assert UserStatus.PENDING_EMAIL.value == "pending_email"


def test_public_web_url_prefers_override_and_falls_back_to_legacy_app_url():
    public = Settings(
        PUBLIC_WEB_URL="https://ctg.example/",
        APP_URL="https://legacy.example/",
    )
    legacy = Settings(PUBLIC_WEB_URL=None, APP_URL="https://legacy.example/")

    assert public.public_web_url == "https://ctg.example"
    assert legacy.public_web_url == "https://legacy.example"


def test_public_web_url_rejects_non_http_urls():
    settings = Settings(PUBLIC_WEB_URL="ctg.example")

    with pytest.raises(ValueError, match="absolute HTTP"):
        _ = settings.public_web_url
