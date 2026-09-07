"""安全工具：密码哈希 + JWT 签发/校验。

- 密码：bcrypt 加盐单向哈希，绝不明文存储。
- JWT：HS256 签名，payload 只放 user_id 与类型，不放敏感信息。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"


# ===== 密码 =====

def hash_password(plain_password: str) -> str:
    """对明文密码做 bcrypt 哈希。"""
    return bcrypt.hashpw(
        plain_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        return False


# ===== JWT =====

def _create_token(
    user_id: int, token_type: str, expires_delta: timedelta
) -> str:
    """签发一个 JWT。token_type 区分 access / refresh。"""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    """签发访问令牌（短时效）。"""
    return _create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    """签发刷新令牌（长时效）。"""
    return _create_token(
        user_id,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str) -> Optional[int]:
    """校验并解析 JWT，返回 user_id；无效/过期/类型不符返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
