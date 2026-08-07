from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from app.core.enums import UserRole, AccountStatus


# ============ 用户相关 Schema ============

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    nickname: str = Field(..., min_length=1, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('密码长度必须至少为8位')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含数字')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    notice_preferences: Optional[Dict[str, bool]] = None


class UserResponse(UserBase):
    id: int
    uid: str
    role: UserRole
    status: AccountStatus
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    score: int
    consecutive_signin_days: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[UserRole] = None


# ============ 帖子相关 Schema ============

class PostBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str
    section: Optional[str] = None
    post_type: str = "normal"
    tags: List[str] = []
    vote_config: Optional[Dict[str, Any]] = None


class PostCreate(PostBase):
    pass


class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = None
    section: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None
    is_featured: Optional[bool] = None


class PostResponse(PostBase):
    id: int
    author_id: int
    author_username: str
    author_nickname: str
    status: str
    like_count: int
    collect_count: int
    comment_count: int
    view_count: int
    is_pinned: bool
    is_featured: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ 评论相关 Schema ============

class CommentBase(BaseModel):
    content: str
    target_type: str
    target_id: int
    parent_id: Optional[int] = None


class CommentCreate(CommentBase):
    pass


class CommentResponse(CommentBase):
    id: int
    author_id: int
    author_username: str
    author_nickname: str
    status: str
    like_count: int
    created_at: datetime
    replies: List['CommentResponse'] = []
    
    class Config:
        from_attributes = True


# ============ 海龟汤相关 Schema ============

class TurtleSoupBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    puzzle: str
    solution: str
    tags: List[str] = []


class TurtleSoupCreate(TurtleSoupBase):
    pass


class TurtleSoupUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    puzzle: Optional[str] = None
    solution: Optional[str] = None
    tags: Optional[List[str]] = None
    is_revealed: Optional[bool] = None


class RatingCreate(BaseModel):
    score: float = Field(..., ge=1.0, le=10.0)
    
    @field_validator('score')
    @classmethod
    def validate_score(cls, v):
        # 检查是否为0.5的倍数
        if v * 2 != int(v * 2):
            raise ValueError('评分必须是0.5的倍数')
        return v


class TurtleSoupResponse(TurtleSoupBase):
    id: int
    author_id: int
    author_username: str
    author_nickname: str
    average_score: float
    rating_count: int
    like_count: int
    collect_count: int
    view_count: int
    is_revealed: bool
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ 比赛相关 Schema ============

class CompetitionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str
    start_time: datetime
    end_time: datetime
    entry_tags: List[str]
    scoring_method: str
    top_n: int = 10
    custom_page_config: Optional[Dict[str, Any]] = None


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionResponse(CompetitionBase):
    id: int
    creator_id: int
    status: str
    result_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============ 社交相关 Schema ============

class FollowAction(BaseModel):
    target_user_id: int


class BlacklistAction(BaseModel):
    target_user_id: int


# ============ 私信相关 Schema ============

class PrivateMessageBase(BaseModel):
    receiver_id: int
    content: str


class PrivateMessageCreate(PrivateMessageBase):
    pass


class PrivateMessageResponse(PrivateMessageBase):
    id: int
    sender_id: int
    sender_username: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 通知相关 Schema ============

class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    content: str
    related_entity_id: Optional[int] = None
    related_entity_type: Optional[str] = None
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 举报相关 Schema ============

class ReportCreate(BaseModel):
    target_type: str
    target_id: int
    reason: str


class ReportResponse(BaseModel):
    id: int
    reporter_id: int
    target_type: str
    target_id: int
    reason: str
    status: str
    handler_id: Optional[int] = None
    handle_result: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 成就相关 Schema ============

class AchievementDefinitionBase(BaseModel):
    code: str
    name: str
    description: str
    icon_url: Optional[str] = None
    condition_type: str
    condition_params: Dict[str, Any]
    is_repeatable: bool = False


class AchievementDefinitionCreate(AchievementDefinitionBase):
    pass


class AchievementDefinitionResponse(AchievementDefinitionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    id: int
    achievement_id: int
    achievement_name: str
    achievement_icon: Optional[str] = None
    current_value: float
    is_completed: bool
    completed_at: Optional[datetime] = None
    granted_count: int
    
    class Config:
        from_attributes = True


# ============ 处罚相关 Schema ============

class PunishmentCreate(BaseModel):
    target_user_id: int
    punishment_type: str
    reason: str
    end_time: Optional[datetime] = None
    related_content_id: Optional[int] = None
    related_content_type: Optional[str] = None


class PunishmentRevoke(BaseModel):
    revoke_reason: str


class PunishmentResponse(BaseModel):
    id: int
    target_user_id: int
    operator_id: int
    punishment_type: str
    reason: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_revoked: bool
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[int] = None
    revoke_reason: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 操作日志相关 Schema ============

class OperationLogResponse(BaseModel):
    id: int
    operator_id: int
    operator_username: str
    operator_roles: List[str]
    action_type: str
    target_type: Optional[str] = None
    target_id: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============ 分页响应 Schema ============

class PageResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True
