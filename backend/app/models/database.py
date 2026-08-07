"""
数据库连接与模型导出
提供统一的数据库访问接口
"""
from sqlmodel import Session
from typing import Generator

from app.db import engine, init_db, get_session as _get_session
from app.models.models import (
    User, UserRole, UserStatus,
    Punishment, PunishmentType,
    Post, PostType,
    Comment, CommentTargetType,
    Soup,
    Rating,
    Like, LikeTargetType,
    Favorite, FavoriteTargetType,
    Follow, Blacklist,
    Competition, CompetitionEntry, CompetitionScoreType, CompetitionStatus,
    Achievement, Title, UserAchievement, AchievementConditionType,
    PrivateMessage, Notification, NotificationType,
    Report, ReportTargetType, ReportStatus,
    OperationLog,
    SigninRecord
)


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
    # 评分系统
    "Rating",
    # 点赞与收藏
    "Like",
    "LikeTargetType",
    "Favorite",
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
    "Title",
    "UserAchievement",
    "AchievementConditionType",
    # 消息系统
    "PrivateMessage",
    "Notification",
    "NotificationType",
    # 举报系统
    "Report",
    "ReportTargetType",
    "ReportStatus",
    # 操作日志
    "OperationLog",
    # 签到记录
    "SigninRecord",
]
