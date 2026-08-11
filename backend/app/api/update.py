from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import get_current_admin_user, get_current_root_user
from app.models.database import User
from app.services.ota import get_task, latest_release_service, start_update_task

router = APIRouter()


@router.get("/status")
async def update_status(
    force: bool = Query(False),
    _current_user: User = Depends(get_current_admin_user),
):
    return (await latest_release_service.check(force=force)).as_dict()


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def run_update(_current_user: User = Depends(get_current_root_user)):
    release = await latest_release_service.check()
    if not release.update_available or not release.tag_name:
        raise HTTPException(status_code=409, detail={"code": "NO_UPDATE_AVAILABLE", "message": "没有可用的新版本"})
    try:
        return start_update_task(release.tag_name)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail={"code": "UPDATE_IN_PROGRESS", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail={"code": "UPDATE_NOT_CONFIGURED", "message": str(exc)}) from exc


@router.get("/tasks/{task_id}")
async def update_task(task_id: str, _current_user: User = Depends(get_current_admin_user)):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="升级任务不存在")
    return task
