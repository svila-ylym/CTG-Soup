"""问卷 API - 汤吧社区"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlmodel import Session, select, func
from datetime import datetime
from typing import List, Literal, Optional, Sequence

from app.api.auth import get_current_active_user
from app.models.database import get_db
from app.models.models import (
    Notification,
    NotificationType,
    Survey,
    SurveyAnswer,
    SurveyQuestion,
    SurveyResponse,
    SurveyStatus,
    User,
    UserRole,
)
from app.schemas.surveys import (
    SurveyCreate,
    SurveyDetail,
    SurveyPageResponse,
    SurveyQuestionResponse,
    SurveyStatistics,
    SurveySubmit,
    SurveySummary,
    SurveyUpdate,
)
from app.utils.cache import (
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
    generate_cache_key,
)

router = APIRouter()
SURVEY_CACHE_TTL_SECONDS = 60
SURVEY_LIST_CACHE_PATTERN = "ctg:v1:surveys:list:*"


def _survey_detail_cache_key(survey_id: int) -> str:
    return f"ctg:v1:surveys:detail:{survey_id}"


def _invalidate_survey_cache(survey_id: Optional[int] = None) -> None:
    cache_delete_pattern(SURVEY_LIST_CACHE_PATTERN)
    if survey_id is not None:
        cache_delete(_survey_detail_cache_key(survey_id))


def _survey_detail(
    survey: Survey,
    questions: Sequence[SurveyQuestion],
    *,
    has_submitted: bool = False,
) -> SurveyDetail:
    return SurveyDetail(
        id=survey.id,
        author_uid=survey.author_uid,
        title=survey.title,
        description=survey.description,
        status=survey.status,
        starts_at=survey.starts_at,
        expires_at=survey.expires_at,
        notification_sent=survey.notification_sent,
        created_at=survey.created_at,
        updated_at=survey.updated_at,
        questions=[SurveyQuestionResponse.model_validate(question) for question in questions],
        has_submitted=has_submitted,
    )


def require_admin_or_root(
    current_user: User = Depends(get_current_active_user),
):
    """验证用户是否为 Admin 或 Root"""
    if current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        raise HTTPException(status_code=403, detail="只有管理员和 Root 用户可以创建问卷")
    return current_user


@router.get("", response_model=SurveyPageResponse)
def list_surveys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Literal["active", "all"] = "active",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取问卷列表，公共视图与管理视图使用隔离缓存。"""
    is_manager = current_user.role in [UserRole.ADMIN, UserRole.ROOT]
    effective_status = "all" if status == "all" and is_manager else "active"
    scope = "manager" if effective_status == "all" else "public"
    cache_key = generate_cache_key(
        "surveys:list",
        page=page,
        page_size=page_size,
        status=effective_status,
        scope=scope,
    )
    cached_page = cache_get(cache_key)
    if cached_page is not None:
        try:
            return SurveyPageResponse.model_validate(cached_page)
        except (ValidationError, TypeError):
            cache_delete(cache_key)

    filters = []
    if effective_status == "active":
        now = datetime.utcnow()
        filters.extend((
            Survey.status == "active",
            (Survey.starts_at == None) | (Survey.starts_at <= now),
            (Survey.expires_at == None) | (Survey.expires_at > now),
        ))

    total_statement = select(func.count(Survey.id))
    if filters:
        total_statement = total_statement.where(*filters)
    total = db.exec(total_statement).one()

    question_count = (
        select(func.count(SurveyQuestion.id))
        .where(SurveyQuestion.survey_id == Survey.id)
        .correlate(Survey)
        .scalar_subquery()
    )
    response_count = (
        select(func.count(SurveyResponse.id))
        .where(SurveyResponse.survey_id == Survey.id)
        .correlate(Survey)
        .scalar_subquery()
    )
    query = select(
        Survey,
        question_count.label("question_count"),
        response_count.label("response_count"),
    )
    if filters:
        query = query.where(*filters)
    rows = db.exec(
        query.order_by(Survey.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    items = [
        SurveySummary(
            id=survey.id,
            title=survey.title,
            description=survey.description,
            status=survey.status,
            starts_at=survey.starts_at,
            expires_at=survey.expires_at,
            notification_sent=survey.notification_sent,
            created_at=survey.created_at,
            updated_at=survey.updated_at,
            question_count=question_total or 0,
            response_count=response_total or 0,
        )
        for survey, question_total, response_total in rows
    ]
    response = SurveyPageResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )
    cache_set(cache_key, response.model_dump(mode="json"), SURVEY_CACHE_TTL_SECONDS)
    return response


@router.get("/{survey_id}", response_model=SurveyDetail)
def get_survey(
    survey_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取问卷详情"""
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    # 检查权限：只有作者或管理员可以查看非活跃问卷
    if survey.status != "active" and current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        if survey.author_uid != current_user.uid:
            raise HTTPException(status_code=403, detail="无权查看此问卷")
    
    detail_key = _survey_detail_cache_key(survey_id)
    common_detail = None
    if survey.status == SurveyStatus.ACTIVE:
        cached_detail = cache_get(detail_key)
        if cached_detail is not None:
            try:
                common_detail = SurveyDetail.model_validate(cached_detail)
            except (ValidationError, TypeError):
                cache_delete(detail_key)

    if common_detail is None:
        questions = db.exec(
            select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
            .order_by(SurveyQuestion.sort_order)
        ).all()
        common_detail = _survey_detail(survey, questions)
        if survey.status == SurveyStatus.ACTIVE:
            cache_set(
                detail_key,
                common_detail.model_dump(mode="json"),
                SURVEY_CACHE_TTL_SECONDS,
            )

    has_submitted = db.exec(
        select(SurveyResponse.id).where(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.user_uid == current_user.uid,
        )
    ).first() is not None
    payload = common_detail.model_dump()
    payload["has_submitted"] = has_submitted
    return SurveyDetail.model_validate(payload)


@router.post("", response_model=SurveyDetail)
def create_survey(
    survey_data: SurveyCreate,
    current_user: User = Depends(require_admin_or_root),
    db: Session = Depends(get_db),
):
    """创建新问卷（仅 Admin/Root）"""
    survey = Survey(
        author_uid=current_user.uid,
        title=survey_data.title,
        description=survey_data.description,
        status=survey_data.status,
        starts_at=survey_data.starts_at,
        expires_at=survey_data.expires_at,
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    # 添加问题
    for idx, q_data in enumerate(survey_data.questions):
        question = SurveyQuestion(
            survey_id=survey.id,
            question_text=q_data.question_text,
            question_type=q_data.question_type,
            options=q_data.options,
            required=q_data.required,
            sort_order=q_data.sort_order or idx,
        )
        db.add(question)
    db.commit()
    
    # 如果状态为 active，发送通知给所有用户
    if survey.status == "active" and not survey.notification_sent:
        users = db.exec(select(User).where(User.status == "active")).all()
        for user in users:
            notification = Notification(
                recipient_uid=user.uid,
                notification_type=NotificationType.SYSTEM,
                title=f"新问卷发布：{survey.title}",
                content=survey_data.description or f"请填写问卷：{survey.title}",
                related_entity_type="survey",
                related_entity_id=survey.id,
            )
            db.add(notification)
        survey.notification_sent = True
        db.commit()
        
    _invalidate_survey_cache(survey.id)
    
    questions = db.exec(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey.id)
        .order_by(SurveyQuestion.sort_order)
    ).all()
    
    return _survey_detail(survey, questions)


@router.put("/{survey_id}", response_model=SurveyDetail)
def update_survey(
    survey_id: int,
    survey_data: SurveyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """更新问卷（仅作者或 Admin/Root）"""
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    if survey.author_uid != current_user.uid and current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        raise HTTPException(status_code=403, detail="无权修改此问卷")
    
    update_data = survey_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(survey, field, value)
    
    db.commit()
    db.refresh(survey)
    _invalidate_survey_cache(survey_id)
    
    questions = db.exec(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
        .order_by(SurveyQuestion.sort_order)
    ).all()
    
    return _survey_detail(survey, questions)


@router.post("/{survey_id}/submit")
def submit_survey(
    survey_id: int,
    submission: SurveySubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """提交问卷回答"""
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    if survey.status != "active":
        raise HTTPException(status_code=400, detail="问卷未开放或已关闭")
    
    now = datetime.utcnow()
    if survey.starts_at and survey.starts_at > now:
        raise HTTPException(status_code=400, detail="问卷尚未开始")
    if survey.expires_at and survey.expires_at < now:
        raise HTTPException(status_code=400, detail="问卷已过期")
    
    # 检查是否已回答
    existing = db.exec(
        select(SurveyResponse).where(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.user_uid == current_user.uid
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="您已经回答过此问卷")
    
    # 创建回答记录
    response = SurveyResponse(survey_id=survey_id, user_uid=current_user.uid)
    db.add(response)
    db.commit()
    db.refresh(response)
    
    # 获取所有问题
    questions = {q.id: q for q in db.exec(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)).all()}
    
    # 保存答案
    for ans_data in submission.answers:
        question = questions.get(ans_data.question_id)
        if not question:
            continue
        
        answer = SurveyAnswer(
            response_id=response.id,
            question_id=ans_data.question_id,
            answer_text=ans_data.answer_text,
            answer_option_ids=ans_data.answer_option_ids,
            answer_rating=ans_data.answer_rating,
        )
        db.add(answer)
    
    db.commit()
    _invalidate_survey_cache()
    return {"message": "问卷提交成功"}


@router.get("/{survey_id}/statistics", response_model=SurveyStatistics)
def get_survey_statistics(
    survey_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取问卷统计信息（仅 Admin/Root 或作者）"""
    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="问卷不存在")
    
    if survey.author_uid != current_user.uid and current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        raise HTTPException(status_code=403, detail="无权查看统计信息")
    
    total_responses = db.exec(
        select(func.count(SurveyResponse.id)).where(SurveyResponse.survey_id == survey_id)
    ).one()
    
    questions = db.exec(select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)).all()
    question_stats = []
    
    for q in questions:
        answers = db.exec(
            select(SurveyAnswer).where(SurveyAnswer.question_id == q.id)
        ).all()
        
        stat = {"question_id": q.id, "question_text": q.question_text, "total_answers": len(answers)}
        
        if q.question_type in ["single_choice", "multiple_choice"]:
            option_counts = {}
            for ans in answers:
                if ans.answer_option_ids:
                    for opt_id in ans.answer_option_ids:
                        option_counts[opt_id] = option_counts.get(opt_id, 0) + 1
            stat["option_distribution"] = option_counts
        elif q.question_type == "rating":
            ratings = [a.answer_rating for a in answers if a.answer_rating]
            if ratings:
                stat["average_rating"] = sum(ratings) / len(ratings)
        
        question_stats.append(stat)
    
    return SurveyStatistics(
        survey_id=survey_id,
        total_responses=total_responses,
        question_stats=question_stats
    )
