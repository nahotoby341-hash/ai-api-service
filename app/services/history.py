"""历史记录服务：写入与查询大模型调用日志。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.request_log import RequestLog
from app.schemas.history import HistoryItem


async def create_request_log(
    session: AsyncSession,
    *,
    user_id: int,
    task_type: str,
    provider: str,
    model: str | None,
    input_length: int,
    output_length: int | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    latency_ms: int | None,
    status: str,
    error_message: str | None = None,
) -> RequestLog:
    """写入一条调用记录。"""
    log = RequestLog(
        user_id=user_id,
        task_type=task_type,
        provider=provider,
        model=model,
        input_length=input_length,
        output_length=output_length,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status=status,
        error_message=error_message,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def list_request_logs(
    session: AsyncSession,
    *,
    user_id: int,
    page: int,
    page_size: int,
    task_type: str | None = None,
) -> tuple[list[HistoryItem], int]:
    """分页查询某用户的历史记录（按时间倒序）。

    :return: (记录列表, 总条数)
    """
    filters = [RequestLog.user_id == user_id]
    if task_type:
        filters.append(RequestLog.task_type == task_type)

    total = (
        await session.scalar(
            select(func.count()).select_from(RequestLog).where(*filters)
        )
    ) or 0

    stmt = (
        select(RequestLog)
        .where(*filters)
        .order_by(RequestLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.scalars(stmt)).all()
    items = [HistoryItem.model_validate(row) for row in rows]
    return items, total
