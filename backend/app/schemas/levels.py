from datetime import date

from pydantic import BaseModel


class SigninStatusResponse(BaseModel):
    signed_in: bool
    signin_day: date
    consecutive_days: int
    experience_points: int
    experience_gained: int
    level: int
    level_start: int
    next_level_start: int | None
