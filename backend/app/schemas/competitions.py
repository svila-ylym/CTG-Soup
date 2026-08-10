from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.database import CompetitionScoreType, CompetitionStatus
from app.schemas.common import PageResponse


class CompetitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=50000)
    start_time: datetime
    end_time: datetime
    required_tag_ids: list[int] = Field(default_factory=list)
    custom_tags: list[str] = Field(default_factory=list)
    score_type: Literal[CompetitionScoreType.AVERAGE] = CompetitionScoreType.AVERAGE
    top_n: int = Field(default=10, ge=1, le=100)
    custom_page_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("required_tag_ids")
    @classmethod
    def unique_positive_tag_ids(cls, value: list[int]) -> list[int]:
        if any(tag_id <= 0 for tag_id in value):
            raise ValueError("标签 ID 必须为正整数")
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def valid_time_range(self) -> "CompetitionCreate":
        china_timezone = timezone(timedelta(hours=8))
        if self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=china_timezone)
        if self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=china_timezone)
        self.start_time = self.start_time.astimezone(timezone.utc).replace(tzinfo=None)
        self.end_time = self.end_time.astimezone(timezone.utc).replace(tzinfo=None)
        if self.start_time >= self.end_time:
            raise ValueError("开始时间必须早于结束时间")
        return self


class CompetitionEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    soup_id: int
    author_uid: int
    final_score: float
    rank: int | None = None
    created_at: datetime


class CompetitionResponse(BaseModel):
    id: int
    creator_uid: int
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    required_tag_ids: list[int]
    score_type: CompetitionScoreType
    top_n: int
    custom_page_config: dict[str, Any]
    status: CompetitionStatus
    result_snapshot: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    settled_at: datetime | None = None
    entries: list[CompetitionEntryResponse] = Field(default_factory=list)


class CompetitionPageResponse(PageResponse[CompetitionResponse]):
    pass
