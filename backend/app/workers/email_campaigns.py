"""CLI worker for opt-in email campaign recipient snapshots."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Sequence

from sqlmodel import Session, select

from app.core.config import get_settings
from app.db import engine
from app.models.database import (
    EmailCampaign,
    EmailCampaignAttachment,
    EmailCampaignRecipient,
    EmailCampaignRecipientStatus,
    EmailCampaignStatus,
    OperationLog,
)
from app.utils.email import SMTPService, get_smtp_service


logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


@dataclass(frozen=True)
class BatchResult:
    claimed: int = 0
    delivered: int = 0
    failed: int = 0
    completed: int = 0


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return unescape("".join(self.parts)).strip()


def masked_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator or not local or not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def _plain_text(rendered_html: str) -> str:
    parser = _TextExtractor()
    parser.feed(rendered_html)
    parser.close()
    return parser.text()


def _private_root() -> Path:
    directory = Path(get_settings().PRIVATE_STORAGE_DIR)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    return directory.resolve()


def _attachment_bytes(attachment: EmailCampaignAttachment) -> tuple[str, bytes, str]:
    root = _private_root()
    path = (root / attachment.storage_key).resolve()
    if root != path and root not in path.parents:
        raise ValueError("attachment path is outside private storage")
    if not path.is_file() or path.stat().st_size != attachment.size:
        raise ValueError("attachment snapshot integrity check failed")
    content = path.read_bytes()
    if len(content) != attachment.size or sha256(content).hexdigest() != attachment.sha256:
        raise ValueError("attachment snapshot integrity check failed")
    return attachment.original_name, content, attachment.mime_type


def _campaign_attachments(
    db: Session,
    campaign_id: int,
) -> list[tuple[str, bytes, str]]:
    rows = db.exec(
        select(EmailCampaignAttachment)
        .where(EmailCampaignAttachment.email_campaign_id == campaign_id)
        .order_by(EmailCampaignAttachment.id)
    ).all()
    return [_attachment_bytes(row) for row in rows]


def _mark_campaign_completed(db: Session, campaign: EmailCampaign) -> bool:
    remaining = db.exec(
        select(EmailCampaignRecipient.id)
        .where(EmailCampaignRecipient.email_campaign_id == campaign.id)
        .where(
            EmailCampaignRecipient.status.in_(
                [
                    EmailCampaignRecipientStatus.PENDING,
                    EmailCampaignRecipientStatus.SENDING,
                ]
            )
        )
        .limit(1)
    ).first()
    if remaining is None and campaign.status != EmailCampaignStatus.CANCELLED:
        campaign.status = EmailCampaignStatus.COMPLETED
        campaign.completed_at = datetime.utcnow()
        return True
    return False


def _pending_recipient(
    db: Session,
    processed_ids: set[int],
) -> EmailCampaignRecipient | None:
    statement = (
        select(EmailCampaignRecipient)
        .join(
            EmailCampaign,
            EmailCampaign.id == EmailCampaignRecipient.email_campaign_id,
        )
        .where(EmailCampaignRecipient.status == EmailCampaignRecipientStatus.PENDING)
        .where(EmailCampaignRecipient.attempts < MAX_ATTEMPTS)
        .where(
            EmailCampaign.status.in_(
                [EmailCampaignStatus.QUEUED, EmailCampaignStatus.SENDING]
            )
        )
        .order_by(EmailCampaignRecipient.id)
        .limit(1)
    )
    if processed_ids:
        statement = statement.where(EmailCampaignRecipient.id.not_in(processed_ids))
    if db.get_bind().dialect.name == "postgresql":
        statement = statement.with_for_update(
            skip_locked=True,
            of=EmailCampaignRecipient,
        )
    return db.exec(statement).first()


def _locked_campaign(
    db: Session,
    campaign_id: int,
) -> EmailCampaign | None:
    statement = select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    if db.get_bind().dialect.name == "postgresql":
        statement = statement.with_for_update()
    return db.exec(statement).first()


def process_campaign_batch(
    session_factory: Callable[[], Session],
    smtp_service: SMTPService,
    batch_size: int = 20,
) -> BatchResult:
    """Deliver one locked batch without ever selecting delivered snapshots."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    claimed = delivered = failed = completed = 0
    processed_ids: set[int] = set()
    for _ in range(batch_size):
        with session_factory() as db:
            recipient = _pending_recipient(db, processed_ids)
            if recipient is None:
                break
            if recipient.id is None:
                raise RuntimeError("persisted campaign recipient is missing an id")
            processed_ids.add(recipient.id)
            claimed += 1
            # Serialize cancellation against the send decision. On PostgreSQL the
            # recipient claim and campaign lock are held through this SMTP send.
            campaign = _locked_campaign(db, recipient.email_campaign_id)
            if campaign is None or campaign.status == EmailCampaignStatus.CANCELLED:
                continue

            campaign.status = EmailCampaignStatus.SENDING
            recipient.status = EmailCampaignRecipientStatus.SENDING
            success = False
            error_code = "SMTP_DELIVERY_FAILED"
            try:
                success = smtp_service.send_campaign_email(
                    recipient.recipient_email,
                    campaign.subject,
                    campaign.rendered_html,
                    _plain_text(campaign.rendered_html),
                    _campaign_attachments(db, campaign.id),
                )
            except Exception as exc:  # Do not retain exception text: it may be sensitive.
                error_code = type(exc).__name__

            recipient.attempts += 1
            if success:
                recipient.status = EmailCampaignRecipientStatus.DELIVERED
                recipient.delivered_at = datetime.utcnow()
                recipient.last_error = None
                delivered += 1
                db.add(
                    OperationLog(
                        operator_uid=campaign.creator_uid,
                        operator_roles=["root"],
                        action_type="send_email_campaign_recipient",
                        target_type="email_campaign",
                        target_id=campaign.id,
                        details={"recipient_uid": recipient.user_uid, "attempt": recipient.attempts},
                    )
                )
            else:
                failed += 1
                recipient.last_error = error_code
                retrying = recipient.attempts < MAX_ATTEMPTS
                recipient.status = (
                    EmailCampaignRecipientStatus.PENDING
                    if retrying
                    else EmailCampaignRecipientStatus.FAILED
                )
                logger.warning(
                    "Campaign delivery failed campaign_id=%s recipient=%s reason=%s",
                    campaign.id,
                    masked_email(recipient.recipient_email),
                    error_code,
                )
                db.add(
                    OperationLog(
                        operator_uid=campaign.creator_uid,
                        operator_roles=["root"],
                        action_type=(
                            "retry_email_campaign_recipient"
                            if retrying
                            else "fail_email_campaign_recipient"
                        ),
                        target_type="email_campaign",
                        target_id=campaign.id,
                        details={"recipient_uid": recipient.user_uid, "attempt": recipient.attempts},
                    )
                )
            if _mark_campaign_completed(db, campaign):
                completed += 1
            db.commit()
    return BatchResult(
        claimed=claimed,
        delivered=delivered,
        failed=failed,
        completed=completed,
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=20)
    args = parser.parse_args(argv)
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    result = process_campaign_batch(lambda: Session(engine), get_smtp_service(), args.batch_size)
    print(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    main()
