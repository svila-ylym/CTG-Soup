from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.models import TagKind, TagStatus
from app.schemas import UploadedAssetResponse
from app.services.tag_rules import normalize_tag_name


CreateGenre = Literal["本格", "变格", "鳖汤"]
ResponseGenre = Literal["本格", "变格", "鳖汤", "未分类"]
CreateSoupColor = Literal["清汤", "红汤", "黑汤"]
ResponseSoupColor = Literal["清汤", "红汤", "黑汤", "未分类"]


def _unique_ids(values: list[int]) -> list[int]:
    if any(value <= 0 for value in values):
        raise ValueError("标签 ID 必须为正整数")
    return list(dict.fromkeys(values))


def _image_ids(values: list[int]) -> list[int]:
    if any(value <= 0 for value in values):
        raise ValueError("图片 ID 必须为正整数")
    if len(values) != len(set(values)):
        raise ValueError("图片不能重复添加")
    return values


def _normalized_custom_tags(values: list[str]) -> list[str]:
    names: list[str] = []
    slugs: set[str] = set()
    for value in values:
        name, slug = normalize_tag_name(value)
        if slug not in slugs:
            names.append(name)
            slugs.add(slug)
    return names


class SoupCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    puzzle: str = ""
    solution: str = ""
    genre: CreateGenre
    soup_color: CreateSoupColor
    main_player_count: str
    secondary_player_count: str
    tag_ids: list[int] = Field(default_factory=list)
    custom_tags: list[str] = Field(default_factory=list)
    puzzle_image_ids: list[int] = Field(default_factory=list, max_length=5)
    solution_image_ids: list[int] = Field(default_factory=list, max_length=5)
    is_revealed: bool = False

    @field_validator("title")
    @classmethod
    def non_blank_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("标题不能为空")
        return value

    @field_validator("tag_ids")
    @classmethod
    def unique_tag_ids(cls, values: list[int]) -> list[int]:
        return _unique_ids(values)

    @field_validator("custom_tags")
    @classmethod
    def normalize_custom_tags(cls, values: list[str]) -> list[str]:
        return _normalized_custom_tags(values)

    @field_validator("puzzle_image_ids", "solution_image_ids")
    @classmethod
    def unique_image_ids(cls, values: list[int]) -> list[int]:
        return _image_ids(values)

    @model_validator(mode="after")
    def limit_tags(self):
        if len(self.tag_ids) + len(self.custom_tags) > 10:
            raise ValueError("单个海龟汤最多使用10个标签")
        return self


class SoupUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    puzzle: Optional[str] = None
    solution: Optional[str] = None
    genre: Optional[CreateGenre] = None
    soup_color: Optional[CreateSoupColor] = None
    main_player_count: Optional[str] = None
    secondary_player_count: Optional[str] = None
    tag_ids: Optional[list[int]] = None
    custom_tags: Optional[list[str]] = None
    puzzle_image_ids: Optional[list[int]] = Field(default=None, max_length=5)
    solution_image_ids: Optional[list[int]] = Field(default=None, max_length=5)
    is_revealed: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def non_blank_title(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("标题不能为空")
        return value

    @field_validator("tag_ids")
    @classmethod
    def unique_tag_ids(cls, values: Optional[list[int]]) -> Optional[list[int]]:
        return _unique_ids(values) if values is not None else None

    @field_validator("custom_tags")
    @classmethod
    def normalize_custom_tags(
        cls,
        values: Optional[list[str]],
    ) -> Optional[list[str]]:
        return _normalized_custom_tags(values) if values is not None else None

    @field_validator("puzzle_image_ids", "solution_image_ids")
    @classmethod
    def unique_image_ids(cls, values: Optional[list[int]]) -> Optional[list[int]]:
        return _image_ids(values) if values is not None else None

    @model_validator(mode="after")
    def limit_tags(self):
        count = len(self.tag_ids or []) + len(self.custom_tags or [])
        if count > 10:
            raise ValueError("单个海龟汤最多使用10个标签")
        return self


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    kind: TagKind
    status: TagStatus
    description: Optional[str] = None
    sort_order: int
    view_count: int
    usage_count: int
    created_at: datetime
    updated_at: datetime


class TagPageResponse(BaseModel):
    items: list[TagResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuthorSummary(BaseModel):
    uid: int
    username: str
    nickname: str
    level: int = 0
    level_band: str = "black"


class SoupResponse(BaseModel):
    id: int
    title: str
    puzzle: str
    solution: Optional[str]
    puzzle_images: list[UploadedAssetResponse] = Field(default_factory=list)
    solution_images: list[UploadedAssetResponse] = Field(default_factory=list)
    solution_available: bool
    is_solution_public: bool
    genre: ResponseGenre
    soup_color: ResponseSoupColor
    competition_colors: list[str] = Field(default_factory=list)
    main_player_count: str
    secondary_player_count: str
    tags: list[TagResponse]
    author_uid: int
    author: AuthorSummary
    average_score: float
    rating_count: int
    comment_count: int = Field(default=0, ge=0)
    like_count: int
    favorite_count: int
    view_count: int
    status: str
    is_liked: bool
    is_favorited: bool
    my_rating: Optional[float]
    can_manage: bool
    can_edit: bool = False
    created_at: datetime
    updated_at: datetime


class SoupPageResponse(BaseModel):
    items: list[SoupResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
