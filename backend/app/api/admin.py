from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.models.database import get_db, User, Punishment, OperationLog, Report, Post, Comment, TurtleSoup
from app.schemas import PunishmentCreate, PunishmentRevoke, PunishmentResponse, OperationLogResponse, ReportResponse, PageResponse
from app.api.auth import get_current_admin_user, get_current_root_user
from app.core.enums import UserRole, AccountStatus, PunishmentType, ActionType

router = APIRouter()


@router.get("/users", response_model=PageResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取用户列表（管理员）"""
    offset = (page - 1) * page_size
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if status_filter:
        query = query.filter(User.status == status_filter)
    
    query = query.order_by(User.created_at.desc())
    
    total = query.count()
    users = query.offset(offset).limit(page_size).all()
    
    items = []
    for user in users:
        items.append({
            "id": user.id,
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/punish", response_model=PunishmentResponse)
async def create_punishment(
    punishment_data: PunishmentCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """执行处罚"""
    target_user = db.query(User).filter(User.id == punishment_data.target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    # 根用户不能被处罚
    if target_user.role == UserRole.ROOT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能处罚根用户")
    
    db_punishment = Punishment(
        target_user_id=punishment_data.target_user_id,
        operator_id=current_user.id,
        punishment_type=punishment_data.punishment_type,
        reason=punishment_data.reason,
        end_time=punishment_data.end_time,
        related_content_id=punishment_data.related_content_id,
        related_content_type=punishment_data.related_content_type,
    )
    
    db.add(db_punishment)
    
    # 根据处罚类型更新用户状态
    if punishment_data.punishment_type == PunishmentType.BAN:
        target_user.status = AccountStatus.BANNED
    elif punishment_data.punishment_type == PunishmentType.SILENCE:
        target_user.status = AccountStatus.SILENCED
    
    # 记录操作日志
    log = OperationLog(
        operator_id=current_user.id,
        operator_roles=[current_user.role],
        action_type=ActionType.PUNISH,
        target_type="user",
        target_id=punishment_data.target_user_id,
        details={"punishment_type": punishment_data.punishment_type, "reason": punishment_data.reason},
    )
    db.add(log)
    
    db.commit()
    db.refresh(db_punishment)
    
    return db_punishment


@router.post("/punish/{punishment_id}/revoke", response_model=PunishmentResponse)
async def revoke_punishment(
    punishment_id: int,
    revoke_data: PunishmentRevoke,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db)
):
    """撤销处罚（仅根用户）"""
    punishment = db.query(Punishment).filter(Punishment.id == punishment_id).first()
    if not punishment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="处罚记录不存在")
    
    if punishment.is_revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="处罚已被撤销")
    
    punishment.is_revoked = True
    punishment.revoked_at = datetime.utcnow()
    punishment.revoked_by = current_user.id
    punishment.revoke_reason = revoke_data.revoke_reason
    
    # 恢复用户状态
    target_user = db.query(User).filter(User.id == punishment.target_user_id).first()
    if target_user:
        if punishment.punishment_type == PunishmentType.BAN and target_user.status == AccountStatus.BANNED:
            target_user.status = AccountStatus.ACTIVE
        elif punishment.punishment_type == PunishmentType.SILENCE and target_user.status == AccountStatus.SILENCED:
            target_user.status = AccountStatus.ACTIVE
    
    # 记录操作日志
    log = OperationLog(
        operator_id=current_user.id,
        operator_roles=[current_user.role],
        action_type=ActionType.REVOKE_PUNISHMENT,
        target_type="punishment",
        target_id=punishment_id,
        details={"revoke_reason": revoke_data.revoke_reason},
    )
    db.add(log)
    
    db.commit()
    
    return punishment


@router.get("/punishments", response_model=PageResponse)
async def list_punishments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_revoked: Optional[bool] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取处罚记录列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Punishment)
    
    if is_revoked is not None:
        query = query.filter(Punishment.is_revoked == is_revoked)
    
    query = query.order_by(Punishment.created_at.desc())
    
    total = query.count()
    punishments = query.offset(offset).limit(page_size).all()
    
    items = []
    for p in punishments:
        items.append({
            "id": p.id,
            "target_user_id": p.target_user_id,
            "operator_id": p.operator_id,
            "punishment_type": p.punishment_type,
            "reason": p.reason,
            "start_time": p.start_time,
            "end_time": p.end_time,
            "is_revoked": p.is_revoked,
            "revoked_at": p.revoked_at,
            "revoked_by": p.revoked_by,
            "revoke_reason": p.revoke_reason,
            "created_at": p.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/reports", response_model=PageResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """获取举报列表"""
    offset = (page - 1) * page_size
    
    query = db.query(Report)
    
    if status_filter:
        query = query.filter(Report.status == status_filter)
    
    query = query.order_by(Report.created_at.desc())
    
    total = query.count()
    reports = query.offset(offset).limit(page_size).all()
    
    items = []
    for report in reports:
        items.append({
            "id": report.id,
            "reporter_id": report.reporter_id,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason": report.reason,
            "status": report.status,
            "handler_id": report.handler_id,
            "handle_result": report.handle_result,
            "handled_at": report.handled_at,
            "created_at": report.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/logs", response_model=PageResponse)
async def list_operation_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action_type: Optional[str] = None,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db)
):
    """获取操作日志（仅根用户）"""
    offset = (page - 1) * page_size
    
    query = db.query(OperationLog)
    
    if action_type:
        query = query.filter(OperationLog.action_type == action_type)
    
    query = query.order_by(OperationLog.created_at.desc())
    
    total = query.count()
    logs = query.offset(offset).limit(page_size).all()
    
    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "operator_id": log.operator_id,
            "operator_username": log.operator.username,
            "operator_roles": log.operator_roles,
            "action_type": log.action_type,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
