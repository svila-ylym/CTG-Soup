"""问卷 Schema 定义 - 汤吧社区"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.models import SurveyStatus, SurveyQuestionType


class SurveyQuestionCreate(BaseModel):
    question_text: str
    question_type: SurveyQuestionType
    options: Optional[List[str]] = None
    required: bool = True
    sort_order: int = 0


class SurveyCreate(BaseModel):
    title: str = Field(max_length=200)
    description: Optional[str] = None
    status: SurveyStatus = SurveyStatus.DRAFT
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    questions: List[SurveyQuestionCreate] = []


class SurveyUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[SurveyStatus] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class SurveyQuestionResponse(SurveyQuestionCreate):
    id: int
    survey_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SurveyResponseBase(BaseModel):
    survey_id: int


class SurveyAnswerCreate(BaseModel):
    question_id: int
    answer_text: Optional[str] = None
    answer_option_ids: Optional[List[int]] = None
    answer_rating: Optional[int] = None


class SurveySubmit(BaseModel):
    answers: List[SurveyAnswerCreate]


class SurveyDetail(SurveyCreate):
    id: int
    author_uid: int
    notification_sent: bool
    created_at: datetime
    updated_at: datetime
    questions: List[SurveyQuestionResponse] = []

    class Config:
        from_attributes = True


class SurveySummary(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    status: SurveyStatus
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    notification_sent: bool
    created_at: datetime
    updated_at: datetime
    question_count: int = 0
    response_count: int = 0

    class Config:
        from_attributes = True


class SurveyPageResponse(BaseModel):
    items: List[SurveySummary]
    total: int
    page: int
    page_size: int
    total_pages: int


class SurveyStatistics(BaseModel):
    survey_id: int
    total_responses: int
    question_stats: List[Dict[str, Any]]
