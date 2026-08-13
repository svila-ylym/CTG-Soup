"""问卷 API - 汤吧社区"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from datetime import datetime
from typing import List

from app.api.auth import get_current_active_user
from app.models.database import get_db
from app.models.models import Survey, SurveyQuestion, SurveyResponse, SurveyAnswer, User, UserRole, Notification, NotificationType
from app.schemas.surveys import (
    SurveyCreate, SurveyUpdate, SurveyDetail, SurveySummary,
    SurveyPageResponse, SurveySubmit, SurveyStatistics
)

router = APIRouter()


def require_admin_or_root(current_user: User):
    """验证用户是否为 Admin 或 Root"""
    if current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        raise HTTPException(status_code=403, detail="只有管理员和 Root 用户可以创建问卷")
    return current_user


@router.get("", response_model=SurveyPageResponse)
def list_surveys(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = "active",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """获取问卷列表"""
    query = select(Survey)
    
    if status == "active":
        now = datetime.utcnow()
        query = query.where(
            Survey.status == "active",
            (Survey.starts_at == None) | (Survey.starts_at <= now),
            (Survey.expires_at == None) | (Survey.expires_at > now)
        )
    elif status == "all":
        if current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
            query = query.where(Survey.status == "active")
    
    # 统计问题数量和回答数量
    total_query = query
    total = len(db.exec(total_query).all())
    
    rows = db.exec(
        query.order_by(Survey.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    
    items = []
    for survey in rows:
        question_count = len(db.exec(select(func.count()).where(SurveyQuestion.survey_id == survey.id)).all())
        response_count = len(db.exec(select(func.count()).where(SurveyResponse.survey_id == survey.id)).all())
        item = SurveySummary(
            id=survey.id,
            title=survey.title,
            description=survey.description,
            status=survey.status,
            starts_at=survey.starts_at,
            expires_at=survey.expires_at,
            notification_sent=survey.notification_sent,
            created_at=survey.created_at,
            updated_at=survey.updated_at,
            question_count=question_count[0] if question_count else 0,
            response_count=response_count[0] if response_count else 0
        )
        items.append(item)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


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
    
    questions = db.exec(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
        .order_by(SurveyQuestion.sort_order)
    ).all()
    
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
        questions=[SurveyQuestionResponse(
            id=q.id,
            survey_id=q.survey_id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=q.options,
            required=q.required,
            sort_order=q.sort_order,
            created_at=q.created_at
        ) for q in questions]
    )


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
    
    questions = db.exec(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey.id)
        .order_by(SurveyQuestion.sort_order)
    ).all()
    
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
        questions=[SurveyQuestionResponse(
            id=q.id,
            survey_id=q.survey_id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=q.options,
            required=q.required,
            sort_order=q.sort_order,
            created_at=q.created_at
        ) for q in questions]
    )


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
    
    questions = db.exec(
        select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
        .order_by(SurveyQuestion.sort_order)
    ).all()
    
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
        questions=[SurveyQuestionResponse(
            id=q.id,
            survey_id=q.survey_id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=q.options,
            required=q.required,
            sort_order=q.sort_order,
            created_at=q.created_at
        ) for q in questions]
    )


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
    
    total_responses = len(db.exec(
        select(func.count()).where(SurveyResponse.survey_id == survey_id)
    ).all())
    
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
        total_responses=total_responses[0] if total_responses else 0,
        question_stats=question_stats
    )
