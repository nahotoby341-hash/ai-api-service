"""FastAPI 依赖注入：获取当前登录用户。"""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User

# 从 Authorization: Bearer <token> 中自动提取令牌
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """解析 JWT → 校验 → 返回当前用户；无效则 401。"""
    if credentials is None:
        raise AuthError()

    user_id = decode_token(credentials.credentials, expected_type="access")
    if user_id is None:
        raise AuthError()

    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise AuthError()

    return user
