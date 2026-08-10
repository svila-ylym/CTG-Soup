"""Authenticated uploads for public images."""
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.api.auth import get_current_active_user
from app.models.database import UploadedAsset, User, get_db
from app.schemas import UploadedAssetResponse, UploadImageResponse
from app.services.public_storage import (
    PublicStorage,
    PublicStorageError,
    get_public_storage,
)
from app.services.upload_rules import validate_upload

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/images", response_model=list[UploadedAssetResponse])
def list_images(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return db.exec(
        select(UploadedAsset)
        .where(
            UploadedAsset.owner_uid == current_user.uid,
            UploadedAsset.kind == "image",
        )
        .order_by(UploadedAsset.created_at.desc(), UploadedAsset.id.desc())
    ).all()


@router.post(
    "/images",
    response_model=UploadImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    storage: PublicStorage = Depends(get_public_storage),
):
    content = await file.read()
    try:
        suffix = validate_upload(file.content_type or "", file.filename or "", len(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    key = f"images/{current_user.uid}/{uuid4().hex}{suffix}"
    try:
        await run_in_threadpool(
            storage.put,
            key,
            content,
            file.content_type or "application/octet-stream",
        )
    except PublicStorageError as exc:
        logger.error(
            "Public image write failed provider=%s key=%s type=%s",
            storage.name,
            key,
            type(exc.__cause__ or exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="公开图片存储暂时不可用",
        ) from exc
    url = storage.public_url(key)

    asset = UploadedAsset(
        owner_uid=current_user.uid,
        kind="image",
        storage_key=key,
        public_url=url,
        mime_type=file.content_type or "application/octet-stream",
        size=len(content),
    )
    try:
        db.add(asset)
        db.flush()
        db.refresh(asset)
        response = {
            "asset_id": asset.id,
            "url": asset.public_url,
            "storage": storage.name,
            "key": asset.storage_key,
            "mime_type": asset.mime_type,
            "size": asset.size,
        }
        db.commit()
    except SQLAlchemyError:
        try:
            db.rollback()
        except SQLAlchemyError as rollback_exc:
            logger.error(
                "Public image transaction rollback failed key=%s type=%s",
                key,
                type(rollback_exc).__name__,
            )
        try:
            await run_in_threadpool(storage.delete, key)
        except PublicStorageError as cleanup_exc:
            logger.error(
                "Public image cleanup failed provider=%s key=%s type=%s",
                storage.name,
                key,
                type(cleanup_exc.__cause__ or cleanup_exc).__name__,
            )
        raise
    return response
