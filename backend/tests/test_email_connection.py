from types import SimpleNamespace
from unittest.mock import Mock

import app.utils.email as email_module


def _settings(*, use_ssl: bool, public_web_url: str = "https://ctg.example") -> SimpleNamespace:
    return SimpleNamespace(
        SMTP_HOST="smtp.126.com",
        SMTP_PORT=465 if use_ssl else 587,
        SMTP_USER="mailer@example.com",
        SMTP_PASSWORD="authorization-code",
        SMTP_FROM_EMAIL="mailer@example.com",
        SMTP_USE_SSL=use_ssl,
        public_web_url=public_web_url,
    )


def test_create_connection_uses_smtp_ssl(monkeypatch):
    connection = Mock()
    smtp_ssl = Mock(return_value=connection)
    smtp = Mock()
    monkeypatch.setattr(email_module, "settings", _settings(use_ssl=True))
    monkeypatch.setattr(email_module.smtplib, "SMTP_SSL", smtp_ssl)
    monkeypatch.setattr(email_module.smtplib, "SMTP", smtp)

    result = email_module.SMTPService()._create_connection()

    assert result is connection
    smtp_ssl.assert_called_once_with("smtp.126.com", 465)
    smtp.assert_not_called()
    connection.starttls.assert_not_called()
    connection.login.assert_called_once_with("mailer@example.com", "authorization-code")


def test_create_connection_uses_starttls_when_ssl_is_disabled(monkeypatch):
    connection = Mock()
    smtp = Mock(return_value=connection)
    smtp_ssl = Mock()
    monkeypatch.setattr(email_module, "settings", _settings(use_ssl=False))
    monkeypatch.setattr(email_module.smtplib, "SMTP", smtp)
    monkeypatch.setattr(email_module.smtplib, "SMTP_SSL", smtp_ssl)

    result = email_module.SMTPService()._create_connection()

    assert result is connection
    smtp.assert_called_once_with("smtp.126.com", 587)
    smtp_ssl.assert_not_called()
    connection.starttls.assert_called_once_with()
    connection.login.assert_called_once_with("mailer@example.com", "authorization-code")


def test_verification_and_reset_links_use_public_web_url(monkeypatch):
    monkeypatch.setattr(
        email_module,
        "settings",
        _settings(use_ssl=True, public_web_url="https://community.example"),
    )
    service = email_module.SMTPService()
    messages = []
    monkeypatch.setattr(
        service,
        "send_email",
        lambda to, subject, html, text: messages.append((html, text)) or True,
    )

    service.send_verification_email(
        "reader@example.com",
        "reader",
        "token-value-at-least-32-characters",
    )
    service.send_password_reset_email(
        "reader@example.com",
        "reader",
        "reset-token",
    )

    verification_html, verification_text = messages[0]
    reset_html, reset_text = messages[1]
    assert "https://community.example/verify-email?token=" in verification_html
    assert "https://community.example/verify-email?token=" in verification_text
    assert "https://community.example/reset-password?token=" in reset_html
    assert "https://community.example/reset-password?token=" in reset_text
    assert "localhost:10000" not in "".join(
        (verification_html, verification_text, reset_html, reset_text)
    )
