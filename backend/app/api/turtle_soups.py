from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import redis
import json

from app.models.database import get_db, TurtleSoup, Rating, User, Like, Collection, Competition, CompetitionEntry
from app.schemas import TurtleSoupCreate, TurtleSoupUpdate, TurtleSoupResponse, RatingCreate, PageResponse
from app.api.auth import get_current_active_user, get_current_user
from app.core.config import get_settings

router = APIRouter()

settings = get_settings()

# Redis客户端用于缓存排行榜
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def calculate_bayesian_average(avg_score: float, rating_count: int) -> float:
    """计算贝叶斯平均分"""
    C = settings.BAYESIAN_C  # 先验评分数量
    M = settings.BAYESIAN_M  # 先验平均分
    
    if rating_count == 0:
        return M
    
    return (C * M + rating_count * avg_score) / (C + rating_count)


def update_soup_rating(soup_id: int, db: Session):
    """更新海龟汤评分"""
    ratings = db.query(Rating).filter(Rating.turtle_soup_id == soup_id).all()
    
    if not ratings:
        soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
        if soup:
            soup.average_score = 0.0
            soup.rating_count = 0
            db.commit()
        return
    
    total_score = sum(r.score for r in ratings)
    count = len(ratings)
    avg_score = total_score / count
    
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if soup:
        soup.average_score = round(avg_score, 2)
        soup.rating_count = count
        db.commit()
        
        # 更新Redis缓存的排行榜
        bayesian_score = calculate_bayesian_average(avg_score, count)
        redis_client.zadd("turtle_soup_ranking", {str(soup_id): bayesian_score})


@router.get("/ranking", response_model=PageResponse)
async def get_turtle_soup_ranking(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取海龟汤排行榜（基于贝叶斯平均分）"""
    # 从Redis获取排行榜
    offset = (page - 1) * page_size
    soup_ids_with_scores = redis_client.zrevrange(
        "turtle_soup_ranking",
        offset,
        offset + page_size - 1,
        withscores=True
    )
    
    if not soup_ids_with_scores:
        # 如果Redis为空，从数据库重新构建
        soups = db.query(TurtleSoup).filter(
            TurtleSoup.status == "published"
        ).order_by(TurtleSoup.average_score.desc()).limit(page_size).all()
        
        items = []
        for soup in soups:
            bayesian_score = calculate_bayesian_average(soup.average_score, soup.rating_count)
            items.append({
                "id": soup.id,
                "title": soup.title,
                "puzzle": soup.puzzle,
                "tags": soup.tags,
                "author_id": soup.author_id,
                "author_username": soup.author.username,
                "author_nickname": soup.author.nickname,
                "average_score": soup.average_score,
                "bayesian_score": round(bayesian_score, 2),
                "rating_count": soup.rating_count,
                "like_count": soup.like_count,
                "collect_count": soup.collect_count,
                "view_count": soup.view_count,
                "is_revealed": soup.is_revealed,
                "created_at": soup.created_at,
            })
        
        total = db.query(TurtleSoup).filter(TurtleSoup.status == "published").count()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    items = []
    for soup_id, bayesian_score in soup_ids_with_scores:
        soup = db.query(TurtleSoup).filter(TurtleSoup.id == int(soup_id)).first()
        if soup and soup.status == "published":
            items.append({
                "id": soup.id,
                "title": soup.title,
                "puzzle": soup.puzzle,
                "tags": soup.tags,
                "author_id": soup.author_id,
                "author_username": soup.author.username,
                "author_nickname": soup.author.nickname,
                "average_score": soup.average_score,
                "bayesian_score": round(bayesian_score, 2),
                "rating_count": soup.rating_count,
                "like_count": soup.like_count,
                "collect_count": soup.collect_count,
                "view_count": soup.view_count,
                "is_revealed": soup.is_revealed,
                "created_at": soup.created_at,
            })
    
    total = redis_client.zcard("turtle_soup_ranking")
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("", response_model=TurtleSoupResponse, status_code=status.HTTP_201_CREATED)
async def create_turtle_soup(
    soup_data: TurtleSoupCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发布海龟汤"""
    db_soup = TurtleSoup(
        author_id=current_user.id,
        title=soup_data.title,
        puzzle=soup_data.puzzle,
        solution=soup_data.solution,
        tags=soup_data.tags,
        status="published",
    )
    
    db.add(db_soup)
    db.commit()
    db.refresh(db_soup)
    
    # 检查是否有进行中的比赛包含此标签
    competitions = db.query(Competition).filter(
        Competition.status == "ongoing",
        Competition.entry_tags.overlap(soup_data.tags)  # PostgreSQL JSONB操作符
    ).all()
    
    for competition in competitions:
        entry = CompetitionEntry(
            competition_id=competition.id,
            turtle_soup_id=db_soup.id,
            author_id=current_user.id,
        )
        db.add(entry)
    
    db.commit()
    
    return db_soup


@router.get("/{soup_id}", response_model=TurtleSoupResponse)
async def get_turtle_soup(
    soup_id: int,
    reveal: bool = False,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取海龟汤详情"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    if soup.status != "published":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="海龟汤不可见")
    
    # 增加浏览量
    soup.view_count += 1
    db.commit()
    
    # 如果不是作者且未显示汤底，则隐藏汤底
    if not reveal and not soup.is_revealed:
        is_author = current_user and current_user.id == soup.author_id
        if not is_author:
            soup_copy = TurtleSoupResponse.from_orm(soup)
            soup_copy.solution = "请先猜测或等待作者公布汤底"
            return soup_copy
    
    return soup


@router.put("/{soup_id}", response_model=TurtleSoupResponse)
async def update_turtle_soup(
    soup_id: int,
    soup_data: TurtleSoupUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新海龟汤（仅作者）"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    if soup.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限修改")
    
    if soup_data.title:
        soup.title = soup_data.title
    if soup_data.puzzle:
        soup.puzzle = soup_data.puzzle
    if soup_data.solution:
        soup.solution = soup_data.solution
    if soup_data.tags is not None:
        soup.tags = soup_data.tags
    if soup_data.is_revealed is not None:
        soup.is_revealed = soup_data.is_revealed
    
    soup.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(soup)
    
    return soup


@router.delete("/{soup_id}")
async def delete_turtle_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除海龟汤（软删除，仅作者）"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    if soup.author_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限删除")
    
    soup.status = "deleted"
    soup.deleted_at = datetime.utcnow()
    db.commit()
    
    # 从排行榜移除
    redis_client.zrem("turtle_soup_ranking", str(soup_id))
    
    return {"message": "删除成功"}


@router.post("/{soup_id}/rate")
async def rate_turtle_soup(
    soup_id: int,
    rating_data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """评分海龟汤"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    if soup.author_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能给自己的作品评分")
    
    # 检查是否已评分
    existing_rating = db.query(Rating).filter(
        Rating.user_id == current_user.id,
        Rating.turtle_soup_id == soup_id
    ).first()
    
    if existing_rating:
        existing_rating.score = rating_data.score
        existing_rating.updated_at = datetime.utcnow()
    else:
        new_rating = Rating(
            user_id=current_user.id,
            turtle_soup_id=soup_id,
            score=rating_data.score,
        )
        db.add(new_rating)
    
    db.commit()
    
    # 更新平均分
    update_soup_rating(soup_id, db)
    
    return {"message": "评分成功", "score": rating_data.score}


@router.post("/{soup_id}/like")
async def like_turtle_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """点赞海龟汤"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    # 检查是否已点赞
    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.turtle_soup_id == soup_id
    ).first()
    
    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已点赞")
    
    new_like = Like(
        user_id=current_user.id,
        target_type="turtle_soup",
        turtle_soup_id=soup_id,
    )
    db.add(new_like)
    
    soup.like_count += 1
    db.commit()
    
    return {"message": "点赞成功"}


@router.delete("/{soup_id}/like")
async def unlike_turtle_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """取消点赞海龟汤"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    existing_like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.turtle_soup_id == soup_id
    ).first()
    
    if not existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未点赞")
    
    db.delete(existing_like)
    soup.like_count -= 1
    db.commit()
    
    return {"message": "已取消点赞"}


@router.post("/{soup_id}/collect")
async def collect_turtle_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """收藏海龟汤"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    existing_collect = db.query(Collection).filter(
        Collection.user_id == current_user.id,
        Collection.turtle_soup_id == soup_id
    ).first()
    
    if existing_collect:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已收藏")
    
    new_collect = Collection(
        user_id=current_user.id,
        target_type="turtle_soup",
        turtle_soup_id=soup_id,
    )
    db.add(new_collect)
    
    soup.collect_count += 1
    db.commit()
    
    return {"message": "收藏成功"}


@router.delete("/{soup_id}/collect")
async def uncollect_turtle_soup(
    soup_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """取消收藏海龟汤"""
    soup = db.query(TurtleSoup).filter(TurtleSoup.id == soup_id).first()
    if not soup:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="海龟汤不存在")
    
    existing_collect = db.query(Collection).filter(
        Collection.user_id == current_user.id,
        Collection.turtle_soup_id == soup_id
    ).first()
    
    if not existing_collect:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未收藏")
    
    db.delete(existing_collect)
    soup.collect_count -= 1
    db.commit()
    
    return {"message": "已取消收藏"}


@router.get("")
async def list_turtle_soups(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tag: Optional[str] = None,
    sort_by: str = Query("created_at", description="排序字段：created_at, average_score, like_count"),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取海龟汤列表"""
    offset = (page - 1) * page_size
    
    query = db.query(TurtleSoup).filter(TurtleSoup.status == "published")
    
    if tag:
        query = query.filter(TurtleSoup.tags.contains([tag]))
    
    if sort_by == "average_score":
        query = query.order_by(TurtleSoup.average_score.desc())
    elif sort_by == "like_count":
        query = query.order_by(TurtleSoup.like_count.desc())
    else:
        query = query.order_by(TurtleSoup.created_at.desc())
    
    total = query.count()
    soups = query.offset(offset).limit(page_size).all()
    
    items = []
    for soup in soups:
        items.append({
            "id": soup.id,
            "title": soup.title,
            "puzzle": soup.puzzle,
            "tags": soup.tags,
            "author_id": soup.author_id,
            "author_username": soup.author.username,
            "author_nickname": soup.author.nickname,
            "average_score": soup.average_score,
            "rating_count": soup.rating_count,
            "like_count": soup.like_count,
            "collect_count": soup.collect_count,
            "view_count": soup.view_count,
            "is_revealed": soup.is_revealed,
            "created_at": soup.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
