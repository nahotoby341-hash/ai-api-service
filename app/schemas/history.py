"""历史记录相关响应模型。"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class HistoryItem(BaseModel):
    id: int
    task_type: Literal["summarize", "translate"]
    input_length: int
    output_length: Optional[int] = None
    provider: str
    model: Optional[str] = None
    status: str
    latency_ms: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}  # 允许直接从 ORM 对象构造


class HistoryQueryParams(BaseModel):
    page: int = 1
    page_size: int = 10
    task_type: Optional[Literal["summarize", "translate"]] = None
