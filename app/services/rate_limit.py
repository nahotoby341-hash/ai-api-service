"""Redis 限流器（固定窗口 + 过期自动清理）。

原理：
    key = rate:{bucket}:{user_id}:{当前窗口序号}
    INCR key → 若值 > 上限 → 拒绝
    EXPIRE key (窗口时长 × 2) → 自动过期，Redis 不膨胀

说明：
- 固定窗口实现简单、开销极小（2 次 Redis 命令），对"防滥用"足够；
- 分钟窗口 + 天窗口双桶判断，任一超限即拒绝；
- Redis 不可用时放行（限流是保护措施，不应成为单点故障）。
"""

import time

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger("rate_limit")

_redis: aioredis.Redis | None = None

# 窗口配置：(key 前缀, 时长秒, 上限配置项名)
_WINDOWS = (
    ("min", 60, "LLM_RATE_LIMIT_PER_MINUTE"),
    ("day", 86400, "LLM_RATE_LIMIT_PER_DAY"),
)


def get_redis() -> aioredis.Redis:
    """获取 Redis 连接单例（懒加载）。"""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _redis


async def close_redis() -> None:
    """应用关闭时释放连接（优雅退出用）。"""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


async def check_rate_limit(user_id: int) -> dict[str, int]:
    """检查用户是否触发限流；超限抛出 RateLimitError(429)。

    :return: 剩余额度 {"min": x, "day": y}，供调用方附加到响应头
    """
    r = get_redis()
    remaining: dict[str, int] = {}

    for prefix, window_seconds, config_name in _WINDOWS:
        limit_value = int(getattr(settings, config_name))
        bucket = int(time.time() // window_seconds)
        key = f"rate:{prefix}:{user_id}:{bucket}"
        try:
            count = await r.incr(key)
            await r.expire(key, window_seconds * 2)
        except Exception as exc:
            # Redis 不可用时放行，并跳过剩余窗口判断
            logger.warning("redis_unavailable_rate_limit_bypassed", error=str(exc)[:300])
            break

        remaining[prefix] = max(0, limit_value - count)
        if count > limit_value:
            raise RateLimitError(f"请求过于频繁（{prefix} 窗口超限），请稍后再试")

    return remaining
