"""
数据库连接与初始化
从环境变量读取配置，支持 PostgreSQL
"""
import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/turtle_soup")

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False").lower() == "true",  # 开发环境开启 SQL 日志
    pool_pre_ping=True,  # 自动重连
    pool_size=10,
    max_overflow=20
)

def init_db():
    """初始化数据库表"""
    SQLModel.metadata.create_all(bind=engine)
    print("✓ 数据库表初始化完成")

def get_session() -> Generator[Session, None, None]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
