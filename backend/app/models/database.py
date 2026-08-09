"""
数据库连接与模型导出
提供统一的数据库访问接口
"""
from sqlmodel import Session
from typing import Generator

from app.db import engine, init_db, get_session as _get_session
from app.models.models import (
    User, UserRole, UserStatus, ThemePreference, EmailVerification,
    ReusableUserUid, UserUidAllocator, UploadedAsset,
    Punishment, PunishmentType,
    Post, PostType,
    Comment, CommentTargetType,
    Soup, SoupImage, SoupTag, FeaturedSoup, Tag, TagAlias, TagKind, TagStatus, Announcement, AnnouncementStatus,
    Rating,
    Like, LikeTargetType,
    Favorite, FavoriteTargetType,
    Follow, Blacklist,
    Competition, CompetitionEntry, CompetitionScoreType, CompetitionStatus,
    Achievement, Title, UserAchievement, AchievementConditionType,
    DirectConversation, PrivateMessage, Notification, NotificationType, Mention, MentionTargetType,
    SystemMessage, SystemMessageRecipient, MessageAttachment,
    EmailCampaign, EmailCampaignAttachment, EmailCampaignCategory,
    EmailCampaignRecipient, EmailCampaignRecipientStatus, EmailCampaignStatus,
    Report, ReportTargetType, ReportStatus,
    OperationLog,
    SigninRecord
    , PermissionGroup, UserPermissionGroup
)

# Transitional names used by legacy route modules. New code must use the
# canonical SQLModel names above; these aliases keep unrelated routers
# importable while they are migrated incrementally.
TurtleSoup = Soup
Collection = Favorite
AchievementDefinition = Achievement


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话"""
    yield from _get_session()


__all__ = [
    # 数据库连接
    "engine",
    "init_db",
    "get_db",
    "get_session",
    # 用户系统
    "User",
    "UserRole",
    "UserStatus",
    "ThemePreference",
    "EmailVerification",
    "ReusableUserUid",
    "UserUidAllocator",
    "UploadedAsset",
    "PermissionGroup",
    "UserPermissionGroup",
    # 处罚系统
    "Punishment",
    "PunishmentType",
    # 帖子系统
    "Post",
    "PostType",
    # 评论系统
    "Comment",
    "CommentTargetType",
    # 海龟汤系统
    "Soup",
    "SoupImage",
    "TurtleSoup",
    "Tag",
    "TagAlias",
    "TagKind",
    "TagStatus",
    "SoupTag",
    "FeaturedSoup",
    "Announcement",
    "AnnouncementStatus",
    # 评分系统
    "Rating",
    # 点赞与收藏
    "Like",
    "LikeTargetType",
    "Favorite",
    "Collection",
    "FavoriteTargetType",
    # 社交关系
    "Follow",
    "Blacklist",
    # 比赛系统
    "Competition",
    "CompetitionEntry",
    "CompetitionScoreType",
    "CompetitionStatus",
    # 成就系统
    "Achievement",
    "AchievementDefinition",
    "Title",
    "UserAchievement",
    "AchievementConditionType",
    # 消息系统
    "DirectConversation",
    "PrivateMessage",
    "Notification",
    "NotificationType",
    "Mention",
    "MentionTargetType",
    "SystemMessage",
    "SystemMessageRecipient",
    "MessageAttachment",
    "EmailCampaign",
    "EmailCampaignAttachment",
    "EmailCampaignCategory",
    "EmailCampaignRecipient",
    "EmailCampaignRecipientStatus",
    "EmailCampaignStatus",
    # 举报系统
    "Report",
    "ReportTargetType",
    "ReportStatus",
    # 操作日志
    "OperationLog",
    # 签到记录
    "SigninRecord",
]
