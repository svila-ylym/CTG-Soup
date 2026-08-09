"""Durable, opt-in-only email campaign queue operations."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.database import (
    EmailCampaign,
    EmailCampaignAttachment,
    EmailCampaignCategory,
    EmailCampaignRecipient,
    EmailCampaignRecipientStatus,
    EmailCampaignStatus,
    MessageAttachment,
    OperationLog,
    User,
    UserStatus,
)
from app.schemas.email_campaigns import EmailCampaignCreate, EmailCampaignSummary
from app.services.safe_markdown import render_safe_markdown


MAX_ATTACHMENT_COUNT = 5
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_TOTAL_ATTACHMENT_BYTES = 25 * 1024 * 1024


def _api_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def eligible_users_statement(recipient_mode: str, recipient_uids: list[int]):
    statement = select(User).where(
        User.status == UserStatus.ACTIVE,
        User.allow_bulk_email.is_(True),
    )
    if recipient_mode == "selected":
        statement = statement.where(User.uid.in_(recipient_uids))
    return statement


def _recipient_snapshot(
    db: Session,
    recipient_mode: str,
    recipient_uids: list[int],
) -> tuple[int, list[User]]:
    if recipient_mode == "selected":
        if not recipient_uids:
            raise _api_error(422, "RECIPIENT_REQUIRED", "请至少选择一个收件人")
        selected_users = db.exec(
            select(User)
            .where(
                User.status == UserStatus.ACTIVE,
                User.uid.in_(recipient_uids),
            )
            .order_by(User.uid)
        ).all()
        if {user.uid for user in selected_users} != set(recipient_uids):
            raise _api_error(422, "RECIPIENT_INVALID", "收件人不存在或未激活")
        selected_count = len(selected_users)
        recipients = [user for user in selected_users if user.allow_bulk_email]
    else:
        selected_count = db.exec(
            select(func.count()).select_from(User).where(User.status == UserStatus.ACTIVE)
        ).one()
        recipients = db.exec(
            eligible_users_statement(recipient_mode, recipient_uids).order_by(User.uid)
        ).all()
    return int(selected_count), recipients


def _campaign_attachments(
    db: Session,
    uploader_uid: int,
    attachment_ids: list[int],
    *,
    lock: bool,
) -> list[MessageAttachment]:
    if not attachment_ids:
        return []
    statement = (
        select(MessageAttachment)
        .where(MessageAttachment.id.in_(attachment_ids))
        .order_by(MessageAttachment.id)
    )
    if lock:
        statement = statement.with_for_update()
    attachments = db.exec(statement).all()
    if (
        len(attachments) != len(attachment_ids)
        or any(
            attachment.uploader_uid != uploader_uid
            or attachment.system_message_id is not None
            for attachment in attachments
        )
    ):
        raise _api_error(
            status.HTTP_403_FORBIDDEN,
            "ATTACHMENT_NOT_OWNED",
            "附件不存在、已使用或不属于当前用户",
        )
    if (
        len(attachments) > MAX_ATTACHMENT_COUNT
        or any(item.size > MAX_ATTACHMENT_BYTES for item in attachments)
        or sum(item.size for item in attachments) > MAX_TOTAL_ATTACHMENT_BYTES
    ):
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ATTACHMENT_LIMIT_EXCEEDED",
            "附件数量或大小超过限制",
        )
    return attachments


def _require_campaign(db: Session, campaign_id: int, *, lock: bool = False) -> EmailCampaign:
    statement = select(EmailCampaign).where(EmailCampaign.id == campaign_id)
    if lock:
        statement = statement.with_for_update()
    campaign = db.exec(statement).first()
    if campaign is None:
        raise _api_error(status.HTTP_404_NOT_FOUND, "CAMPAIGN_NOT_FOUND", "邮件活动不存在")
    return campaign


def _count_recipients(
    db: Session,
    campaign_id: int,
    recipient_status: EmailCampaignRecipientStatus | None = None,
) -> int:
    statement = select(func.count()).select_from(EmailCampaignRecipient).where(
        EmailCampaignRecipient.email_campaign_id == campaign_id
    )
    if recipient_status is not None:
        statement = statement.where(EmailCampaignRecipient.status == recipient_status)
    return int(db.exec(statement).one())


def campaign_summary(db: Session, campaign: EmailCampaign) -> EmailCampaignSummary:
    return EmailCampaignSummary(
        id=campaign.id,
        subject=campaign.subject,
        category=campaign.category.value,
        recipient_mode=campaign.recipient_mode,
        status=campaign.status.value,
        selected_count=campaign.selected_count,
        eligible_count=campaign.eligible_count,
        filtered_count=campaign.filtered_count,
        queued_count=campaign.queued_count,
        delivered_count=_count_recipients(
            db, campaign.id, EmailCampaignRecipientStatus.DELIVERED
        ),
        failed_count=_count_recipients(
            db, campaign.id, EmailCampaignRecipientStatus.FAILED
        ),
        attachment_count=int(
            db.exec(
                select(func.count())
                .select_from(EmailCampaignAttachment)
                .where(EmailCampaignAttachment.email_campaign_id == campaign.id)
            ).one()
        ),
        created_at=campaign.created_at,
        queued_at=campaign.queued_at,
        completed_at=campaign.completed_at,
    )


def create_campaign(
    db: Session,
    root_user: User,
    data: EmailCampaignCreate,
) -> EmailCampaignSummary:
    # Validate now for prompt feedback and repeat under a lock when queuing.
    _campaign_attachments(db, root_user.uid, data.attachment_ids, lock=False)
    selected_count, recipients = _recipient_snapshot(
        db, data.recipient_mode, data.recipient_uids
    )
    campaign = EmailCampaign(
        creator_uid=root_user.uid,
        subject=data.subject,
        markdown=data.markdown,
        rendered_html=render_safe_markdown(data.markdown),
        category=EmailCampaignCategory(data.category),
        recipient_mode=data.recipient_mode,
        recipient_uids=data.recipient_uids,
        attachment_ids=data.attachment_ids,
        selected_count=selected_count,
        eligible_count=len(recipients),
        filtered_count=selected_count - len(recipients),
    )
    db.add(campaign)
    db.flush()
    db.add(
        OperationLog(
            operator_uid=root_user.uid,
            operator_roles=[root_user.role.value],
            action_type="create_email_campaign",
            target_type="email_campaign",
            target_id=campaign.id,
            details={
                "category": campaign.category.value,
                "recipient_mode": campaign.recipient_mode,
                "selected_count": campaign.selected_count,
                "eligible_count": campaign.eligible_count,
                "filtered_count": campaign.filtered_count,
                "attachment_count": len(data.attachment_ids),
            },
        )
    )
    db.commit()
    db.refresh(campaign)
    return campaign_summary(db, campaign)


def queue_campaign(
    db: Session,
    root_user: User,
    campaign_id: int,
) -> EmailCampaignSummary:
    campaign = _require_campaign(db, campaign_id, lock=True)
    if campaign.status != EmailCampaignStatus.DRAFT:
        raise _api_error(
            status.HTTP_409_CONFLICT,
            "CAMPAIGN_NOT_DRAFT",
            "只有草稿邮件活动可以排队",
        )

    attachments = _campaign_attachments(
        db, campaign.creator_uid, campaign.attachment_ids, lock=True
    )
    selected_count, recipients = _recipient_snapshot(
        db, campaign.recipient_mode, campaign.recipient_uids
    )

    if not recipients:
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "RECIPIENT_REQUIRED",
            "没有订阅批量邮件的活跃收件人",
        )

    campaign.selected_count = selected_count
    campaign.eligible_count = len(recipients)
    campaign.filtered_count = selected_count - len(recipients)
    campaign.queued_count = len(recipients)
    campaign.status = EmailCampaignStatus.QUEUED
    campaign.queued_at = datetime.utcnow()
    for user in recipients:
        db.add(
            EmailCampaignRecipient(
                email_campaign_id=campaign.id,
                user_uid=user.uid,
                recipient_email=user.email,
            )
        )
    for attachment in attachments:
        db.add(
            EmailCampaignAttachment(
                email_campaign_id=campaign.id,
                source_attachment_id=attachment.id,
                storage_key=attachment.storage_key,
                original_name=attachment.original_name,
                mime_type=attachment.mime_type,
                size=attachment.size,
                sha256=attachment.sha256,
            )
        )
    db.add(
        OperationLog(
            operator_uid=root_user.uid,
            operator_roles=[root_user.role.value],
            action_type="queue_email_campaign",
            target_type="email_campaign",
            target_id=campaign.id,
            details={
                "selected_count": campaign.selected_count,
                "eligible_count": campaign.eligible_count,
                "filtered_count": campaign.filtered_count,
                "queued_count": campaign.queued_count,
                "attachment_count": len(attachments),
            },
        )
    )
    db.commit()
    db.refresh(campaign)
    return campaign_summary(db, campaign)


def cancel_campaign(
    db: Session,
    root_user: User,
    campaign_id: int,
) -> EmailCampaignSummary:
    campaign = _require_campaign(db, campaign_id, lock=True)
    if campaign.status in {EmailCampaignStatus.COMPLETED, EmailCampaignStatus.CANCELLED}:
        raise _api_error(
            status.HTTP_409_CONFLICT,
            "CAMPAIGN_NOT_CANCELLABLE",
            "邮件活动无法取消",
        )
    campaign.status = EmailCampaignStatus.CANCELLED
    db.add(
        OperationLog(
            operator_uid=root_user.uid,
            operator_roles=[root_user.role.value],
            action_type="cancel_email_campaign",
            target_type="email_campaign",
            target_id=campaign.id,
            details={"queued_count": campaign.queued_count},
        )
    )
    db.commit()
    db.refresh(campaign)
    return campaign_summary(db, campaign)
