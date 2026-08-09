from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import get_settings
from app.api import auth, users, posts, turtle_soups, competitions, social, messages, notifications, achievements, admin, search, uploads, tags, announcements, message_socket, system_messages
from pathlib import Path
from app.db import init_db
from app.services.dependency_health import optional_dependency_status

settings = get_settings()

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="汤吧社区 API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:10000", "http://127.0.0.1:10000", "http://0.0.0.0:10000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    safe_errors = [
        {
            "type": item.get("type", "validation_error"),
            "loc": item.get("loc", ()),
            "msg": item.get("msg", "请求参数验证失败"),
        }
        for item in exc.errors()
    ]
    logger.warning(
        "Request validation failed path=%s fields=%s",
        request.url.path,
        [item["loc"] for item in safe_errors],
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": {"code": "VALIDATION_ERROR", "message": "请求参数验证失败"},
            "errors": safe_errors,
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database operation failed path=%s type=%s",
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {"code": "DATABASE_ERROR", "message": "数据库操作失败"},
            "error": type(exc).__name__ if settings.DEBUG else "内部服务器错误"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled request error path=%s type=%s",
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": {"code": "INTERNAL_ERROR", "message": "内部服务器错误"},
            "error": type(exc).__name__ if settings.DEBUG else "请稍后重试"
        }
    )


# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(posts.router, prefix="/api/posts", tags=["帖子"])
app.include_router(turtle_soups.router, prefix="/api/turtle-soups", tags=["海龟汤"])
app.include_router(tags.router, prefix="/api/tags", tags=["标签"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["公告"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["比赛"])
app.include_router(social.router, prefix="/api/social", tags=["社交"])
app.include_router(messages.router, prefix="/api/messages", tags=["消息"])
app.include_router(message_socket.router, tags=["消息实时连接"])
app.include_router(system_messages.router, prefix="/api/system-messages", tags=["系统消息"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["通知"])
app.include_router(achievements.router, prefix="/api/achievements", tags=["成就"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["上传"])
storage_dir = Path(settings.LOCAL_STORAGE_DIR)
if not storage_dir.is_absolute():
    storage_dir = Path(__file__).resolve().parents[1] / storage_dir
storage_dir = storage_dir.resolve()
private_storage_dir = Path(settings.PRIVATE_STORAGE_DIR)
if not private_storage_dir.is_absolute():
    private_storage_dir = Path(__file__).resolve().parents[1] / private_storage_dir
private_storage_dir = private_storage_dir.resolve()
if (
    storage_dir == private_storage_dir
    or storage_dir in private_storage_dir.parents
    or private_storage_dir in storage_dir.parents
):
    raise RuntimeError("PRIVATE_STORAGE_DIR must not overlap the public storage directory")
storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")


# 健康检查
@app.get("/health")
async def health_check():
    dependencies = {"database": "configured", **optional_dependency_status()}
    status_value = "ok" if all(
        value in {"available", "configured", "standby"}
        for value in dependencies.values()
    ) else "degraded"
    return {"status": status_value, "version": settings.APP_VERSION, "dependencies": dependencies}


# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("应用启动中...")
    # 初始化数据库表
    init_db()
    logger.info("数据库初始化完成")
    # 这里可以添加其他启动逻辑，如Redis连接、Elasticsearch索引等
    logger.info("应用启动完成")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("应用关闭中...")
    # 这里可以添加清理逻辑
    logger.info("应用已关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=10001,
        reload=settings.DEBUG
    )
