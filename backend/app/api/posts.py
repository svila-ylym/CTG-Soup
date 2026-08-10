from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import Comment, CommentTargetType, MentionTargetType, OperationLog, Post, User, get_db
from app.schemas.community import (
    PostCommentCreate,
    PostCommentPageResponse,
    PostCommentResponse,
    PostCreate,
    PostPageResponse,
    PostResponse,
    PostUpdate,
)
from app.services.mentions import mention_refs, notify_comment_reply, sync_mentions
from app.services.levels import level_band, level_progress
from app.services.user_display import user_display_fields

router = APIRouter()


def _author(db: Session, uid: int) -> dict:
    user = db.get(User, uid)
    progress = level_progress(user.points if user else 0)
    return {
        "uid": uid,
        "username": user.username if user else "unknown",
        "nickname": user.nickname if user else "未知用户",
        "avatar_url": user.avatar_url if user else None,
        "level": progress.level,
        "level_band": level_band(progress.level),
        **user_display_fields(db, user),
    }


def _payload(db: Session, post: Post, current_user: Optional[User] = None) -> dict:
    return {
        "id": post.id,
        "author_uid": post.author_uid,
        "author": _author(db, post.author_uid),
        "title": post.title,
        "content": post.content,
        "section": post.section,
        "post_type": post.post_type,
        "tags": post.tags,
        "status": post.status,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "favorite_count": post.favorite_count,
        "view_count": post.view_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "mentions": mention_refs(db, MentionTargetType.POST, post.id),
        "can_edit": bool(current_user and post.author_uid == current_user.uid),
    }


def _comment_payload(
    db: Session,
    comment: Comment,
    replies: Optional[list[dict]] = None,
) -> dict:
    return {
        "id": comment.id,
        "author_uid": comment.author_uid,
        "author": _author(db, comment.author_uid),
        "content": comment.content,
        "parent_id": comment.parent_id,
        "mentions": mention_refs(db, MentionTargetType.COMMENT, comment.id),
        "created_at": comment.created_at,
        "replies": replies or [],
    }


def _get_visible_post(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=404, detail="帖子不存在")
    return post


@router.post("", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    data: PostCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    post = Post(
        author_uid=current_user.uid,
        title=data.title,
        content=data.content,
        section=data.section,
        post_type=data.post_type,
        tags=list(dict.fromkeys(tag.strip() for tag in data.tags if tag.strip())),
    )
    db.add(post)
    db.flush()
    sync_mentions(
        db,
        current_user.uid,
        MentionTargetType.POST,
        post.id,
        post.content,
    )
    db.commit()
    db.refresh(post)
    return _payload(db, post, current_user)


@router.get("", response_model=PostPageResponse)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    section: Optional[str] = None,
    tag: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|like_count|comment_count)$"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = select(Post).where(Post.status == "published")
    if section:
        query = query.where(Post.section == section)
    rows = db.exec(query).all()
    if tag:
        rows = [post for post in rows if tag in post.tags]
    rows.sort(
        key=lambda post: getattr(post, sort_by),
        reverse=True,
    )
    total = len(rows)
    rows = rows[(page - 1) * page_size : page * page_size]
    return {
        "items": [_payload(db, post, current_user) for post in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    post = _get_visible_post(db, post_id)
    post.view_count += 1
    db.commit()
    db.refresh(post)
    return _payload(db, post, current_user)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    post = _get_visible_post(db, post_id)
    if post.author_uid != current_user.uid:
        raise HTTPException(status_code=403, detail="只能修改自己的帖子")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(post, key, value)
    if data.content is not None:
        post.content = data.content
        sync_mentions(
            db,
            current_user.uid,
            MentionTargetType.POST,
            post.id,
            post.content,
        )
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return _payload(db, post, current_user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    post = _get_visible_post(db, post_id)
    if post.author_uid != current_user.uid and current_user.role.value not in {"admin", "root"}:
        raise HTTPException(status_code=403, detail="无权删除此帖子")
    post.status = "deleted"
    post.updated_at = datetime.utcnow()
    sync_mentions(db, current_user.uid, MentionTargetType.POST, post.id, "")
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete",
        target_type="post",
        target_id=post.id,
        details={"title": post.title},
    ))
    db.commit()


@router.get("/{post_id}/comments", response_model=PostCommentPageResponse)
def list_post_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _get_visible_post(db, post_id)
    roots = db.exec(
        select(Comment)
        .where(
            Comment.target_type == CommentTargetType.POST,
            Comment.target_id == post_id,
            Comment.parent_id.is_(None),
            Comment.status == "published",
        )
        .order_by(Comment.created_at.desc(), Comment.id.desc())
    ).all()
    total = len(roots)
    roots = roots[(page - 1) * page_size : page * page_size]
    root_ids = [comment.id for comment in roots]
    replies_by_parent: dict[int, list[dict]] = {comment_id: [] for comment_id in root_ids}
    if root_ids:
        replies = db.exec(
            select(Comment)
            .where(
                Comment.target_type == CommentTargetType.POST,
                Comment.target_id == post_id,
                Comment.parent_id.in_(root_ids),
                Comment.status == "published",
            )
            .order_by(Comment.created_at, Comment.id)
        ).all()
        for reply in replies:
            replies_by_parent[reply.parent_id].append(_comment_payload(db, reply))
    return {
        "items": [
            _comment_payload(db, comment, replies_by_parent[comment.id])
            for comment in roots
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post(
    "/{post_id}/comments",
    response_model=PostCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post_comment(
    post_id: int,
    data: PostCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    post = _get_visible_post(db, post_id)
    parent = None
    if data.parent_id is not None:
        parent = db.get(Comment, data.parent_id)
        if (
            parent is None
            or parent.target_type != CommentTargetType.POST
            or parent.target_id != post_id
            or parent.parent_id is not None
            or parent.status != "published"
        ):
            raise HTTPException(status_code=422, detail={"code": "INVALID_COMMENT_PARENT", "message": "回复目标不存在或不可回复"})
    comment = Comment(
        author_uid=current_user.uid,
        target_type=CommentTargetType.POST,
        target_id=post_id,
        content=data.content,
        parent_id=data.parent_id,
    )
    db.add(comment)
    db.flush()
    mentions = sync_mentions(
        db,
        current_user.uid,
        MentionTargetType.COMMENT,
        comment.id,
        comment.content,
    )
    if parent is not None:
        notify_comment_reply(db, current_user.uid, parent, {item.uid for item in mentions})
    post.comment_count += 1
    db.commit()
    db.refresh(comment)
    return _comment_payload(db, comment)


@router.delete("/{post_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post_comment(
    post_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    post = _get_visible_post(db, post_id)
    comment = db.get(Comment, comment_id)
    if (
        comment is None
        or comment.target_type != CommentTargetType.POST
        or comment.target_id != post_id
        or comment.status == "deleted"
    ):
        raise HTTPException(status_code=404, detail="评论不存在")
    if comment.author_uid != current_user.uid and current_user.role.value not in {"admin", "root"}:
        raise HTTPException(status_code=403, detail="无权删除此评论")

    comments = [comment]
    if comment.parent_id is None:
        comments.extend(db.exec(
            select(Comment).where(
                Comment.target_type == CommentTargetType.POST,
                Comment.target_id == post_id,
                Comment.parent_id == comment.id,
                Comment.status == "published",
            )
        ).all())
    for item in comments:
        item.status = "deleted"
        item.updated_at = datetime.utcnow()
        sync_mentions(db, current_user.uid, MentionTargetType.COMMENT, item.id, "")
    post.comment_count = max(0, post.comment_count - len(comments))
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete",
        target_type="comment",
        target_id=comment.id,
        details={"post_id": post.id, "deleted_count": len(comments)},
    ))
    db.commit()
