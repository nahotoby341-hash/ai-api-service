"""AI 能力路由：文本摘要 / 翻译。

完整链路：JWT 校验 → Redis 限流 → 调用大模型 → 写历史记录 → 记监控指标。
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import AppError, RateLimitError
from app.db.session import get_session
from app.models.user import User
from app.schemas.ai import (
    AIResultResponse,
    SummarizeRequest,
    TranslateRequest,
)
from app.schemas.common import ApiResponse
from app.services.history import create_request_log
from app.services.llm import LLMResult, llm_client
from app.services.rate_limit import check_rate_limit
from app.utils.metrics import llm_latency_seconds, llm_requests_total, rate_limit_rejections_total

router = APIRouter(prefix="/ai", tags=["AI 能力"])


def _rate_limit_headers(remaining: dict[str, int]) -> dict[str, str]:
    """把剩余额度拼成响应头。"""
    return {
        "X-RateLimit-Remaining-Minute": str(remaining.get("min", -1)),
        "X-RateLimit-Remaining-Day": str(remaining.get("day", -1)),
    }


async def _run_ai_task(
    response: Response,
    session: AsyncSession,
    user: User,
    task_type: str,
    call_llm,  # 实际执行大模型调用的异步函数
    input_length: int,
) -> ApiResponse[AIResultResponse]:
    """AI 任务公共流程：限流 → 调用 → 写历史 → 返回。"""
    # 1. 限流（超限抛 429）
    try:
        remaining = await check_rate_limit(user.id)
    except RateLimitError:
        rate_limit_rejections_total.labels(user_id=str(user.id)).inc()
        raise
    for k, v in _rate_limit_headers(remaining).items():
        response.headers[k] = v

    # 2. 调用大模型
    result: LLMResult = await call_llm()

    # 3. 监控指标
    llm_requests_total.labels(
        provider=result.provider, task_type=task_type, status="success"
    ).inc()
    llm_latency_seconds.labels(
        provider=result.provider, task_type=task_type
    ).observe((result.latency_ms or 0) / 1000)

    # 4. 写历史（不存原文，只存元数据）
    await create_request_log(
        session,
        user_id=user.id,
        task_type=task_type,
        provider=result.provider,
        model=result.model,
        input_length=input_length,
        output_length=len(result.content),
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        total_tokens=result.total_tokens,
        latency_ms=result.latency_ms,
        status="success",
    )

    return ApiResponse(
        data=AIResultResponse(
            result=result.content,
            provider=result.provider,
            model=result.model,
            usage=result,  # LLMResult 字段名与 LLMUsage 一致
        )
    )


@router.post("/summarize", response_model=ApiResponse[AIResultResponse])
async def summarize(
    payload: SummarizeRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AIResultResponse]:
    """文本摘要。"""
    return await _run_ai_task(
        response, session, user, "summarize",
        call_llm=lambda: llm_client.summarize(
            payload.text, payload.max_length, payload.temperature
        ),
        input_length=len(payload.text),
    )


@router.post("/translate", response_model=ApiResponse[AIResultResponse])
async def translate(
    payload: TranslateRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[AIResultResponse]:
    """文本翻译。"""
    return await _run_ai_task(
        response, session, user, "translate",
        call_llm=lambda: llm_client.translate(
            payload.text, payload.target_lang, payload.temperature
        ),
        input_length=len(payload.text),
    )
