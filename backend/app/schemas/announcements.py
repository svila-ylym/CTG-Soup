from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def sanitize_plain_text(value: str) -> str:
    import re

    value = re.sub(r"<[^>]*>", "", value)
    return value.strip()


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    priority: int = Field(default=0, ge=0, le=100)
    expires_at: Optional[datetime] = None

    @field_validator("title", "content")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = sanitize_plain_text(value)
        if not cleaned:
            raise ValueError("文本不能为空")
        return cleaned


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    expires_at: Optional[datetime] = None

    @field_validator("title", "content")
    @classmethod
    def clean_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = sanitize_plain_text(value)
        if not cleaned:
            raise ValueError("文本不能为空")
        return cleaned


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_uid: int
    title: str
    content: str
    priority: int
    status: str
    expires_at: Optional[datetime]
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AnnouncementPageResponse(BaseModel):
    items: list[AnnouncementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TagAdminCreate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)
    kind: str = "custom"


class TagAdminUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=30)
    description: Optional[str] = Field(default=None, max_length=500)
    status: Optional[str] = None
    sort_order: Optional[int] = None


class TagMergeRequest(BaseModel):
    target_tag_id: int = Field(gt=0)
