import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

import app.api.auth as auth
from app.core.config import Settings
from app.models.models import (
    EmailVerification,
    ReusableUserUid,
    User,
    UserRole,
    UserStatus,
    UserUidAllocator,
)
from app.schemas import (
    EmailVerificationRequest,
    EmailVerificationResendRequest,
    RefreshTokenRequest,
    UserCreate,
)
from app.services.email_verification import hash_verification_token
from app.services.rate_limiter import RateLimiter


class _Query:
    def __init__(self, value):
        self.value = value

    def filter(self, *_args):
        return self

    def first(self):
        return self.value


class _Database:
    def __init__(self, value):
        self.value = value

    def query(self, _model):
        return _Query(self.value)


class _SMTP:
    def __init__(self, succeeds=True):
        self.succeeds = succeeds
        self.tokens = []

    def send_verification_email(self, _email, _username, token):
        self.tokens.append(token)
        return self.succeeds


class _EventuallySuccessfulSMTP:
    def __init__(self):
        self.attempts = 0

    def send_verification_email(self, _email, _username, _token):
        self.attempts += 1
        return self.attempts == 3


class _DenyingLimiter:
    def __init__(self):
        self.calls = []

    def allow(self, scope, key, limit, window_seconds):
        self.calls.append((scope, key, limit, window_seconds))
        return False


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            EmailVerification.__table__,
            UserUidAllocator.__table__,
            ReusableUserUid.__table__,
        ],
    )
    with Session(engine) as value:
        yield value


@pytest.fixture(autouse=True)
def isolated_rate_limiter(monkeypatch):
    monkeypatch.setattr(auth, "rate_limiter", RateLimiter(redis_client=None))


def _registration() -> UserCreate:
    return UserCreate(
        username="new-user",
        nickname="New User",
        email="new-user@example.com",
        password="Password1",
    )


def test_tokens_use_string_subject_and_explicit_types():
    access = auth.create_access_token({"sub": 42})
    refresh = auth.create_refresh_token({"sub": 42})

    access_payload = jwt.decode(access, auth.settings.SECRET_KEY, algorithms=[auth.settings.ALGORITHM])
    refresh_payload = jwt.decode(refresh, auth.settings.SECRET_KEY, algorithms=[auth.settings.ALGORITHM])

    assert access_payload["sub"] == "42"
    assert access_payload["token_type"] == "access"
    assert refresh_payload["sub"] == "42"
    assert refresh_payload["token_type"] == "refresh"


def test_access_decoder_rejects_refresh_tokens():
    token = auth.create_refresh_token({"sub": 42})

    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token(token, expected_type="access")

    assert exc_info.value.status_code == 401


def test_refresh_decoder_rejects_access_tokens():
    token = auth.create_access_token({"sub": 42})

    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token(token, expected_type="refresh")

    assert exc_info.value.status_code == 401


def test_pending_email_user_cannot_log_in(monkeypatch):
    user = SimpleNamespace(
        uid=42,
        username="pending-user",
        hashed_password="hash",
        role=UserRole.USER,
        status=UserStatus.PENDING_EMAIL,
    )
    monkeypatch.setattr(auth, "verify_password", lambda *_args: True)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.login(
                SimpleNamespace(username="pending-user", password="Password1"),
                _Database(user),
            )
        )

    assert exc_info.value.status_code == 403
    assert "邮箱" in exc_info.value.detail


def test_refresh_request_uses_json_body_schema():
    request = RefreshTokenRequest.model_validate({"refresh_token": "token"})

    assert request.refresh_token == "token"


def test_registration_stores_only_token_hash_and_leaves_user_pending(monkeypatch, session):
    smtp = _SMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)

    user = asyncio.run(auth.register(_registration(), session))
    verification = session.exec(select(EmailVerification)).one()

    assert user.status == UserStatus.PENDING_EMAIL
    assert user.role == UserRole.ROOT
    assert len(smtp.tokens) == 1
    assert verification.token_hash == hash_verification_token(smtp.tokens[0])
    assert verification.token_hash != smtp.tokens[0]


def test_email_verification_activates_user_and_consumes_token(monkeypatch, session):
    smtp = _SMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)
    user = asyncio.run(auth.register(_registration(), session))

    asyncio.run(
        auth.verify_email(
            EmailVerificationRequest(token=smtp.tokens[0]),
            session,
        )
    )
    session.refresh(user)
    verification = session.exec(select(EmailVerification)).one()

    assert user.status == UserStatus.ACTIVE
    assert verification.used_at is not None


def test_used_verification_token_for_active_user_is_idempotent(monkeypatch, session):
    smtp = _SMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)
    asyncio.run(auth.register(_registration(), session))
    request = EmailVerificationRequest(token=smtp.tokens[0])

    first = asyncio.run(auth.verify_email(request, session))
    second = asyncio.run(auth.verify_email(request, session))

    assert first["message"] == "邮箱验证成功，请登录"
    assert second == {"message": "邮箱已验证"}


def test_expired_and_unknown_verification_tokens_have_distinct_codes(
    monkeypatch,
    session,
):
    smtp = _SMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)
    asyncio.run(auth.register(_registration(), session))
    verification = session.exec(select(EmailVerification)).one()
    verification.expires_at = datetime.utcnow() - timedelta(seconds=1)
    session.commit()

    with pytest.raises(HTTPException) as expired_info:
        asyncio.run(
            auth.verify_email(
                EmailVerificationRequest(token=smtp.tokens[0]),
                session,
            )
        )
    with pytest.raises(HTTPException) as invalid_info:
        asyncio.run(
            auth.verify_email(
                EmailVerificationRequest(token="x" * 40),
                session,
            )
        )

    assert expired_info.value.detail["code"] == "VERIFICATION_EXPIRED"
    assert invalid_info.value.detail["code"] == "VERIFICATION_INVALID"


def test_smtp_failure_keeps_pending_account_for_resend(monkeypatch, session):
    monkeypatch.setattr(auth, "smtp_service", _SMTP(succeeds=False), raising=False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.register(_registration(), session))

    assert exc_info.value.status_code == 503
    user = session.exec(select(User)).one()
    assert user.status == UserStatus.PENDING_EMAIL


def test_registration_retries_email_delivery_before_returning_success(monkeypatch, session):
    smtp = _EventuallySuccessfulSMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)

    user = asyncio.run(auth.register(_registration(), session))

    assert user.status == UserStatus.PENDING_EMAIL
    assert smtp.attempts == 3


def test_registration_is_limited_before_creating_an_account(monkeypatch, session):
    limiter = _DenyingLimiter()
    monkeypatch.setattr(auth, "rate_limiter", limiter)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(auth.register(_registration(), session))

    assert exc_info.value.status_code == 429
    assert session.exec(select(User)).all() == []
    assert limiter.calls == [
        ("email-ip", "unknown", auth.settings.EMAIL_VERIFICATION_IP_LIMIT, auth.settings.EMAIL_VERIFICATION_IP_WINDOW_SECONDS),
    ]


def test_resend_is_rate_limited_for_pending_accounts(monkeypatch, session):
    smtp = _SMTP()
    monkeypatch.setattr(auth, "smtp_service", smtp, raising=False)
    asyncio.run(auth.register(_registration(), session))

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            auth.resend_verification_email(
                EmailVerificationResendRequest(email="new-user@example.com"),
                session,
            )
        )

    assert exc_info.value.status_code == 429


def test_passwords_over_bcrypt_byte_limit_are_rejected():
    with pytest.raises(ValueError, match="72"):
        UserCreate(
            username="new-user",
            nickname="New User",
            email="new-user@example.com",
            password="Aa1" + "密" * 24,
        )


@pytest.mark.parametrize(
    "secret",
    ["short", "your-secret-key-change-in-production", "replace-with-a-random-secret-at-least-32-characters-long"],
)
def test_insecure_jwt_secrets_are_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY=secret)
