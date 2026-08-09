from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


RecipientMode = Literal["selected", "all"]


class MarkdownPreviewRequest(BaseModel):
    markdown: str = Field(min_length=1, max_length=50000)


class MarkdownPreviewResponse(BaseModel):
    rendered_html: str


class SystemMessageCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    markdown: str = Field(min_length=1, max_length=50000)
    recipient_mode: RecipientMode
    recipient_uids: list[int] = Field(default_factory=list, max_length=10000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=5)

    @field_validator("title", "markdown")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("内容不能为空")
        return normalized

    @field_validator("recipient_uids", "attachment_ids")
    @classmethod
    def unique_positive_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("ID 必须为正整数")
        if len(values) != len(set(values)):
            raise ValueError("ID 不能重复")
        return values


class MessageAttachmentResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    size: int
    sha256: str
    created_at: datetime

    class Config:
        from_attributes = True


class SystemMessageSummary(BaseModel):
    id: int
    title: str
    sender_uid: int
    is_read: bool
    attachment_count: int
    created_at: datetime


class SystemMessageDetail(SystemMessageSummary):
    markdown: str
    rendered_html: str
    read_at: datetime | None = None
    attachments: list[MessageAttachmentResponse]


class SystemMessagePage(BaseModel):
    items: list[SystemMessageSummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class SystemMessageSendResponse(BaseModel):
    id: int
    title: str
    recipient_mode: RecipientMode
    recipient_count: int
    attachment_count: int
    created_at: datetime
