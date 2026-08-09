from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.database import AchievementConditionType, NotificationType, PostType
from app.schemas.common import PageResponse


class UserSummary(BaseModel):
    uid: int
    username: str
    nickname: str
    avatar_url: str | None = None


class MentionRef(BaseModel):
    uid: int
    username: str
    start_offset: int
    end_offset: int


class PostCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    section: str = Field(default="general", min_length=1, max_length=50)
    post_type: PostType = PostType.NORMAL
    tags: list[str] = Field(default_factory=list, max_length=10)


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    section: str | None = Field(default=None, min_length=1, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=10)


class PostResponse(BaseModel):
    id: int
    author_uid: int
    author: UserSummary
    title: str
    content: str
    section: str
    post_type: PostType
    tags: list[str]
    status: str
    like_count: int
    comment_count: int
    favorite_count: int
    view_count: int
    created_at: datetime
    updated_at: datetime
    mentions: list[MentionRef] = Field(default_factory=list)


class PostPageResponse(PageResponse[PostResponse]):
    pass


class PostCommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_id: int | None = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("评论不能为空")
        return normalized


class PostCommentResponse(BaseModel):
    id: int
    author_uid: int
    author: UserSummary
    content: str
    parent_id: int | None = None
    mentions: list[MentionRef] = Field(default_factory=list)
    created_at: datetime
    replies: list["PostCommentResponse"] = Field(default_factory=list)


class PostCommentPageResponse(PageResponse[PostCommentResponse]):
    pass


class TargetUserAction(BaseModel):
    target_uid: int = Field(gt=0)


class FollowResponse(BaseModel):
    follower_uid: int
    followed_uid: int
    active: bool


class BlacklistResponse(BaseModel):
    blocker_uid: int
    blocked_uid: int
    active: bool


class UserPageResponse(PageResponse[UserSummary]):
    pass


class PrivateMessageCreate(BaseModel):
    receiver_uid: int = Field(gt=0)
    content: str = Field(min_length=1, max_length=5000)


class PrivateMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_uid: int
    receiver_uid: int
    sender: UserSummary
    receiver: UserSummary
    content: str
    is_read: bool
    created_at: datetime


class PrivateMessagePageResponse(PageResponse[PrivateMessageResponse]):
    pass


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recipient_uid: int
    notification_type: NotificationType
    title: str
    content: str
    related_entity_type: str | None = None
    related_entity_id: int | None = None
    is_read: bool
    created_at: datetime


class NotificationPageResponse(PageResponse[NotificationResponse]):
    pass


class AchievementCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    icon_url: str | None = None
    condition_type: AchievementConditionType
    condition_params: dict[str, Any] = Field(default_factory=dict)
    is_repeatable: bool = False


class AchievementResponse(AchievementCreate):
    id: int
    title_id: int | None = None
    created_at: datetime


class AchievementPageResponse(PageResponse[AchievementResponse]):
    pass


class UserAchievementResponse(BaseModel):
    id: int
    user_uid: int
    achievement_id: int
    achievement: AchievementResponse
    current_value: float
    is_achieved: bool
    achieved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserAchievementPageResponse(PageResponse[UserAchievementResponse]):
    pass


class SearchPostResponse(BaseModel):
    id: int
    author_uid: int
    title: str
    excerpt: str
    section: str
    created_at: datetime


class SearchPostPageResponse(PageResponse[SearchPostResponse]):
    pass


class SearchSoupResponse(BaseModel):
    id: int
    author_uid: int
    title: str
    puzzle_excerpt: str
    average_score: float
    rating_count: int
    favorite_count: int
    created_at: datetime


class SearchSoupPageResponse(PageResponse[SearchSoupResponse]):
    pass
