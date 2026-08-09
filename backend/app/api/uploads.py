"""Authenticated image uploads stored on the local disk."""
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.auth import get_current_active_user
from app.core.config import get_settings
from app.models.database import UploadedAsset, User, get_db
from app.schemas import UploadedAssetResponse, UploadImageResponse
from app.services.upload_rules import validate_upload

router = APIRouter()
settings = get_settings()


def _local_directory() -> Path:
    directory = Path(settings.LOCAL_STORAGE_DIR)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parents[2] / directory
    directory.mkdir(parents=True, exist_ok=True)
    return directory


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
):
    content = await file.read()
    try:
        suffix = validate_upload(file.content_type or "", file.filename or "", len(content))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    key = f"images/{current_user.uid}/{uuid4().hex}{suffix}"
    destination = _local_directory() / key
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.write_bytes(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="头像保存失败") from exc
    url = f"/storage/{key}"

    asset = UploadedAsset(
        owner_uid=current_user.uid,
        kind="image",
        storage_key=key,
        public_url=url,
        mime_type=file.content_type or "application/octet-stream",
        size=len(content),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {
        "asset_id": asset.id,
        "url": asset.public_url,
        "storage": "local",
        "key": asset.storage_key,
        "mime_type": asset.mime_type,
        "size": asset.size,
    }
