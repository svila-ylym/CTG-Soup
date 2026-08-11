from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.models.database import get_db, User, Punishment, OperationLog, Report, Post, Comment, TurtleSoup, PermissionGroup, UserPermissionGroup, Tag, TagAlias, SoupTag, TagKind, TagStatus, Announcement, AnnouncementStatus, Competition, EmailCampaign, ReusableUserUid, NotificationType, ReportStatus
from app.schemas import AdminUserUpdate, PunishmentCreate, PunishmentRevoke, PunishmentResponse, OperationLogResponse, ReportResponse, ReportCreate, ReportDecision, PageResponse, MessageResponse
from app.api.auth import get_current_admin_user, get_current_root_user, get_current_user
from app.models.database import UserRole, UserStatus, PunishmentType
from app.core.enums import ActionType
from app.services.governance_rules import can_manage_role
from app.services.governance_rules import decide_report
from app.schemas.announcements import TagAdminCreate, TagAdminUpdate, TagMergeRequest, AnnouncementCreate, AnnouncementUpdate
from app.services.tag_rules import normalize_tag_name
from app.services.competition_entries import (
    lock_competition_collection,
    rebuild_unsettled_competitions_for_tags,
)
from app.services.reporting import ReportTargetError, inspect_report_target, validate_report_target
from app.services.moderation_locks import lock_report_submission, lock_role_management, lock_user_punishments
from app.services.punishments import (
    active_punishment_types,
    effective_user_status,
    sync_user_punishment_status,
)
from app.api.system_messages import admin_router as system_message_admin_router
from app.schemas.email_campaigns import EmailCampaignCreate, EmailCampaignPage, EmailCampaignSummary
from app.services.email_campaigns import cancel_campaign, campaign_summary, create_campaign, queue_campaign
from app.services.pending_accounts import delete_pending_account_dependencies, lock_uid_allocation
from app.services.notification_dispatch import notify_user, notify_users
from sqlmodel import select

router = APIRouter()
router.include_router(system_message_admin_router, prefix="/system-messages")


@router.get("/email-campaigns", response_model=EmailCampaignPage)
def list_email_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    total = db.query(EmailCampaign).count()
    items = db.exec(
        select(EmailCampaign)
        .order_by(EmailCampaign.created_at.desc(), EmailCampaign.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [campaign_summary(db, campaign) for campaign in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post(
    "/email-campaigns",
    response_model=EmailCampaignSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_email_campaign(
    data: EmailCampaignCreate,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    return create_campaign(db, current_user, data)


@router.post("/email-campaigns/{campaign_id}/queue", response_model=EmailCampaignSummary)
def queue_email_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    return queue_campaign(db, current_user, campaign_id)


@router.post("/email-campaigns/{campaign_id}/cancel", response_model=EmailCampaignSummary)
def cancel_email_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    return cancel_campaign(db, current_user, campaign_id)


def _plain_text(value: str | None) -> str | None:
    import re
    if value is None:
        return None
    return re.sub(r"<[^>]*>", "", value).strip()


@router.get("/tags")
def admin_list_tags(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return db.exec(select(Tag).order_by(Tag.sort_order, Tag.id)).all()


@router.post("/tags", status_code=status.HTTP_201_CREATED)
def admin_create_tag(
    data: TagAdminCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    name, slug = normalize_tag_name(data.name)
    if db.exec(select(Tag).where(Tag.slug == slug)).first():
        raise HTTPException(409, "标签已存在")
    try:
        kind = TagKind(data.kind)
    except ValueError as exc:
        raise HTTPException(422, "标签类型无效") from exc
    tag = Tag(name=name, slug=slug, kind=kind, description=_plain_text(data.description))
    db.add(tag)
    db.flush()
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="create", target_type="tag", target_id=tag.id, details={"name": name}))
    db.commit()
    db.refresh(tag)
    return tag


@router.put("/tags/{tag_id}")
def admin_update_tag(
    tag_id: int,
    data: TagAdminUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "标签不存在")
    values = data.model_dump(exclude_unset=True)
    if "name" in values:
        values["name"], values["slug"] = normalize_tag_name(values.pop("name"))
    if "description" in values:
        values["description"] = _plain_text(values["description"])
    if "status" in values:
        try:
            values["status"] = TagStatus(values["status"])
        except ValueError as exc:
            raise HTTPException(422, "标签状态无效") from exc
    status_changed = (
        "status" in values
        and values["status"] != tag.status
    )
    if status_changed:
        lock_competition_collection(db)
    for key, value in values.items():
        setattr(tag, key, value)
    tag.updated_at = datetime.utcnow()
    if status_changed:
        db.flush()
        rebuild_unsettled_competitions_for_tags(db, {tag.id})
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="update", target_type="tag", target_id=tag.id, details=values))
    db.commit()
    db.refresh(tag)
    return tag


@router.post("/tags/{tag_id}/merge")
def admin_merge_tag(
    tag_id: int,
    data: TagMergeRequest,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    if tag_id == data.target_tag_id:
        raise HTTPException(400, "不能合并到自身")
    source = db.get(Tag, tag_id)
    target = db.get(Tag, data.target_tag_id)
    if not source or not target:
        raise HTTPException(404, "标签不存在")
    lock_competition_collection(db)
    for relation in db.exec(select(SoupTag).where(SoupTag.tag_id == source.id)).all():
        if not db.get(SoupTag, (relation.soup_id, target.id)):
            db.add(SoupTag(soup_id=relation.soup_id, tag_id=target.id))
        db.delete(relation)
    # Keep competition references valid when a taxonomy entry is merged.
    for competition in db.exec(select(Competition)).all():
        changed = False
        updated_tag_sets = {}
        for field_name in ("required_tag_ids", "optional_tag_ids"):
            values = []
            for value in getattr(competition, field_name) or []:
                tag_value = int(value)
                if tag_value == source.id:
                    tag_value = target.id
                    changed = True
                if tag_value not in values:
                    values.append(tag_value)
            updated_tag_sets[field_name] = values
        if changed:
            overlap = set(updated_tag_sets["required_tag_ids"]).intersection(
                updated_tag_sets["optional_tag_ids"]
            )
            competition.required_tag_ids = updated_tag_sets["required_tag_ids"]
            competition.optional_tag_ids = [
                value for value in updated_tag_sets["optional_tag_ids"]
                if value not in overlap
            ]
            competition.updated_at = datetime.utcnow()
    alias = db.exec(select(TagAlias).where(TagAlias.alias_slug == source.slug)).first()
    if alias is None:
        db.add(TagAlias(alias_slug=source.slug, tag_id=target.id))
    source.status = TagStatus.DISABLED
    source.updated_at = datetime.utcnow()
    db.flush()
    rebuild_unsettled_competitions_for_tags(db, {source.id, target.id})
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="merge", target_type="tag", target_id=source.id, details={"target_tag_id": target.id}))
    db.commit()
    return {"source_tag_id": source.id, "target_tag_id": target.id}


@router.post("/announcements", status_code=status.HTTP_201_CREATED)
def admin_create_announcement(
    data: AnnouncementCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = Announcement(author_uid=current_user.uid, **data.model_dump())
    db.add(announcement)
    db.flush()
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="create", target_type="announcement", target_id=announcement.id, details={"title": announcement.title}))
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/announcements")
def admin_list_announcements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    query = select(Announcement)
    total = len(db.exec(query).all())
    items = db.exec(
        query.order_by(Announcement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.put("/announcements/{announcement_id}")
def admin_update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    values = data.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(announcement, key, value)
    announcement.updated_at = datetime.utcnow()
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="update",
        target_type="announcement",
        target_id=announcement.id,
        details={"fields": list(values)},
    ))
    db.commit()
    db.refresh(announcement)
    return announcement


@router.post("/announcements/{announcement_id}/publish")
def admin_publish_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    announcement.status = AnnouncementStatus.PUBLISHED
    announcement.published_at = datetime.utcnow()
    announcement.updated_at = datetime.utcnow()
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="publish", target_type="announcement", target_id=announcement.id, details={}))
    db.commit()
    db.refresh(announcement)
    return announcement


@router.post("/announcements/{announcement_id}/withdraw")
def admin_withdraw_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    announcement.status = AnnouncementStatus.DRAFT
    announcement.updated_at = datetime.utcnow()
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="withdraw", target_type="announcement", target_id=announcement.id, details={}))
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/announcements/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_announcement(
    announcement_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    announcement = db.get(Announcement, announcement_id)
    if not announcement:
        raise HTTPException(404, "公告不存在")
    db.add(OperationLog(operator_uid=current_user.uid, operator_roles=[current_user.role.value], action_type="delete", target_type="announcement", target_id=announcement.id, details={}))
    db.delete(announcement)
    db.commit()


def _permission_group_payload(group: PermissionGroup, member_uids: list[int]) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "permissions": group.permissions,
        "member_uids": member_uids,
        "member_count": len(member_uids),
        "created_at": group.created_at,
        "updated_at": group.updated_at,
    }


@router.get("/permission-groups")
async def list_permission_groups(current_user: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    groups = db.query(PermissionGroup).order_by(PermissionGroup.name).all()
    memberships = db.query(UserPermissionGroup).all()
    members_by_group: dict[int, list[int]] = {}
    for membership in memberships:
        members_by_group.setdefault(membership.group_id, []).append(membership.user_uid)
    return [_permission_group_payload(group, members_by_group.get(group.id, [])) for group in groups]


@router.post("/permission-groups", status_code=201)
async def create_permission_group(data: dict, current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    name = str(data.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "权限组名称不能为空")
    if db.query(PermissionGroup).filter(PermissionGroup.name == name).first():
        raise HTTPException(409, "权限组已存在")
    permissions = [str(item).strip() for item in data.get("permissions", []) if str(item).strip()]
    group = PermissionGroup(name=name, description=data.get("description"), permissions=permissions)
    db.add(group)
    db.flush()
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="create",
        target_type="permission_group",
        target_id=group.id,
        details={"name": group.name},
    ))
    db.commit()
    db.refresh(group)
    return _permission_group_payload(group, [])


@router.put("/permission-groups/{group_id}")
async def update_permission_group(group_id: int, data: dict, current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    group = db.get(PermissionGroup, group_id)
    if group is None:
        raise HTTPException(404, "权限组不存在")
    values = {}
    if "name" in data:
        name = str(data["name"]).strip()
        if not name:
            raise HTTPException(400, "权限组名称不能为空")
        duplicate = db.query(PermissionGroup).filter(
            PermissionGroup.name == name,
            PermissionGroup.id != group_id,
        ).first()
        if duplicate:
            raise HTTPException(409, "权限组已存在")
        values["name"] = name
    if "description" in data:
        values["description"] = str(data["description"]).strip() or None
    if "permissions" in data:
        values["permissions"] = [str(item).strip() for item in data["permissions"] if str(item).strip()]
    for key, value in values.items():
        setattr(group, key, value)
    group.updated_at = datetime.utcnow()
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="update",
        target_type="permission_group",
        target_id=group.id,
        details={"fields": list(values)},
    ))
    db.commit()
    db.refresh(group)
    members = [item.user_uid for item in db.query(UserPermissionGroup).filter(UserPermissionGroup.group_id == group.id).all()]
    return _permission_group_payload(group, members)


@router.delete("/permission-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission_group(group_id: int, current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    group = db.get(PermissionGroup, group_id)
    if group is None:
        raise HTTPException(404, "权限组不存在")
    db.query(UserPermissionGroup).filter(UserPermissionGroup.group_id == group_id).delete(synchronize_session=False)
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete",
        target_type="permission_group",
        target_id=group.id,
        details={"name": group.name},
    ))
    db.delete(group)
    db.commit()


@router.put("/permission-groups/{group_id}/members/{uid}")
async def assign_permission_group(group_id: int, uid: int, current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    if not db.get(PermissionGroup, group_id) or not db.get(User, uid):
        raise HTTPException(404, "权限组或用户不存在")
    if not db.query(UserPermissionGroup).filter_by(user_uid=uid, group_id=group_id).first():
        db.add(UserPermissionGroup(user_uid=uid, group_id=group_id))
        db.add(OperationLog(
            operator_uid=current_user.uid,
            operator_roles=[current_user.role.value],
            action_type="assign",
            target_type="permission_group_member",
            target_id=uid,
            details={"group_id": group_id},
        ))
        db.commit()
    return {"user_uid": uid, "group_id": group_id, "assigned": True}


@router.delete("/permission-groups/{group_id}/members/{uid}")
async def remove_permission_group(group_id: int, uid: int, current_user: User = Depends(get_current_root_user), db: Session = Depends(get_db)):
    membership = db.query(UserPermissionGroup).filter_by(user_uid=uid, group_id=group_id).first()
    if membership:
        db.delete(membership)
        db.add(OperationLog(
            operator_uid=current_user.uid,
            operator_roles=[current_user.role.value],
            action_type="remove",
            target_type="permission_group_member",
            target_id=uid,
            details={"group_id": group_id},
        ))
        db.commit()
    return {"user_uid": uid, "group_id": group_id, "assigned": False}


@router.post("/reports", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def submit_report(
    data: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit a report; moderation decisions are restricted to admins."""
    try:
        target = validate_report_target(
            db,
            data.target_type,
            data.target_id,
            current_user.uid,
        )
    except ReportTargetError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    lock_report_submission(
        db,
        current_user.uid,
        target.target_type.value,
        target.target_id,
    )
    duplicate = db.query(Report).filter(
        Report.reporter_uid == current_user.uid,
        Report.target_type == target.target_type,
        Report.target_id == target.target_id,
        Report.status == ReportStatus.PENDING,
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "REPORT_ALREADY_PENDING", "message": "该目标已有待处理举报"},
        )
    report = Report(
        reporter_uid=current_user.uid,
        target_type=target.target_type,
        target_id=target.target_id,
        reason=data.reason.strip(),
    )
    db.add(report)
    db.flush()
    reporter_content = f"你的举报 #{report.id} 已提交，管理员会尽快处理。"
    notify_user(
        db,
        current_user,
        NotificationType.REPORT_RESULT,
        "举报已提交",
        reporter_content,
        related_entity_type="report",
        related_entity_id=report.id,
    )
    if target.author_uid:
        target_user = db.get(User, target.author_uid)
        notify_user(
            db,
            target_user,
            NotificationType.REPORT_RESULT,
            "收到举报提醒",
            f"你的内容或账号收到举报 #{report.id}，管理员将进行审核。",
            related_entity_type="report",
            related_entity_id=report.id,
        )
    admins = db.query(User).filter(
        User.role.in_([UserRole.ADMIN, UserRole.ROOT]),
        User.status.in_([UserStatus.ACTIVE, UserStatus.SILENCED]),
    ).all()
    notify_users(
        db,
        admins,
        NotificationType.REPORT_RESULT,
        "新的举报",
        f"用户 @{current_user.username} 提交了举报 #{report.id}，目标为 {target.target_type.value} #{target.target_id}。",
        related_entity_type="report",
        related_entity_id=report.id,
    )
    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/decision", response_model=ReportResponse)
async def decide_report_endpoint(
    report_id: int,
    data: ReportDecision,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    report = db.exec(
        select(Report).where(Report.id == report_id).with_for_update()
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="举报不存在")
    try:
        change = decide_report(
            {"status": report.status.value if hasattr(report.status, "value") else report.status},
            handler_uid=current_user.uid,
            accepted=data.accepted,
            result=data.result,
            now=datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report.status = change["status"]
    report.handler_uid = change["handler_uid"]
    report.handle_result = change["handle_result"]
    report.handled_at = change["handled_at"]
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="report_decision",
        target_type="report",
        target_id=report.id,
        details={"accepted": data.accepted, "result": data.result},
    ))
    decision_label = "采纳" if data.accepted else "未采纳"
    decision_content = f"你提交的举报 #{report.id} 已{decision_label}：{report.handle_result}。操作人：@{current_user.username}（UID {current_user.uid}）"
    reporter = db.get(User, report.reporter_uid)
    notify_user(
        db,
        reporter,
        NotificationType.REPORT_RESULT,
        "举报处理结果",
        decision_content,
        related_entity_type="report",
        related_entity_id=report.id,
    )
    target = inspect_report_target(db, report.target_type, report.target_id)
    if target.author_uid and target.author_uid != report.reporter_uid:
        notify_user(
            db,
            db.get(User, target.author_uid),
            NotificationType.REPORT_RESULT,
            "举报处理结果",
            f"涉及你的举报 #{report.id} 已{decision_label}。操作人：@{current_user.username}（UID {current_user.uid}）",
            related_entity_type="report",
            related_entity_id=report.id,
        )
    db.commit()
    db.refresh(report)
    return report


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
    statuses_changed = False
    for user in users:
        if user.status in {UserStatus.BANNED, UserStatus.SILENCED}:
            statuses_changed = sync_user_punishment_status(db, user) or statuses_changed
    if statuses_changed:
        db.commit()
    user_uids = [user.uid for user in users]
    memberships = db.query(UserPermissionGroup).filter(
        UserPermissionGroup.user_uid.in_(user_uids)
    ).all() if user_uids else []
    groups_by_user: dict[int, list[int]] = {}
    for membership in memberships:
        groups_by_user.setdefault(membership.user_uid, []).append(membership.group_id)

    items = []
    for user in users:
        items.append({
            "id": user.uid,
            "uid": user.uid,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "allow_bulk_email": user.allow_bulk_email,
            "group_ids": groups_by_user.get(user.uid, []),
            "created_at": user.created_at,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.put("/users/{uid}")
async def update_user_management(
    uid: int,
    data: AdminUserUpdate,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    lock_role_management(db)
    target = db.get(User, uid)
    if target is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    lock_user_punishments(db, target.uid)
    db.refresh(target)
    if data.role is None and data.status is None:
        raise HTTPException(status_code=400, detail="至少需要修改角色或状态")

    next_role = UserRole(data.role.value) if data.role is not None else target.role
    next_status = UserStatus(data.status.value) if data.status is not None else target.status
    punitive_statuses = {UserStatus.BANNED, UserStatus.SILENCED}
    if target.status != next_status and next_status in punitive_statuses:
        raise HTTPException(status_code=400, detail="封禁或禁言必须通过处罚功能执行")
    if target.status in punitive_statuses and next_status != target.status:
        active_punishment = db.query(Punishment).filter(
            Punishment.target_uid == target.uid,
            Punishment.punishment_type.in_([PunishmentType.BAN, PunishmentType.SILENCE]),
            Punishment.is_revoked == False,
            or_(Punishment.end_time.is_(None), Punishment.end_time > datetime.utcnow()),
        ).first()
        if active_punishment:
            raise HTTPException(status_code=409, detail="请先撤销该用户的生效处罚")
    if target.uid == current_user.uid and next_role != UserRole.ROOT:
        raise HTTPException(status_code=400, detail="不能移除当前根用户权限")
    if target.uid == current_user.uid and next_status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="不能停用当前根用户")
    if target.role == UserRole.ROOT and next_status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="根用户不能被停用或处罚")
    if next_role == UserRole.ROOT and next_status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="根用户必须保持激活状态")
    if next_role == UserRole.ROOT and active_punishment_types(db, target.uid):
        raise HTTPException(status_code=409, detail="存在生效处罚的用户不能设为根用户")
    if target.role == UserRole.ROOT and next_role != UserRole.ROOT:
        root_count = db.query(User).filter(User.role == UserRole.ROOT).count()
        if root_count <= 1:
            raise HTTPException(status_code=400, detail="系统至少需要保留一个根用户")

    changed = target.role != next_role or target.status != next_status
    target.role = next_role
    target.status = next_status
    if changed:
        target.token_version += 1
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="user_update",
        target_type="user",
        target_id=target.uid,
        details={"role": target.role.value, "status": target.status.value},
    ))
    db.commit()
    db.refresh(target)
    return {
        "uid": target.uid,
        "username": target.username,
        "nickname": target.nickname,
        "email": target.email,
        "role": target.role,
        "status": target.status,
        "token_version": target.token_version,
    }


@router.delete("/users/{uid}/pending", response_model=MessageResponse)
async def delete_pending_user(
    uid: int,
    current_user: User = Depends(get_current_root_user),
    db: Session = Depends(get_db),
):
    lock_uid_allocation(db)
    target = db.exec(
        select(User).where(User.uid == uid).with_for_update()
    ).first()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target.status != UserStatus.PENDING_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="只能删除待邮箱验证账号",
        )

    target_username = target.username
    target_email = target.email
    delete_pending_account_dependencies(db, target.uid)
    if db.get(ReusableUserUid, target.uid) is None:
        db.add(ReusableUserUid(uid=target.uid, released_at=datetime.utcnow()))
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete_pending_user",
        target_type="user",
        target_id=target.uid,
        details={"username": target_username, "email": target_email},
    ))
    db.delete(target)
    db.commit()
    return {"message": f"待验证账号 @{target_username} 已删除，UID {uid} 已回收"}


@router.post("/punish", response_model=PunishmentResponse)
async def create_punishment(
    punishment_data: PunishmentCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """执行处罚"""
    lock_role_management(db)
    current_user = db.get(User, current_user.uid, populate_existing=True)
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无法验证管理员身份")
    if current_user.role not in {UserRole.ADMIN, UserRole.ROOT} or current_user.status in {
        UserStatus.BANNED,
        UserStatus.PENDING_EMAIL,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员权限已失效")
    target_user = db.query(User).filter(User.uid == punishment_data.target_uid).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    lock_user_punishments(db, target_user.uid)
    db.refresh(target_user)

    if target_user.uid == current_user.uid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能处罚自己")
    if target_user.role == UserRole.ROOT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="根用户不能被处罚")
    if not can_manage_role(current_user.role.value, target_user.role.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色不能处罚目标用户")

    try:
        punishment_type = PunishmentType(punishment_data.punishment_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="处罚类型无效") from exc
    reason = punishment_data.reason.strip()
    if len(reason) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="处罚原因至少需要 2 个字符")
    now = datetime.utcnow()
    if punishment_data.end_time is not None and punishment_data.end_time <= now:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="处罚结束时间必须晚于当前时间")
    duplicate = db.query(Punishment).filter(
        Punishment.target_uid == target_user.uid,
        Punishment.punishment_type == punishment_type,
        Punishment.is_revoked == False,
        or_(Punishment.end_time.is_(None), Punishment.end_time > now),
    ).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户已有同类型生效处罚")

    db_punishment = Punishment(
        target_uid=punishment_data.target_uid,
        operator_uid=current_user.uid,
        punishment_type=punishment_type,
        reason=reason,
        end_time=punishment_data.end_time,
        related_content_id=punishment_data.related_content_id,
        start_time=now,
    )

    db.add(db_punishment)
    db.flush()

    # 根据全部生效处罚更新用户状态，封禁始终优先于禁言。
    previous_status = target_user.status
    active_types = active_punishment_types(db, target_user.uid, now)
    target_user.status = effective_user_status(db, target_user, active_types)
    if target_user.status != previous_status:
        target_user.token_version += 1

    # 记录操作日志
    log = OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type=ActionType.PUNISH,
        target_type="user",
        target_id=punishment_data.target_uid,
        details={"punishment_type": punishment_type.value, "reason": reason},
    )
    db.add(log)
    action_label = '封禁' if punishment_type == PunishmentType.BAN else '禁言' if punishment_type == PunishmentType.SILENCE else '处罚'
    notify_user(
        db,
        target_user,
        NotificationType.PUNISHMENT,
        "账号处罚通知",
        f"你的账号受到{action_label}：{reason}。操作人：@{current_user.username}（UID {current_user.uid}）",
        related_entity_type="punishment",
        related_entity_id=db_punishment.id,
    )

    db.commit()
    db.refresh(db_punishment)

    return db_punishment


@router.post("/punish/{punishment_id}/revoke", response_model=PunishmentResponse)
async def revoke_punishment(
    punishment_id: int,
    revoke_data: PunishmentRevoke,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """撤销当前管理员有权管理的处罚。"""
    lock_role_management(db)
    current_user = db.get(User, current_user.uid, populate_existing=True)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证管理员身份",
        )
    punishment = db.query(Punishment).filter(Punishment.id == punishment_id).first()
    if not punishment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="处罚记录不存在")

    if punishment.is_revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="处罚已被撤销")

    revoke_reason = revoke_data.revoke_reason.strip()
    if len(revoke_reason) < 2:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="撤销原因至少需要 2 个字符")

    target_user = db.query(User).filter(User.uid == punishment.target_uid).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if target_user.uid == current_user.uid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能撤销自己的处罚")
    if not can_manage_role(current_user.role.value, target_user.role.value):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色不能管理目标用户")

    lock_user_punishments(db, punishment.target_uid)
    db.refresh(punishment)
    db.refresh(target_user)
    if punishment.is_revoked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="处罚已被撤销")

    punishment.is_revoked = True
    punishment.revoked_at = datetime.utcnow()
    punishment.revoked_by = current_user.uid
    punishment.revoke_reason = revoke_reason

    # 恢复用户状态
    if target_user:
        previous_status = target_user.status
        now = datetime.utcnow()
        active_types = active_punishment_types(
            db,
            punishment.target_uid,
            now,
            exclude_id=punishment.id,
        )
        target_user.status = effective_user_status(db, target_user, active_types)
        if target_user.status != previous_status:
            target_user.token_version += 1

    # 记录操作日志
    log = OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type=ActionType.REVOKE_PUNISHMENT,
        target_type="punishment",
        target_id=punishment_id,
        details={"revoke_reason": revoke_reason},
    )
    db.add(log)
    if target_user:
        notify_user(
            db,
            target_user,
            NotificationType.PUNISHMENT_REVOKED,
            "处罚已撤销",
            f"处罚 #{punishment.id} 已撤销：{punishment.revoke_reason}。操作人：@{current_user.username}（UID {current_user.uid}）",
            related_entity_type="punishment",
            related_entity_id=punishment.id,
        )

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
    now = datetime.utcnow()

    items = []
    for p in punishments:
        items.append({
            "id": p.id,
            "target_uid": p.target_uid,
            "operator_uid": p.operator_uid,
            "punishment_type": p.punishment_type,
            "reason": p.reason,
            "start_time": p.start_time,
            "end_time": p.end_time,
            "is_revoked": p.is_revoked,
            "is_active": not p.is_revoked and (p.end_time is None or p.end_time > now),
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
        target = inspect_report_target(db, report.target_type, report.target_id)
        items.append({
            "id": report.id,
            "reporter_uid": report.reporter_uid,
            "target_type": report.target_type,
            "target_id": report.target_id,
            "reason": report.reason,
            "status": report.status,
            "handler_uid": report.handler_uid,
            "handle_result": report.handle_result,
            "handled_at": report.handled_at,
            "target_exists": target.exists,
            "target_url": target.url,
            "target_author_uid": target.author_uid,
            "target_preview": target.preview,
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
    operator_uids = {log.operator_uid for log in logs}
    operators = db.query(User).filter(User.uid.in_(operator_uids)).all() if operator_uids else []
    usernames = {operator.uid: operator.username for operator in operators}

    items = []
    for log in logs:
        items.append({
            "id": log.id,
            "operator_uid": log.operator_uid,
            "operator_username": usernames.get(log.operator_uid),
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
