"""Canonical turtle soup API with normalized taxonomy metadata."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.api.auth import get_current_active_user, get_current_user, get_optional_current_user
from app.models.database import Comment, CommentTargetType, Favorite, Like, MentionTargetType, OperationLog, Rating, Soup, SoupImage, SoupTag, Tag, UploadedAsset, User, get_db
from app.schemas.soups import (
    AuthorSummary,
    SoupCreate,
    SoupPageResponse,
    SoupResponse,
    SoupUpdate,
    TagResponse,
)
from app.services.soup_rules import validate_score
from app.services.competition_entries import (
    evaluate_soup_competitions,
    remove_soup_from_unsettled_competitions,
    refresh_soup_competition_scores,
)
from app.services.mentions import mention_refs, notify_comment_reply, sync_mentions
from app.services.tag_resolution import TagSelectionError, resolve_active_tags
from app.services.levels import level_band, level_progress

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
    progress = level_progress(user.points if user else 0)
    return AuthorSummary(
        uid=uid,
        username=user.username if user else "unknown",
        nickname=user.nickname if user else "未知用户",
        level=progress.level,
        level_band=level_band(progress.level),
    )


def _tags(db: Session, soup_id: int) -> list[Tag]:
    return db.exec(
        select(Tag)
        .join(SoupTag, SoupTag.tag_id == Tag.id)
        .where(SoupTag.soup_id == soup_id)
        .order_by(Tag.sort_order, Tag.id)
    ).all()


def _soup_images(db: Session, soup_id: int, placement: str) -> list[UploadedAsset]:
    return db.exec(
        select(UploadedAsset)
        .join(SoupImage, SoupImage.asset_id == UploadedAsset.id)
        .where(
            SoupImage.soup_id == soup_id,
            SoupImage.placement == placement,
        )
        .order_by(SoupImage.sort_order)
    ).all()


def _soup_comment_counts(db: Session, soup_ids: list[int]) -> dict[int, int]:
    if not soup_ids:
        return {}
    rows = db.exec(
        select(Comment.target_id, func.count(Comment.id))
        .where(
            Comment.target_type == CommentTargetType.SOUP,
            Comment.target_id.in_(soup_ids),
            Comment.parent_id.is_(None),
            Comment.status == "published",
        )
        .group_by(Comment.target_id)
    ).all()
    return {target_id: count for target_id, count in rows}


def _can_reveal_solution(soup: Soup, reveal: bool) -> bool:
    return reveal and soup.status in {"published", "revealed"}


def _payload(
    soup: Soup,
    db: Session,
    current_user: Optional[User],
    reveal: bool = False,
    comment_count: Optional[int] = None,
) -> dict:
    is_author = bool(current_user and current_user.uid == soup.author_uid)
    can_manage = bool(
        current_user
        and (is_author or current_user.role.value in {"admin", "root"})
    )
    shown = _can_reveal_solution(soup, reveal)
    puzzle_images = _soup_images(db, soup.id, "puzzle")
    solution_images = _soup_images(db, soup.id, "solution") if shown else []
    if comment_count is None:
        comment_count = _soup_comment_counts(db, [soup.id]).get(soup.id, 0)
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
        "puzzle_images": puzzle_images,
        "solution_images": solution_images,
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
        "comment_count": comment_count,
        "like_count": soup.like_count,
        "favorite_count": soup.favorite_count,
        "view_count": soup.view_count,
        "status": soup.status,
        "is_liked": liked,
        "is_favorited": favorited,
        "my_rating": my_rating,
        "can_manage": can_manage,
        "can_edit": is_author,
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


def _rating_soup_statement(soup_id: int):
    return select(Soup).where(Soup.id == soup_id).with_for_update()


def _get_soup_for_rating(db: Session, soup_id: int) -> Soup:
    soup = db.exec(_rating_soup_statement(soup_id)).first()
    if not soup or soup.status == "deleted":
        raise HTTPException(
            status_code=404,
            detail={"code": "SOUP_NOT_FOUND", "message": "海龟汤不存在"},
        )
    return soup


def _resolve_tags(db: Session, tag_ids: list[int], custom_names: list[str]) -> list[Tag]:
    try:
        return resolve_active_tags(
            db,
            tag_ids,
            custom_names,
            min_count=0,
            max_count=10,
        )
    except TagSelectionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


def _resolve_owned_images(
    db: Session,
    owner_uid: int,
    puzzle_ids: list[int],
    solution_ids: list[int],
) -> tuple[list[UploadedAsset], list[UploadedAsset]]:
    all_ids = [*puzzle_ids, *solution_ids]
    if len(all_ids) != len(set(all_ids)):
        raise HTTPException(
            status_code=422,
            detail={"code": "DUPLICATE_SOUP_IMAGE", "message": "同一图片不能重复添加"},
        )
    if not all_ids:
        return [], []
    assets = db.exec(
        select(UploadedAsset).where(UploadedAsset.id.in_(all_ids))
    ).all()
    by_id = {asset.id: asset for asset in assets}
    if any(
        asset_id not in by_id
        or by_id[asset_id].owner_uid != owner_uid
        or by_id[asset_id].kind != "image"
        for asset_id in all_ids
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_SOUP_IMAGE", "message": "图片不存在或不属于当前用户"},
        )
    return (
        [by_id[asset_id] for asset_id in puzzle_ids],
        [by_id[asset_id] for asset_id in solution_ids],
    )


def _validate_content_presence(
    puzzle: str,
    solution: str,
    puzzle_assets: list[UploadedAsset],
    solution_assets: list[UploadedAsset],
) -> None:
    if not puzzle.strip() and not puzzle_assets:
        raise HTTPException(
            status_code=422,
            detail={"code": "PUZZLE_CONTENT_REQUIRED", "message": "谜面需要文字或图片"},
        )
    if not solution.strip() and not solution_assets:
        raise HTTPException(
            status_code=422,
            detail={"code": "SOLUTION_CONTENT_REQUIRED", "message": "汤底需要文字或图片"},
        )


def _sync_soup_images(
    db: Session,
    soup_id: int,
    puzzle_assets: list[UploadedAsset],
    solution_assets: list[UploadedAsset],
) -> None:
    for row in db.exec(select(SoupImage).where(SoupImage.soup_id == soup_id)).all():
        db.delete(row)
    for placement, assets in (
        ("puzzle", puzzle_assets),
        ("solution", solution_assets),
    ):
        for sort_order, asset in enumerate(assets):
            db.add(SoupImage(
                soup_id=soup_id,
                asset_id=asset.id,
                placement=placement,
                sort_order=sort_order,
            ))
    db.flush()


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
        (
            Soup.avg_rating.desc(),
            Soup.rating_count.desc(),
            Soup.created_at.desc(),
            Soup.id.desc(),
        )
        if sort_by in {"score", "average_score"}
        else (Soup.like_count.desc(),)
        if sort_by in {"likes", "like_count"}
        else (Soup.created_at.desc(),)
    )
    total = len(db.exec(query).all())
    rows = db.exec(query.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    if selected_tag and rows:
        selected_tag.view_count += 1
        db.commit()
    comment_counts = _soup_comment_counts(db, [row.id for row in rows])
    return {
        "items": [
            _payload(row, db, None, comment_count=comment_counts.get(row.id, 0))
            for row in rows
        ],
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
    puzzle_assets, solution_assets = _resolve_owned_images(
        db,
        current_user.uid,
        data.puzzle_image_ids,
        data.solution_image_ids,
    )
    _validate_content_presence(data.puzzle, data.solution, puzzle_assets, solution_assets)
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
    _sync_soup_images(db, soup.id, puzzle_assets, solution_assets)
    _sync_tags(db, soup, tags)
    db.flush()
    evaluate_soup_competitions(db, soup)
    db.commit()
    db.refresh(soup)
    return _payload(soup, db, current_user, True, comment_count=0)


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
    if soup.author_uid != current_user.uid:
        raise HTTPException(status_code=403, detail={"code": "SOUP_UPDATE_FORBIDDEN", "message": "无权更新此作品"})
    values = data.model_dump(exclude_unset=True)
    current_puzzle_assets = _soup_images(db, soup.id, "puzzle")
    current_solution_assets = _soup_images(db, soup.id, "solution")
    puzzle_ids = values.pop(
        "puzzle_image_ids",
        [asset.id for asset in current_puzzle_assets],
    )
    solution_ids = values.pop(
        "solution_image_ids",
        [asset.id for asset in current_solution_assets],
    )
    puzzle_assets, solution_assets = _resolve_owned_images(
        db,
        current_user.uid,
        puzzle_ids,
        solution_ids,
    )
    effective_puzzle = values.get("puzzle", soup.puzzle)
    effective_solution = values.get("solution", soup.solution)
    _validate_content_presence(
        effective_puzzle,
        effective_solution,
        puzzle_assets,
        solution_assets,
    )
    tag_values_present = "tag_ids" in values or "custom_tags" in values
    if tag_values_present:
        tags = _resolve_tags(db, values.pop("tag_ids", []), values.pop("custom_tags", []))
        _sync_tags(db, soup, tags)
    values.pop("is_revealed", None)
    if data.is_revealed is not None:
        soup.status = "revealed" if data.is_revealed else "published"
    for key, value in values.items():
        setattr(soup, key, value)
    _sync_soup_images(db, soup.id, puzzle_assets, solution_assets)
    soup.updated_at = datetime.utcnow()
    db.flush()
    evaluate_soup_competitions(db, soup)
    db.commit()
    db.refresh(soup)
    return _payload(soup, db, current_user, True)


@router.delete("/{soup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    soup = _get_soup(db, soup_id)
    if soup.author_uid != current_user.uid and current_user.role.value not in {"admin", "root"}:
        raise HTTPException(
            status_code=403,
            detail={"code": "SOUP_DELETE_FORBIDDEN", "message": "无权删除此海龟汤"},
        )
    previous_status = soup.status
    soup.status = "deleted"
    soup.updated_at = datetime.utcnow()
    removed_entries = remove_soup_from_unsettled_competitions(db, soup.id)
    db.add(OperationLog(
        operator_uid=current_user.uid,
        operator_roles=[current_user.role.value],
        action_type="delete",
        target_type="soup",
        target_id=soup.id,
        details={
            "title": soup.title,
            "previous_status": previous_status,
            "removed_competition_entries": removed_entries,
        },
    ))
    db.commit()


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


def _rating_already_submitted() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "RATING_ALREADY_SUBMITTED",
            "message": "评分确认后不可修改",
        },
    )


@router.put("/{soup_id}/rating")
def rate_soup(soup_id: int, data: RatingInput, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    soup = _get_soup_for_rating(db, soup_id)
    if soup.author_uid == current_user.uid:
        raise HTTPException(400, detail={"code": "SELF_RATING_FORBIDDEN", "message": "不能给自己的作品评分"})
    rating = db.exec(select(Rating).where(Rating.user_uid == current_user.uid, Rating.soup_id == soup_id)).first()
    if rating:
        raise _rating_already_submitted()
    try:
        with db.begin_nested():
            db.add(Rating(user_uid=current_user.uid, soup_id=soup_id, score=data.score))
            db.flush()
    except IntegrityError as exc:
        raise _rating_already_submitted() from exc
    _refresh_soup_rating(db, soup)
    refresh_soup_competition_scores(db, soup)
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
