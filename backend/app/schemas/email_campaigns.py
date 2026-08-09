from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


RecipientMode = Literal["selected", "all"]
CampaignCategory = Literal["notice", "promotion"]
CampaignStatus = Literal["draft", "queued", "sending", "completed", "cancelled"]


class EmailCampaignCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    markdown: str = Field(min_length=1, max_length=50000)
    category: CampaignCategory
    recipient_mode: RecipientMode
    recipient_uids: list[int] = Field(default_factory=list, max_length=10000)
    attachment_ids: list[int] = Field(default_factory=list)

    @field_validator("subject", "markdown")
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


class EmailCampaignSummary(BaseModel):
    id: int
    subject: str
    category: CampaignCategory
    recipient_mode: RecipientMode
    status: CampaignStatus
    selected_count: int
    eligible_count: int
    filtered_count: int
    queued_count: int
    delivered_count: int
    failed_count: int
    attachment_count: int
    created_at: datetime
    queued_at: datetime | None = None
    completed_at: datetime | None = None


class EmailCampaignPage(BaseModel):
    items: list[EmailCampaignSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
