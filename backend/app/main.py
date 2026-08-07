from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.core.config import get_settings
from app.api import auth, users, posts, turtle_soups, competitions, social, messages, achievements, admin, search
from app.db import init_db

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
    description="海龟汤解谜社区平台 API",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vue开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"验证错误：{exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "请求参数验证失败",
            "errors": exc.errors()
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"数据库错误：{str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "数据库操作失败",
            "error": str(exc) if settings.DEBUG else "内部服务器错误"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理异常：{str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "内部服务器错误",
            "error": str(exc) if settings.DEBUG else "请稍后重试"
        }
    )


# 路由注册
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(posts.router, prefix="/api/posts", tags=["帖子"])
app.include_router(turtle_soups.router, prefix="/api/turtle-soups", tags=["海龟汤"])
app.include_router(competitions.router, prefix="/api/competitions", tags=["比赛"])
app.include_router(social.router, prefix="/api/social", tags=["社交"])
app.include_router(messages.router, prefix="/api/messages", tags=["消息"])
app.include_router(achievements.router, prefix="/api/achievements", tags=["成就"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])
app.include_router(search.router, prefix="/api/search", tags=["搜索"])


# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}


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
        port=8000,
        reload=settings.DEBUG
    )
