"""
数据模型定义 - 海龟汤社区平台
包含所有核心数据表：用户、帖子、海龟汤、评论、评分、社交关系、比赛、成就、消息等
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ==================== 枚举类型 ====================
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ROOT = "root"

class UserStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"
    SILENCED = "silenced"

class PunishmentType(str, Enum):
    BAN = "ban"
    SILENCE = "silence"
    DELETE_CONTENT = "delete_content"
    DISABLE_COMMENT = "disable_comment"
    RATE_LIMIT = "rate_limit"

class PostType(str, Enum):
    NORMAL = "normal"
    VOTE = "vote"
    SOUP = "soup"

class CommentTargetType(str, Enum):
    POST = "post"
    SOUP = "soup"

class LikeTargetType(str, Enum):
    POST = "post"
    SOUP = "soup"
    COMMENT = "comment"

class FavoriteTargetType(str, Enum):
    POST = "post"
    SOUP = "soup"

class CompetitionScoreType(str, Enum):
    AVERAGE = "average"
    TOP_SCORE = "top_score"

class CompetitionStatus(str, Enum):
    PENDING = "pending"
    ONGOING = "ongoing"
    COMPLETED = "completed"

class AchievementConditionType(str, Enum):
    REGISTER_DAYS = "register_days"
    POST_COUNT = "post_count"
    SOUP_COUNT = "soup_count"
    FRIEND_COUNT = "friend_count"
    TOTAL_LIKES = "total_likes"
    TOTAL_VIEWS = "total_views"
    SIGNIN_DAYS = "signin_days"

class NotificationType(str, Enum):
    MENTION = "mention"
    COMMENT_REPLY = "comment_reply"
    RATING = "rating"
    REPORT_RESULT = "report_result"
    PUNISHMENT = "punishment"
    PUNISHMENT_REVOKED = "punishment_revoked"
    ROLE_CHANGED = "role_changed"
    ACHIEVEMENT = "achievement"
    COMPETITION_START = "competition_start"
    COMPETITION_END = "competition_end"
    SYSTEM = "system"

class ReportTargetType(str, Enum):
    POST = "post"
    COMMENT = "comment"
    SOUP = "soup"
    MESSAGE = "message"
    USER = "user"

class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    REJECTED = "rejected"

# ==================== 用户系统 ====================
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    uid: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    nickname: str
    email: str = Field(unique=True, index=True)
    hashed_password: str
    role: UserRole = Field(default=UserRole.USER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    points: int = Field(default=0)
    last_signin: Optional[datetime] = None
    consecutive_signin_days: int = Field(default=0)
    notification_prefs: dict = Field(default_factory=dict, sa_column_kwargs={"server_default": "{}"})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 处罚系统 ====================
class Punishment(SQLModel, table=True):
    __tablename__ = "punishments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    target_uid: int = Field(foreign_key="users.uid", index=True)
    operator_uid: int = Field(foreign_key="users.uid")
    punishment_type: PunishmentType
    reason: str
    start_time: datetime
    end_time: Optional[datetime] = None
    is_revoked: bool = Field(default=False)
    revoked_by: Optional[int] = Field(default=None, foreign_key="users.uid")
    revoked_at: Optional[datetime] = None
    related_content_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 帖子系统 ====================
class Post(SQLModel, table=True):
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    title: str
    content: str
    section: str = Field(default="general")
    post_type: PostType = Field(default=PostType.NORMAL)
    tags: list = Field(default_factory=list, sa_column_kwargs={"server_default": "[]"})
    status: str = Field(default="published")
    view_count: int = Field(default=0)
    like_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    favorite_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 评论系统 ====================
class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: CommentTargetType
    target_id: int
    content: str
    parent_id: Optional[int] = Field(default=None, foreign_key="comments.id")
    status: str = Field(default="published")
    like_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 海龟汤系统 ====================
class Soup(SQLModel, table=True):
    __tablename__ = "soups"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    title: str
    puzzle: str
    solution: str
    tags: list = Field(default_factory=list, sa_column_kwargs={"server_default": "[]"})
    avg_rating: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    bayesian_rating: float = Field(default=0.0)
    like_count: int = Field(default=0)
    favorite_count: int = Field(default=0)
    view_count: int = Field(default=0)
    status: str = Field(default="published")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 评分系统 ====================
class Rating(SQLModel, table=True):
    __tablename__ = "ratings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 点赞与收藏 ====================
class Like(SQLModel, table=True):
    __tablename__ = "likes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: LikeTargetType
    target_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: FavoriteTargetType
    target_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 社交关系 ====================
class Follow(SQLModel, table=True):
    __tablename__ = "follows"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    follower_uid: int = Field(foreign_key="users.uid", index=True)
    followed_uid: int = Field(foreign_key="users.uid", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Blacklist(SQLModel, table=True):
    __tablename__ = "blacklists"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    blocker_uid: int = Field(foreign_key="users.uid", index=True)
    blocked_uid: int = Field(foreign_key="users.uid", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 比赛系统 ====================
class Competition(SQLModel, table=True):
    __tablename__ = "competitions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_uid: int = Field(foreign_key="users.uid")
    name: str
    description: str
    start_time: datetime
    end_time: datetime
    required_tags: list = Field(default_factory=list, sa_column_kwargs={"server_default": "[]"})
    score_type: CompetitionScoreType = Field(default=CompetitionScoreType.AVERAGE)
    top_n: int = Field(default=10)
    custom_page_config: dict = Field(default_factory=dict, sa_column_kwargs={"server_default": "{}"})
    status: CompetitionStatus = Field(default=CompetitionStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None

class CompetitionEntry(SQLModel, table=True):
    __tablename__ = "competition_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    competition_id: int = Field(foreign_key="competitions.id", index=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    final_score: float
    rank: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 成就系统 ====================
class Achievement(SQLModel, table=True):
    __tablename__ = "achievements"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True)
    name: str
    description: str
    icon_url: Optional[str] = None
    title_id: Optional[int] = Field(default=None, foreign_key="titles.id")
    condition_type: AchievementConditionType
    condition_params: dict = Field(default_factory=dict, sa_column_kwargs={"server_default": "{}"})
    is_repeatable: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Title(SQLModel, table=True):
    __tablename__ = "titles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    icon_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserAchievement(SQLModel, table=True):
    __tablename__ = "user_achievements"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    achievement_id: int = Field(foreign_key="achievements.id", index=True)
    current_value: float = Field(default=0.0)
    achieved_at: Optional[datetime] = None
    is_achieved: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 消息系统 ====================
class PrivateMessage(SQLModel, table=True):
    __tablename__ = "private_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_uid: int = Field(foreign_key="users.uid", index=True)
    receiver_uid: int = Field(foreign_key="users.uid", index=True)
    content: str
    is_read: bool = Field(default=False)
    sender_deleted: bool = Field(default=False)
    receiver_deleted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    recipient_uid: int = Field(foreign_key="users.uid", index=True)
    notification_type: NotificationType
    title: str
    content: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 举报系统 ====================
class Report(SQLModel, table=True):
    __tablename__ = "reports"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    reporter_uid: int = Field(foreign_key="users.uid")
    target_type: ReportTargetType
    target_id: int
    reason: str
    status: ReportStatus = Field(default=ReportStatus.PENDING)
    handler_uid: Optional[int] = Field(default=None, foreign_key="users.uid")
    handle_result: Optional[str] = None
    handled_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 操作日志 ====================
class OperationLog(SQLModel, table=True):
    __tablename__ = "operation_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    operator_uid: int = Field(foreign_key="users.uid", index=True)
    operator_roles: list = Field(default_factory=list, sa_column_kwargs={"server_default": "[]"})
    action_type: str
    target_type: str
    target_id: Optional[int] = None
    details: dict = Field(default_factory=dict, sa_column_kwargs={"server_default": "{}"})
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 签到记录 ====================
class SigninRecord(SQLModel, table=True):
    __tablename__ = "signin_records"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    signin_date: datetime = Field(default_factory=datetime.utcnow)
    points_earned: int = Field(default=10)
