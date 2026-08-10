from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.database import UserRole
from app.schemas.common import PageResponse


class PublicProfileUser(BaseModel):
    uid: int
    username: str
    nickname: str
    avatar_url: str | None = None
    profile_background_url: str | None = None
    bio: str | None = None
    role: UserRole
    level: int
    level_band: str
    experience_points: int
    level_start: int
    next_level_start: int | None
    registration_date: str = "2026-08-10"
    created_at: datetime


class ProfileStats(BaseModel):
    post_count: int
    soup_count: int
    follower_count: int
    following_count: int
    like_received: int


class ProfileRelation(BaseModel):
    is_self: bool
    is_following: bool
    is_friend: bool
    is_blocked: bool


class ProfileSoupSummary(BaseModel):
    id: int
    title: str
    puzzle_excerpt: str
    genre: str
    soup_color: str
    average_score: float
    rating_count: int
    like_count: int
    favorite_count: int
    created_at: datetime


class ProfileSoupPage(PageResponse[ProfileSoupSummary]):
    pass


class PublicProfileResponse(BaseModel):
    user: PublicProfileUser
    stats: ProfileStats
    relation: ProfileRelation
    featured_soups: list[ProfileSoupSummary]
    soups: ProfileSoupPage


class FeaturedSoupInput(BaseModel):
    soup_ids: list[int] = Field(default_factory=list, max_length=5)

    @field_validator("soup_ids")
    @classmethod
    def unique_positive_ids(cls, values: list[int]) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("作品 ID 必须为正整数")
        if len(set(values)) != len(values):
            raise ValueError("代表作不能重复")
        return values
