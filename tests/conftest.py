"""测试夹具。

设计目标：
- 测试**不依赖真实 PostgreSQL / Redis / 大模型**，任何机器上 `pytest -v` 都能跑。
- 数据库：SQLite 内存库（aiosqlite），每用例重建表，互不干扰。
- Redis 限流：mock 掉 check_rate_limit，直接返回剩余额度。
- 大模型：mock 掉 llm_client 的方法，返回固定假结果。
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_session
from app.main import app

# 导入模型，确保注册到 Base.metadata
from app.models import request_log, user  # noqa: F401
from app.schemas.ai import LLMUsage
from app.services.llm import LLMResult

# 每个测试函数使用全新的内存库（建表 → 测试 → 删表）
_engine = create_async_engine("sqlite+aiosqlite:///:memory:")
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    """独立的测试数据库会话。"""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _SessionLocal() as session:
        yield session
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session, monkeypatch):
    """测试用 HTTP 客户端：注入内存数据库、mock 限流与大模型。"""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session

    # 1. mock Redis 限流：直接返回额度，不真正连 Redis
    monkeypatch.setattr(
        "app.api.routes.ai.check_rate_limit",
        lambda user_id: {"min": 5, "day": 100},
    )

    # 2. mock 大模型调用：固定假结果
    fake_result = LLMResult(
        content="【测试】这是一段模拟的 AI 返回结果。",
        provider="mock",
        model="mock-model",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        latency_ms=5,
    )

    async def fake_summarize(text, max_length, temperature):
        return fake_result

    async def fake_translate(text, target_lang, temperature):
        return fake_result

    monkeypatch.setattr(
        "app.services.llm.llm_client.summarize", fake_summarize
    )
    monkeypatch.setattr(
        "app.services.llm.llm_client.translate", fake_translate
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


async def register_and_login(client: AsyncClient) -> str:
    """工具函数：注册 + 登录，返回 access_token。"""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "Abc123456"},
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "Abc123456"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["access_token"]
