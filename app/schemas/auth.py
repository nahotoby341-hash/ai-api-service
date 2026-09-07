"""认证相关请求/响应模型。"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

# 密码规则：8-64 位，至少包含字母和数字
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,64}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)

    @field_validator("password")
    @classmethod
    def _check_password_strength(cls, v: str) -> str:
        if not _PASSWORD_RE.match(v):
            raise ValueError("密码需 8-64 位，且同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
