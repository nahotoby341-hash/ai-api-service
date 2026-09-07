"""结构化日志。

- 输出 JSON 格式日志（structlog），便于日志系统采集。
- RequestContextMiddleware 为每个请求生成 request_id，并绑定到日志上下文，
  一次请求的所有日志行都带同一 request_id，可串联排查。
- 敏感信息（密码/令牌/API Key/请求原文）一律不写入日志。
"""

import logging
import sys
import time
import uuid

import structlog

from app.core.config import settings

_SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization"}


def setup_logging() -> None:
    """初始化日志配置（应用启动时调用一次）。"""
    # 基础 logging 配置：structlog 把最终渲染交给标准 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # 注入 request_id 等上下文
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),  # JSON 输出
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    """获取一个结构化 logger。"""
    return structlog.get_logger(name)


class RequestContextMiddleware:
    """纯 ASGI 中间件：为每个请求生成 request_id 并记录请求/响应摘要日志。

    采用纯 ASGI 写法（直接操作 scope/send/receive），保证与端点运行在
    同一个协程任务中，structlog contextvars（request_id 等）可正常传播到业务日志。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:16]
        # 绑定到 structlog 上下文，本次请求内的所有日志自动携带
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope.get("method"),
            path=scope.get("path"),
        )
        start = time.perf_counter()
        logger = get_logger("http")

        # 过滤敏感请求头，仅记录安全的信息
        raw_headers = [
            (k.decode("latin-1"), v.decode("latin-1"))
            for k, v in scope.get("headers", [])
        ]
        safe_headers = {
            k: v for k, v in raw_headers if k.lower() not in _SENSITIVE_HEADERS
        }
        logger.info("request_started", headers=safe_headers)

        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "request_failed",
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info("request_finished", status_code=status_code, duration_ms=duration_ms)
            structlog.contextvars.clear_contextvars()
