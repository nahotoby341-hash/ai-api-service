"""数据库会话管理（SQLAlchemy 异步模式）。

- engine：全局唯一数据库引擎（连接池）。
- get_session：FastAPI 依赖，每个请求一个会话，请求结束自动关闭。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：提供一个数据库会话，请求结束自动关闭。"""
    async with AsyncSessionLocal() as session:
        yield session
