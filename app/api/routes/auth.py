"""认证路由：注册 / 登录 / 刷新令牌。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, AuthError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[dict])
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[dict]:
    """注册新用户。"""
    exists = await session.scalar(
        select(User).where(User.email == payload.email)
    )
    if exists:
        raise AppError(code=40901, message="该邮箱已注册", http_status=409)

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return ApiResponse(data={"user_id": user.id, "email": user.email})


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[TokenResponse]:
    """登录，签发 access_token 与 refresh_token。"""
    user = await session.scalar(
        select(User).where(User.email == payload.email)
    )
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AuthError(code=40102, message="邮箱或密码错误")

    if not user.is_active:
        raise AuthError(code=40103, message="账号已被禁用")

    return ApiResponse(
        data=TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[TokenResponse]:
    """用 refresh_token 换新令牌对（旧 refresh 同时作废换新）。"""
    user_id = decode_token(payload.refresh_token, expected_type="refresh")
    if user_id is None:
        raise AuthError(code=40104, message="刷新令牌无效或已过期")

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError(code=40104, message="刷新令牌无效或已过期")

    return ApiResponse(
        data=TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )
