from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    USER = "user"  # 普通用户
    ADMIN = "admin"  # 管理员
    ROOT = "root"  # 根用户


class AccountStatus(str, Enum):
    """账户状态枚举"""
    ACTIVE = "active"  # 正常
    BANNED = "banned"  # 封号
    SILENCED = "silenced"  # 禁言
    PENDING_EMAIL = "pending_email"  # 待邮箱验证


class PunishmentType(str, Enum):
    """处罚类型枚举"""
    BAN = "ban"  # 封号
    SILENCE = "silence"  # 禁言
    DELETE_CONTENT = "delete_content"  # 删除内容
    DISABLE_COMMENT = "disable_comment"  # 禁用评论
    RATE_LIMIT = "rate_limit"  # 限流


class ContentType(str, Enum):
    """内容类型枚举"""
    POST = "post"  # 帖子
    COMMENT = "comment"  # 评论
    TURTLE_SOUP = "turtle_soup"  # 海龟汤
    PRIVATE_MESSAGE = "private_message"  # 私信


class PostType(str, Enum):
    """帖子类型枚举"""
    NORMAL = "normal"  # 普通帖子
    VOTE = "vote"  # 投票帖子
    TURTLE_SOUP = "turtle_soup"  # 海龟汤帖子


class NotificationType(str, Enum):
    """通知类型枚举"""
    MENTION = "mention"  # @提及
    COMMENT_REPLY = "comment_reply"  # 评论回复
    RATING = "rating"  # 评分
    REPORT_RESULT = "report_result"  # 举报结果
    PUNISHMENT = "punishment"  # 处罚
    PUNISHMENT_REVOKED = "punishment_revoked"  # 处罚撤销
    ROLE_CHANGED = "role_changed"  # 角色变动
    ACHIEVEMENT = "achievement"  # 成就获得
    COMPETITION_START = "competition_start"  # 比赛开始
    COMPETITION_END = "competition_end"  # 比赛结束


class AchievementConditionType(str, Enum):
    """成就条件类型枚举"""
    REGISTER_DAYS = "register_days"  # 注册天数
    POST_COUNT = "post_count"  # 发帖数
    SOUP_COUNT = "soup_count"  # 发汤数
    FRIEND_COUNT = "friend_count"  # 好友数
    LIKE_RECEIVED = "like_received"  # 获赞总数
    COLLECT_COUNT = "collect_count"  # 收藏数
    COMMENT_COUNT = "comment_count"  # 评论数
    LOGIN_DAYS = "login_days"  # 登录天数


class CompetitionScoringMethod(str, Enum):
    """比赛计分方式枚举"""
    AVERAGE = "average"  # 平均制
    HIGHEST = "highest"  # 高分制


class CompetitionStatus(str, Enum):
    """比赛状态枚举"""
    PENDING = "pending"  # 未开始
    ONGOING = "ongoing"  # 进行中
    ENDED = "ended"  # 已结束


class ActionType(str, Enum):
    """操作日志动作类型枚举"""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    RESTORE = "restore"
    PUNISH = "punish"
    REVOKE_PUNISHMENT = "revoke_punishment"
    CHANGE_ROLE = "change_role"
    GRANT_ACHIEVEMENT = "grant_achievement"
    REVOKE_ACHIEVEMENT = "revoke_achievement"
