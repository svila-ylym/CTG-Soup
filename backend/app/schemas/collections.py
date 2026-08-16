"""Request and response schemas for soup collections."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import PageResponse
from app.schemas.soups import AuthorSummary


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or "<" in normalized or ">" in normalized:
            raise ValueError("合集名称不能为空或包含 HTML")
        return normalized

    @field_validator("description")
    @classmethod
    def plain_description(cls, value: str) -> str:
        if "<" in value or ">" in value:
            raise ValueError("合集简介不允许 HTML")
        return value.strip()


class CollectionUpdate(CollectionCreate):
    pass


class CollectionSummary(BaseModel):
    id: int
    owner_uid: int
    name: str
    description: str
    soup_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class CollectionSoupSummary(BaseModel):
    id: int
    title: str
    puzzle_excerpt: str
    genre: str
    soup_color: str
    average_score: float
    rating_count: int
    like_count: int
    competition_colors: list[str] = Field(default_factory=list)
    is_hall_of_fame: bool = False
    created_at: datetime


class CollectionDetail(CollectionSummary):
    author: AuthorSummary
    soups: PageResponse[CollectionSoupSummary]


class CollectionPage(PageResponse[CollectionSummary]):
    pass


class CollectionMinePage(PageResponse[CollectionSummary]):
    pass
