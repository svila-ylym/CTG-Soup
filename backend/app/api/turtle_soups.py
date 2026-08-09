"""Canonical turtle soup API with normalized taxonomy metadata."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_current_user, get_optional_current_user
from app.models.database import Comment, CommentTargetType, Favorite, Like, MentionTargetType, Rating, Soup, SoupTag, Tag, TagKind, TagStatus, User, get_db
from app.schemas.soups import (
    AuthorSummary,
    SoupCreate,
    SoupPageResponse,
    SoupResponse,
    SoupUpdate,
    TagResponse,
)
from app.services.soup_rules import validate_score
from app.services.competition_entries import evaluate_soup_competitions
from app.services.mentions import mention_refs, notify_comment_reply, sync_mentions
from app.services.tag_rules import normalize_tag_name

router = APIRouter()


class RatingInput(BaseModel):
    score: float = Field(ge=1, le=10)

    @field_validator("score")
    @classmethod
    def half_step(cls, value: float) -> float:
        try:
            return validate_score(value)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


class InteractionInput(BaseModel):
    active: bool


class CommentInput(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("content")
    @classmethod
    def plain_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("评论不能为空")
        if "<" in normalized or ">" in normalized:
            raise ValueError("评论不允许 HTML")
        return normalized


def _comment_payload(
    db: Session,
    comment: Comment,
    replies: Optional[list[dict]] = None,
) -> dict:
    return {
        "id": comment.id,
        "content": comment.content,
        "author_uid": comment.author_uid,
        "author": _author(db, comment.author_uid),
        "parent_id": comment.parent_id,
        "created_at": comment.created_at,
        "replies": replies or [],
        "mentions": mention_refs(db, MentionTargetType.COMMENT, comment.id),
    }


def _refresh_soup_rating(db: Session, soup: Soup) -> None:
    ratings = db.exec(select(Rating).where(Rating.soup_id == soup.id)).all()
    soup.avg_rating = round(sum(item.score for item in ratings) / len(ratings), 2) if ratings else 0.0
    soup.rating_count = len(ratings)


def _refresh_soup_interaction_count(db: Session, soup: Soup, kind: str) -> None:
    model = Like if kind == "like" else Favorite
    count = len(db.exec(select(model).where(model.target_type == "soup", model.target_id == soup.id)).all())
    if kind == "like":
        soup.like_count = count
    else:
        soup.favorite_count = count


def _author(db: Session, uid: int) -> AuthorSummary:
    user = db.get(User, uid)
    return AuthorSummary(
        uid=uid,
        username=user.username if user else "unknown",
        nickname=user.nickname if user else "未知用户",
    )


def _tags(db: Session, soup_id: int) -> list[Tag]:
    return db.exec(
        select(Tag)
        .join(SoupTag, SoupTag.tag_id == Tag.id)
        .where(SoupTag.soup_id == soup_id)
        .order_by(Tag.sort_order, Tag.id)
    ).all()


def _can_reveal_solution(soup: Soup, reveal: bool) -> bool:
    return reveal and soup.status in {"published", "revealed"}


def _payload(
    soup: Soup,
    db: Session,
    current_user: Optional[User],
    reveal: bool = False,
) -> dict:
    is_author = bool(current_user and current_user.uid == soup.author_uid)
    can_manage = bool(
        current_user
        and (is_author or current_user.role.value in {"admin", "root"})
    )
    shown = _can_reveal_solution(soup, reveal)
    liked = favorited = False
    my_rating = None
    if current_user:
        liked = db.exec(
            select(Like).where(
                Like.user_uid == current_user.uid,
                Like.target_type == "soup",
                Like.target_id == soup.id,
            )
        ).first() is not None
        favorited = db.exec(
            select(Favorite).where(
                Favorite.user_uid == current_user.uid,
                Favorite.target_type == "soup",
                Favorite.target_id == soup.id,
            )
        ).first() is not None
        rating = db.exec(
            select(Rating).where(
                Rating.user_uid == current_user.uid,
                Rating.soup_id == soup.id,
            )
        ).first()
        my_rating = rating.score if rating else None
    return {
        "id": soup.id,
        "title": soup.title,
        "puzzle": soup.puzzle,
        "solution": soup.solution if shown else None,
        "solution_available": True,
        "is_solution_public": soup.status in {"published", "revealed"},
        "genre": soup.genre,
        "soup_color": soup.soup_color,
        "main_player_count": soup.main_player_count,
        "secondary_player_count": soup.secondary_player_count,
        "tags": _tags(db, soup.id),
        "author_uid": soup.author_uid,
        "author": _author(db, soup.author_uid),
        "average_score": soup.avg_rating,
        "rating_count": soup.rating_count,
        "bayesian_rating": soup.bayesian_rating,
        "like_count": soup.like_count,
        "favorite_count": soup.favorite_count,
        "view_count": soup.view_count,
        "status": soup.status,
        "is_liked": liked,
        "is_favorited": favorited,
        "my_rating": my_rating,
        "can_manage": can_manage,
        "created_at": soup.created_at,
        "updated_at": soup.updated_at,
    }


def _get_soup(db: Session, soup_id: int) -> Soup:
    soup = db.get(Soup, soup_id)
    if not soup or soup.status == "deleted":
        raise HTTPException(
            status_code=404,
            detail={"code": "SOUP_NOT_FOUND", "message": "海龟汤不存在"},
        )
    return soup


def _resolve_tags(db: Session, tag_ids: list[int], custom_names: list[str]) -> list[Tag]:
    tags: list[Tag] = []
    seen: set[int] = set()
    for tag_id in tag_ids:
        tag = db.get(Tag, tag_id)
        if not tag or tag.status != TagStatus.ACTIVE:
            raise HTTPException(
                status_code=422,
                detail={"code": "TAG_NOT_ACTIVE", "message": "标签不存在或已停用"},
            )
        if tag.id not in seen:
            tags.append(tag)
            seen.add(tag.id)

    for raw_name in custom_names:
        name, slug = normalize_tag_name(raw_name)
        tag = db.exec(select(Tag).where(Tag.slug == slug)).first()
        if tag and tag.status != TagStatus.ACTIVE:
            raise HTTPException(
                status_code=422,
                detail={"code": "TAG_NOT_ACTIVE", "message": "标签不存在或已停用"},
            )
        if not tag:
            tag = Tag(name=name, slug=slug, kind=TagKind.CUSTOM, status=TagStatus.ACTIVE)
            db.add(tag)
            db.flush()
        if tag.id not in seen:
            tags.append(tag)
            seen.add(tag.id)
    if len(tags) > 10:
        raise HTTPException(status_code=422, detail={"code": "TOO_MANY_TAGS", "message": "单个海龟汤最多使用10个标签"})
    return tags


def _sync_tags(db: Session, soup: Soup, tags: list[Tag]) -> None:
    old_links = db.exec(select(SoupTag).where(SoupTag.soup_id == soup.id)).all()
    affected = {link.tag_id for link in old_links} | {tag.id for tag in tags}
    for link in old_links:
        db.delete(link)
    for tag in tags:
        db.add(SoupTag(soup_id=soup.id, tag_id=tag.id))
    db.flush()
    for tag_id in affected:
        tag = db.get(Tag, tag_id)
        if tag:
            tag.usage_count = len(db.exec(select(SoupTag).where(SoupTag.tag_id == tag_id)).all())


@router.get("", response_model=SoupPageResponse)
def list_soups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: Optional[str] = None,
    tag_id: Optional[int] = Query(None, gt=0),
    genre: Optional[str] = None,
    soup_color: Optional[str] = None,
    sort_by: str = Query("created_at"),
    db: Session = Depends(get_db),
):
    query = select(Soup).where(Soup.status.in_(["published", "revealed"]))
    selected_tag: Optional[Tag] = None
    if tag_id:
        selected_tag = db.get(Tag, tag_id)
        if selected_tag:
            query = query.where(Soup.id.in_(select(SoupTag.soup_id).where(SoupTag.tag_id == tag_id)))
    elif tag:
        selected_tag = db.exec(select(Tag).where(Tag.slug == tag.casefold())).first()
        if selected_tag:
            query = query.where(Soup.id.in_(select(SoupTag.soup_id).where(SoupTag.tag_id == selected_tag.id)))
        else:
            query = query.where(Soup.id == -1)
    if genre:
        query = query.where(Soup.genre == genre)
    if soup_color:
        query = query.where(Soup.soup_color == soup_color)
    order = (
        Soup.bayesian_rating.desc()
        if sort_by in {"bayesian", "bayesian_rating"}
        else Soup.avg_rating.desc()
        if sort_by in {"score", "average_score"}
        else Soup.like_count.desc()
        if sort_by in {"likes", "like_count"}
        else Soup.created_at.desc()
    )
    total = len(db.exec(query).all())
    rows = db.exec(query.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    if selected_tag and rows:
        selected_tag.view_count += 1
        db.commit()
    return {
        "items": [_payload(row, db, None) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post("", response_model=SoupResponse, status_code=status.HTTP_201_CREATED)
def create_soup(
    data: SoupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tags = _resolve_tags(db, data.tag_ids, data.custom_tags)
    soup = Soup(
        author_uid=current_user.uid,
        title=data.title,
        puzzle=data.puzzle,
        solution=data.solution,
        genre=data.genre,
        soup_color=data.soup_color,
        main_player_count=data.main_player_count,
        secondary_player_count=data.secondary_player_count,
        status="revealed" if data.is_revealed else "published",
    )
    db.add(soup)
    db.flush()
    _sync_tags(db, soup, tags)
    db.flush()
    evaluate_soup_competitions(db, soup)
    db.refresh(soup)
    return _payload(soup, db, current_user, True)


@router.get("/{soup_id}", response_model=SoupResponse)
def get_soup(
    soup_id: int,
    reveal: bool = False,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    soup = _get_soup(db, soup_id)
    soup.view_count += 1
    db.commit()
    db.refresh(soup)
    return _payload(soup, db, current_user, reveal)


@router.put("/{soup_id}", response_model=SoupResponse)
def update_soup(
    soup_id: int,
    data: SoupUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    soup = _get_soup(db, soup_id)
    is_admin = current_user.role.value in {"admin", "root"}
    if soup.author_uid != current_user.uid and not is_admin:
        raise HTTPException(status_code=403, detail={"code": "SOUP_UPDATE_FORBIDDEN", "message": "无权更新此作品"})
    values = data.model_dump(exclude_unset=True)
    tag_values_present = "tag_ids" in values or "custom_tags" in values
    if tag_values_present:
        tags = _resolve_tags(db, values.pop("tag_ids", []), values.pop("custom_tags", []))
        _sync_tags(db, soup, tags)
    values.pop("is_revealed", None)
    if data.is_revealed is not None:
        soup.status = "revealed" if data.is_revealed else "published"
    for key, value in values.items():
        setattr(soup, key, value)
    soup.updated_at = datetime.utcnow()
    db.flush()
    evaluate_soup_competitions(db, soup)
    db.refresh(soup)
    return _payload(soup, db, current_user, True)


@router.get("/{soup_id}/comments")
def list_comments(
    soup_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _get_soup(db, soup_id)
    roots = db.exec(
        select(Comment)
        .where(
            Comment.target_type == CommentTargetType.SOUP,
            Comment.target_id == soup_id,
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
                Comment.target_type == CommentTargetType.SOUP,
                Comment.target_id == soup_id,
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


@router.post("/{soup_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    soup_id: int,
    data: CommentInput,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_soup(db, soup_id)
    parent = None
    if data.parent_id is not None:
        parent = db.get(Comment, data.parent_id)
        if (
            parent is None
            or parent.target_type != CommentTargetType.SOUP
            or parent.target_id != soup_id
            or parent.parent_id is not None
            or parent.status != "published"
        ):
            raise HTTPException(422, detail={"code": "INVALID_COMMENT_PARENT", "message": "回复目标不存在或不可回复"})
    comment = Comment(
        author_uid=current_user.uid,
        target_type=CommentTargetType.SOUP,
        target_id=soup_id,
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
    db.commit()
    db.refresh(comment)
    return _comment_payload(db, comment)


@router.delete("/{soup_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    soup_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _get_soup(db, soup_id)
    comment = db.get(Comment, comment_id)
    if (
        comment is None
        or comment.target_type != CommentTargetType.SOUP
        or comment.target_id != soup_id
        or comment.status == "deleted"
    ):
        raise HTTPException(404, detail={"code": "COMMENT_NOT_FOUND", "message": "评论不存在"})
    if comment.author_uid != current_user.uid and current_user.role.value not in {"admin", "root"}:
        raise HTTPException(403, detail={"code": "COMMENT_DELETE_FORBIDDEN", "message": "无权删除此评论"})
    comment.status = "deleted"
    comment.updated_at = datetime.utcnow()
    sync_mentions(
        db,
        current_user.uid,
        MentionTargetType.COMMENT,
        comment.id,
        "",
    )
    db.commit()


@router.put("/{soup_id}/rating")
def rate_soup(soup_id: int, data: RatingInput, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    soup = _get_soup(db, soup_id)
    if soup.author_uid == current_user.uid:
        raise HTTPException(400, detail={"code": "SELF_RATING_FORBIDDEN", "message": "不能给自己的作品评分"})
    rating = db.exec(select(Rating).where(Rating.user_uid == current_user.uid, Rating.soup_id == soup_id)).first()
    if rating:
        rating.score = data.score
        rating.updated_at = datetime.utcnow()
    else:
        try:
            with db.begin_nested():
                db.add(Rating(user_uid=current_user.uid, soup_id=soup_id, score=data.score))
                db.flush()
        except IntegrityError:
            rating = db.exec(select(Rating).where(Rating.user_uid == current_user.uid, Rating.soup_id == soup_id)).first()
            if rating is None:
                raise
            rating.score = data.score
            rating.updated_at = datetime.utcnow()
    _refresh_soup_rating(db, soup)
    db.commit()
    db.refresh(soup)
    return {"average_score": soup.avg_rating, "rating_count": soup.rating_count, "my_rating": data.score}


@router.put("/{soup_id}/{kind}")
def set_interaction(soup_id: int, kind: str, data: InteractionInput, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    if kind not in {"like", "favorite"}:
        raise HTTPException(404, detail="交互类型不存在")
    soup = _get_soup(db, soup_id)
    model = Like if kind == "like" else Favorite
    record = db.exec(select(model).where(model.user_uid == current_user.uid, model.target_type == "soup", model.target_id == soup_id)).first()
    if data.active and not record:
        try:
            with db.begin_nested():
                db.add(model(user_uid=current_user.uid, target_type="soup", target_id=soup_id))
                db.flush()
        except IntegrityError:
            pass
    elif not data.active and record:
        db.delete(record)
    _refresh_soup_interaction_count(db, soup, kind)
    db.commit()
    active_record = db.exec(select(model).where(model.user_uid == current_user.uid, model.target_type == "soup", model.target_id == soup_id)).first() is not None
    return {"is_liked": kind == "like" and active_record, "is_favorited": kind == "favorite" and active_record, "like_count": soup.like_count, "favorite_count": soup.favorite_count}
