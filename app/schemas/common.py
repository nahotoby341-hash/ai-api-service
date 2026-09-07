"""统一响应包装与分页结构。"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """所有接口的统一响应格式：{"code": 0, "message": "ok", "data": ...}"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    """分页数据结构。"""

    items: list[T]
    total: int
    page: int
    page_size: int
