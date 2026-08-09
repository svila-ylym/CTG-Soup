from typing import Generic, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total_pages: int = Field(ge=0)


class ApiError(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


def extract_detail_message(detail: object, fallback: str = "请求失败") -> str:
    if isinstance(detail, dict):
        message = detail.get("message")
        if isinstance(message, str) and message:
            return message
    if isinstance(detail, str) and detail:
        return detail
    return fallback
