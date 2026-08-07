from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db, User, PrivateMessage, Blacklist
from app.schemas import PrivateMessageCreate, PrivateMessageResponse, PageResponse
from app.api.auth import get_current_active_user

router = APIRouter()


@router.post("", response_model=PrivateMessageResponse)
async def send_message(
    message_data: PrivateMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """发送私信"""
    if message_data.receiver_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能给自己发消息")
    
    receiver = db.query(User).filter(User.id == message_data.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    
    # 检查是否被拉黑
    is_blocked = db.query(Blacklist).filter(
        (Blacklist.blocker_id == message_data.receiver_id) & (Blacklist.blocked_id == current_user.id)
    ).first()
    
    if is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您已被对方拉黑")
    
    db_message = PrivateMessage(
        sender_id=current_user.id,
        receiver_id=message_data.receiver_id,
        content=message_data.content,
    )
    
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    
    return {
        "id": db_message.id,
        "sender_id": db_message.sender_id,
        "receiver_id": db_message.receiver_id,
        "content": db_message.content,
        "is_read": db_message.is_read,
        "created_at": db_message.created_at,
        "sender_username": current_user.username,
    }


@router.get("/inbox", response_model=PageResponse)
async def get_inbox(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取收件箱"""
    offset = (page - 1) * page_size
    
    query = db.query(PrivateMessage).filter(
        PrivateMessage.receiver_id == current_user.id,
        PrivateMessage.receiver_deleted == False
    ).order_by(PrivateMessage.created_at.desc())
    
    total = query.count()
    messages = query.offset(offset).limit(page_size).all()
    
    items = []
    for msg in messages:
        items.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "sender_username": msg.sender.username,
            "content": msg.content,
            "is_read": msg.is_read,
            "created_at": msg.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/sent", response_model=PageResponse)
async def get_sent(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取已发送消息"""
    offset = (page - 1) * page_size
    
    query = db.query(PrivateMessage).filter(
        PrivateMessage.sender_id == current_user.id,
        PrivateMessage.sender_deleted == False
    ).order_by(PrivateMessage.created_at.desc())
    
    total = query.count()
    messages = query.offset(offset).limit(page_size).all()
    
    items = []
    for msg in messages:
        items.append({
            "id": msg.id,
            "receiver_id": msg.receiver_id,
            "receiver_username": msg.receiver.username,
            "content": msg.content,
            "is_read": msg.is_read,
            "created_at": msg.created_at,
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.put("/{message_id}/read")
async def mark_as_read(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记消息为已读"""
    message = db.query(PrivateMessage).filter(
        PrivateMessage.id == message_id,
        PrivateMessage.receiver_id == current_user.id
    ).first()
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    
    message.is_read = True
    db.commit()
    
    return {"message": "已标记为已读"}


@router.delete("/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除消息（仅自己可见）"""
    message = db.query(PrivateMessage).filter(PrivateMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    
    if message.sender_id == current_user.id:
        message.sender_deleted = True
    elif message.receiver_id == current_user.id:
        message.receiver_deleted = True
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    
    db.commit()
    
    return {"message": "删除成功"}
