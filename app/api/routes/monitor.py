"""监控路由：健康检查 + Prometheus 指标。

- /healthz：存活探针，进程在即返回 ok（不依赖外部组件）
- /readyz：就绪探针，数据库 / Redis 连通才返回 ok（供编排系统判断）
- /metrics：Prometheus 指标（生产环境建议通过 Nginx 限制内网访问）
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.services.rate_limit import get_redis

logger = get_logger("monitor")
router = APIRouter(tags=["监控"])


@router.get("/healthz")
async def healthz() -> dict:
    """存活探针。"""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict:
    """就绪探针：检查 PostgreSQL 与 Redis 连通性。"""
    checks: dict[str, str] = {}

    # 数据库
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {str(exc)[:200]}"

    # Redis
    try:
        await get_redis().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {str(exc)[:200]}"

    healthy = all(v == "ok" for v in checks.values())
    if not healthy:
        logger.warning("readyz_unhealthy", checks=checks)
    return {"status": "ok" if healthy else "degraded", "checks": checks}


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus 指标（text 格式）。"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
