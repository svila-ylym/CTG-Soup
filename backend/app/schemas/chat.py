from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.community import UserSummary


class ConversationCreate(BaseModel):
    user_uid: int = Field(gt=0)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("消息不能为空")
        return normalized


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_uid: int
    receiver_uid: int
    content: str
    is_read: bool
    created_at: datetime


class ConversationResponse(BaseModel):
    id: int
    other_user: UserSummary
    last_message: ChatMessageResponse | None = None
    unread_count: int
    last_message_at: datetime | None = None
    created_at: datetime


class ConversationPageResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class MessageCursorPage(BaseModel):
    items: list[ChatMessageResponse]
    next_cursor: int | None = None


class ReadConversationRequest(BaseModel):
    message_id: int | None = Field(default=None, gt=0)


class ReadConversationResponse(BaseModel):
    conversation_id: int
    last_read_message_id: int | None
    read_count: int
