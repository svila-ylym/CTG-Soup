"""Pure level calculations shared by profiles and daily sign-in."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class LevelProgress:
    level: int
    experience_points: int
    level_start: int
    next_level_start: int | None

    @property
    def experience_into_level(self) -> int:
        return max(self.experience_points - self.level_start, 0)

    @property
    def experience_for_next_level(self) -> int | None:
        if self.next_level_start is None:
            return None
        return self.next_level_start - self.level_start


def level_progress(points: int) -> LevelProgress:
    normalized = max(points, 0)
    level = min(100, 1 + math.isqrt(normalized // 100))
    level_start = 100 * (level - 1) ** 2
    next_level_start = None if level == 100 else 100 * level ** 2
    return LevelProgress(level, normalized, level_start, next_level_start)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def signin_day(now: datetime, timezone_name: str) -> date:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return now.astimezone(ZoneInfo(timezone_name)).date()


def signin_reward(streak: int) -> int:
    return 10 + min(max(streak, 1), 7)
