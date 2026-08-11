"""
数据模型定义 - 汤吧社区
包含所有核心数据表：用户、帖子、海龟汤、评论、评分、社交关系、比赛、成就、消息等
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from enum import Enum
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    JSON,
    Column,
    Enum as SAEnum,
    Text,
    UniqueConstraint,
)

# ==================== 枚举类型 ====================
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ROOT = "root"

class UserStatus(str, Enum):
    PENDING_EMAIL = "pending_email"
    ACTIVE = "active"
    BANNED = "banned"
    SILENCED = "silenced"


class ThemePreference(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

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


class MentionTargetType(str, Enum):
    POST = "post"
    COMMENT = "comment"

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


class TagKind(str, Enum):
    SYSTEM = "system"
    CUSTOM = "custom"


class TagStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AnnouncementStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    EXPIRED = "expired"


class EmailCampaignCategory(str, Enum):
    NOTICE = "notice"
    PROMOTION = "promotion"


class EmailCampaignStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENDING = "sending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EmailCampaignRecipientStatus(str, Enum):
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"

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
    avatar_asset_id: Optional[int] = Field(
        default=None,
        foreign_key="uploaded_assets.id",
    )
    bio: Optional[str] = None
    points: int = Field(default=0)
    allow_bulk_email: bool = Field(default=True, index=True)
    theme_preference: ThemePreference = Field(
        default=ThemePreference.SYSTEM,
        sa_column=Column(
            SAEnum(
                ThemePreference,
                values_callable=lambda values: [value.value for value in values],
                native_enum=False,
                length=10,
            ),
            nullable=False,
            default=ThemePreference.SYSTEM,
        ),
    )
    token_version: int = Field(default=0)
    last_signin: Optional[datetime] = None
    consecutive_signin_days: int = Field(default=0)
    notification_prefs: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON())
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def profile_background_asset_id(self) -> Optional[int]:
        value = self.notification_prefs.get("profile_background_asset_id") if isinstance(self.notification_prefs, dict) else None
        return value if isinstance(value, int) and value > 0 else None

    @property
    def profile_background_url(self) -> Optional[str]:
        value = self.notification_prefs.get("profile_background_url") if isinstance(self.notification_prefs, dict) else None
        return value if isinstance(value, str) and value else None

    @property
    def registration_date(self) -> str:
        """Return the JSON-backed registration date, with a legacy fallback."""
        value = self.notification_prefs.get("registration_date") if isinstance(self.notification_prefs, dict) else None
        return value if isinstance(value, str) and value else "2026-08-10"

    @property
    def level(self) -> int:
        return max(self.points, 0) // 100

    @property
    def level_band(self) -> str:
        bands = ("black", "yellow", "purple", "green", "bronze", "silver", "cyan", "blue", "gold", "red")
        return bands[min(self.level // 10, len(bands) - 1)]


class EmailVerification(SQLModel, table=True):
    __tablename__ = "email_verifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    token_hash: str = Field(unique=True, index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    used_at: Optional[datetime] = None


class UserUidAllocator(SQLModel, table=True):
    __tablename__ = "user_uid_allocator"

    id: int = Field(default=1, primary_key=True)
    next_uid: int = Field(ge=1)


class ReusableUserUid(SQLModel, table=True):
    __tablename__ = "reusable_user_uids"

    uid: int = Field(primary_key=True, ge=1)
    released_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class UploadedAsset(SQLModel, table=True):
    __tablename__ = "uploaded_assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_uid: int = Field(foreign_key="users.uid", index=True)
    kind: str = Field(default="image", index=True, max_length=32)
    storage_key: str = Field(unique=True, max_length=500)
    public_url: str = Field(max_length=1000)
    mime_type: str = Field(max_length=100)
    size: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class PermissionGroup(SQLModel, table=True):
    """Named permission bundle managed by administrators."""
    __tablename__ = "permission_groups"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list, sa_column=Column(JSON()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserPermissionGroup(SQLModel, table=True):
    __tablename__ = "user_permission_groups"
    user_uid: int = Field(foreign_key="users.uid", primary_key=True)
    group_id: int = Field(foreign_key="permission_groups.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    revoke_reason: Optional[str] = None
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
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON())
    )
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
class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(index=True, max_length=30)
    kind: TagKind = Field(default=TagKind.CUSTOM)
    status: TagStatus = Field(default=TagStatus.ACTIVE)
    description: Optional[str] = Field(default=None, max_length=500)
    sort_order: int = Field(default=0)
    view_count: int = Field(default=0, ge=0)
    usage_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TagAlias(SQLModel, table=True):
    __tablename__ = "tag_aliases"

    id: Optional[int] = Field(default=None, primary_key=True)
    alias_slug: str = Field(unique=True, index=True, max_length=64)
    tag_id: int = Field(foreign_key="tags.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Announcement(SQLModel, table=True):
    __tablename__ = "announcements"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    title: str = Field(max_length=200)
    content: str
    priority: int = Field(default=0, ge=0, le=100)
    status: AnnouncementStatus = Field(default=AnnouncementStatus.DRAFT, index=True)
    expires_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SoupCollection(SQLModel, table=True):
    __tablename__ = "soup_collections"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_uid: int = Field(foreign_key="users.uid", index=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Soup(SQLModel, table=True):
    __tablename__ = "soups"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    collection_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("soup_collections.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    title: str
    puzzle: str
    solution: str
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON())
    )
    genre: str = Field(default="未分类", max_length=20, index=True)
    soup_color: str = Field(default="未分类", max_length=20, index=True)
    main_player_count: str = Field(default="", sa_column=Column(Text, nullable=False))
    secondary_player_count: str = Field(default="", sa_column=Column(Text, nullable=False))
    avg_rating: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    like_count: int = Field(default=0)
    favorite_count: int = Field(default=0)
    view_count: int = Field(default=0)
    status: str = Field(default="published")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SoupImage(SQLModel, table=True):
    __tablename__ = "soup_images"
    __table_args__ = (
        UniqueConstraint("soup_id", "asset_id", name="uq_soup_images_soup_asset"),
        UniqueConstraint(
            "soup_id",
            "placement",
            "sort_order",
            name="uq_soup_images_placement_order",
        ),
        CheckConstraint(
            "placement IN ('puzzle', 'solution')",
            name="ck_soup_images_placement",
        ),
        CheckConstraint("sort_order >= 0", name="ck_soup_images_sort_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    asset_id: int = Field(foreign_key="uploaded_assets.id", index=True)
    placement: str = Field(max_length=16, index=True)
    sort_order: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SoupTag(SQLModel, table=True):
    __tablename__ = "soup_tags"

    soup_id: int = Field(foreign_key="soups.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeaturedSoup(SQLModel, table=True):
    __tablename__ = "featured_soups"
    __table_args__ = (
        UniqueConstraint("user_uid", "soup_id", name="uq_featured_soups_user_soup"),
        UniqueConstraint("user_uid", "position", name="uq_featured_soups_user_position"),
        CheckConstraint("position >= 0 AND position < 5", name="ck_featured_soups_position"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    position: int = Field(ge=0, lt=5)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 评分系统 ====================
class Rating(SQLModel, table=True):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_uid", "soup_id", name="uq_ratings_user_soup"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 点赞与收藏 ====================
class Like(SQLModel, table=True):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("user_uid", "target_type", "target_id", name="uq_likes_user_target"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: LikeTargetType
    target_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Favorite(SQLModel, table=True):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_uid", "target_type", "target_id", name="uq_favorites_user_target"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: FavoriteTargetType
    target_id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 社交关系 ====================
class Follow(SQLModel, table=True):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_uid", "followed_uid", name="uq_follows_pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    follower_uid: int = Field(foreign_key="users.uid", index=True)
    followed_uid: int = Field(foreign_key="users.uid", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Blacklist(SQLModel, table=True):
    __tablename__ = "blacklists"
    __table_args__ = (
        UniqueConstraint("blocker_uid", "blocked_uid", name="uq_blacklists_pair"),
    )

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
    required_tag_ids: List[int] = Field(
        default_factory=list,
        sa_column=Column(JSON())
    )
    optional_tag_ids: List[int] = Field(
        default_factory=list,
        sa_column=Column(JSON())
    )
    competition_color: str = Field(default="#2563EB", max_length=7)
    score_type: CompetitionScoreType = Field(default=CompetitionScoreType.AVERAGE)
    top_n: int = Field(default=10)
    custom_page_config: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON())
    )
    status: CompetitionStatus = Field(default=CompetitionStatus.PENDING)
    result_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON())
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None

class CompetitionEntry(SQLModel, table=True):
    __tablename__ = "competition_entries"
    __table_args__ = (
        UniqueConstraint("competition_id", "soup_id", name="uq_competition_entries_pair"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    competition_id: int = Field(foreign_key="competitions.id", index=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    author_uid: int = Field(foreign_key="users.uid", index=True)
    final_score: float = Field(default=0.0)
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
    condition_params: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON())
    )
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

# ==================== 根用户站内信与私有附件 ====================
class SystemMessage(SQLModel, table=True):
    __tablename__ = "system_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    sender_uid: int = Field(foreign_key="users.uid", index=True)
    title: str = Field(max_length=200)
    markdown: str = Field(sa_column=Column(Text, nullable=False))
    rendered_html: str = Field(sa_column=Column(Text, nullable=False))
    recipient_mode: str = Field(max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SystemMessageRecipient(SQLModel, table=True):
    __tablename__ = "system_message_recipients"
    __table_args__ = (
        UniqueConstraint(
            "system_message_id",
            "user_uid",
            name="uq_system_message_recipient",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    system_message_id: int = Field(foreign_key="system_messages.id", index=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    delivered_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None


class MessageAttachment(SQLModel, table=True):
    __tablename__ = "message_attachments"

    id: Optional[int] = Field(default=None, primary_key=True)
    uploader_uid: int = Field(foreign_key="users.uid", index=True)
    system_message_id: Optional[int] = Field(
        default=None,
        foreign_key="system_messages.id",
        index=True,
    )
    storage_key: str = Field(unique=True, max_length=500)
    original_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size: int = Field(ge=0)
    sha256: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class EmailCampaign(SQLModel, table=True):
    __tablename__ = "email_campaigns"

    id: Optional[int] = Field(default=None, primary_key=True)
    creator_uid: int = Field(foreign_key="users.uid", index=True)
    subject: str = Field(max_length=200)
    markdown: str = Field(sa_column=Column(Text, nullable=False))
    rendered_html: str = Field(sa_column=Column(Text, nullable=False))
    category: EmailCampaignCategory = Field(
        default=EmailCampaignCategory.NOTICE,
        sa_column=Column(
            SAEnum(
                EmailCampaignCategory,
                values_callable=lambda values: [value.value for value in values],
                native_enum=False,
                length=10,
            ),
            nullable=False,
            default=EmailCampaignCategory.NOTICE,
        ),
    )
    recipient_mode: str = Field(max_length=10)
    recipient_uids: List[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    attachment_ids: List[int] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    status: EmailCampaignStatus = Field(
        default=EmailCampaignStatus.DRAFT,
        sa_column=Column(
            SAEnum(
                EmailCampaignStatus,
                values_callable=lambda values: [value.value for value in values],
                native_enum=False,
                length=10,
            ),
            nullable=False,
            default=EmailCampaignStatus.DRAFT,
            index=True,
        ),
    )
    selected_count: int = Field(default=0)
    eligible_count: int = Field(default=0)
    filtered_count: int = Field(default=0)
    queued_count: int = Field(default=0)
    queued_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class EmailCampaignRecipient(SQLModel, table=True):
    __tablename__ = "email_campaign_recipients"
    __table_args__ = (
        UniqueConstraint(
            "email_campaign_id",
            "user_uid",
            name="uq_email_campaign_recipient",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    email_campaign_id: int = Field(foreign_key="email_campaigns.id", index=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    recipient_email: str = Field(max_length=320)
    status: EmailCampaignRecipientStatus = Field(
        default=EmailCampaignRecipientStatus.PENDING,
        sa_column=Column(
            SAEnum(
                EmailCampaignRecipientStatus,
                values_callable=lambda values: [value.value for value in values],
                native_enum=False,
                length=10,
            ),
            nullable=False,
            default=EmailCampaignRecipientStatus.PENDING,
            index=True,
        ),
    )
    attempts: int = Field(default=0)
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text))
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class EmailCampaignAttachment(SQLModel, table=True):
    __tablename__ = "email_campaign_attachments"

    id: Optional[int] = Field(default=None, primary_key=True)
    email_campaign_id: int = Field(foreign_key="email_campaigns.id", index=True)
    source_attachment_id: Optional[int] = Field(
        default=None,
        foreign_key="message_attachments.id",
        index=True,
    )
    storage_key: str = Field(max_length=500)
    original_name: str = Field(max_length=255)
    mime_type: str = Field(max_length=100)
    size: int = Field(ge=0)
    sha256: str = Field(max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

# ==================== 消息系统 ====================
class DirectConversation(SQLModel, table=True):
    __tablename__ = "direct_conversations"
    __table_args__ = (
        UniqueConstraint("low_uid", "high_uid", name="uq_direct_conversation_pair"),
        CheckConstraint("low_uid < high_uid", name="ck_direct_conversation_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    low_uid: int = Field(foreign_key="users.uid", index=True)
    high_uid: int = Field(foreign_key="users.uid", index=True)
    last_message_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PrivateMessage(SQLModel, table=True):
    __tablename__ = "private_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: Optional[int] = Field(
        default=None,
        foreign_key="direct_conversations.id",
        index=True,
    )
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


class Mention(SQLModel, table=True):
    __tablename__ = "mentions"
    __table_args__ = (
        UniqueConstraint(
            "mentioned_uid",
            "target_type",
            "target_id",
            name="uq_mentions_recipient_target",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    actor_uid: int = Field(foreign_key="users.uid", index=True)
    mentioned_uid: int = Field(foreign_key="users.uid", index=True)
    target_type: MentionTargetType = Field(
        sa_column=Column(
            SAEnum(
                MentionTargetType,
                values_callable=lambda values: [value.value for value in values],
                native_enum=False,
                length=20,
            ),
            nullable=False,
        )
    )
    target_id: int = Field(index=True)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(gt=0)
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
    operator_roles: Optional[List[str]] = Field(
        default_factory=list,
        sa_column=Column(JSON())
    )
    action_type: str
    target_type: str
    target_id: Optional[int] = None
    details: Optional[dict] = Field(
        default_factory=dict,
        sa_column=Column(JSON())
    )
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ==================== 签到记录 ====================
class SigninRecord(SQLModel, table=True):
    __tablename__ = "signin_records"
    __table_args__ = (
        UniqueConstraint("user_uid", "signin_day", name="uq_signin_user_day"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_uid: int = Field(foreign_key="users.uid", index=True)
    signin_day: date = Field(default_factory=date.today, index=True)
    points_earned: int = Field(default=10)
