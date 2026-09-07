"""FastAPI 应用入口。

启动方式（开发）：
    uvicorn app.main:app --reload --port 8000
启动方式（生产，容器内）：
    gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import ai, auth, history, monitor
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import RequestContextMiddleware, get_logger, setup_logging
from app.services.rate_limit import close_redis

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理。"""
    setup_logging()
    logger.info("app_starting", env=settings.APP_ENV)
    yield
    await close_redis()
    logger.info("app_stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI 赋能 Web API 服务：JWT 认证 + 大模型摘要/翻译 + 历史记录 + 限流 + 监控",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ===== 中间件 =====
app.add_middleware(RequestContextMiddleware)  # 结构化日志 + request_id

# ===== Prometheus 自动埋点（请求量 / 耗时 / 状态码） =====
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False
)


# ===== 全局异常处理 =====

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """业务异常 → 统一 JSON 响应。"""
    return JSONResponse(
        status_code=exc.http_status,
        content={"code": exc.code, "message": exc.message, "data": exc.data},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """参数校验失败（FastAPI 自动触发）→ 统一格式，提取第一条错误信息。"""
    first = exc.errors()[0] if exc.errors() else {}
    msg = first.get("msg", "参数校验失败")
    # 把 loc 拼成可读路径，如 "body.text"
    loc = ".".join(str(x) for x in first.get("loc", []))
    return JSONResponse(
        status_code=422,
        content={"code": 42201, "message": f"{loc}: {msg}", "data": None},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """兜底 HTTP 异常 → 统一格式。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code * 100, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未预期异常：记 ERROR 日志（带 request_id 可追踪），不向客户端泄露堆栈。"""
    logger.exception("unhandled_error", error=str(exc)[:500])
    return JSONResponse(
        status_code=500,
        content={"code": 50000, "message": "服务器内部错误，请稍后再试", "data": None},
    )


# ===== 路由 =====
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(history.router, prefix=API_PREFIX)
app.include_router(monitor.router)

# ===== 在线体验测试页（静态） =====
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
