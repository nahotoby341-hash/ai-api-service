"""历史记录路由：分页查询自己的调用历史。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.common import ApiResponse, PageData
from app.schemas.history import HistoryItem
from app.services.history import list_request_logs

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("", response_model=ApiResponse[PageData[HistoryItem]])
async def get_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    task_type: str | None = Query(default=None, pattern="^(summarize|translate)$"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[PageData[HistoryItem]]:
    """分页查询当前用户的调用历史（时间倒序）。"""
    items, total = await list_request_logs(
        session,
        user_id=user.id,
        page=page,
        page_size=page_size,
        task_type=task_type,
    )
    return ApiResponse(
        data=PageData(items=items, total=total, page=page, page_size=page_size)
    )
