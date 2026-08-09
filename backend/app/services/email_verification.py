"""Pure helpers for opaque email-verification tokens."""

import hashlib
import secrets
from datetime import datetime, timedelta


def new_verification_token() -> str:
    return secrets.token_urlsafe(32)


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verification_expiry(now: datetime, minutes: int = 30) -> datetime:
    return now + timedelta(minutes=minutes)
