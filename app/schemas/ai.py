"""AI 能力（摘要/翻译）请求与响应模型。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=settings.MAX_INPUT_LENGTH)
    max_length: int = Field(default=200, ge=20, le=2000)  # 摘要目标字数
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=settings.MAX_INPUT_LENGTH)
    target_lang: str = Field(default="zh", min_length=1, max_length=20)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)

    @field_validator("target_lang")
    @classmethod
    def _normalize_lang(cls, v: str) -> str:
        """只允许常见语言代码，防注入与乱填。"""
        allowed = {"zh", "en", "ja", "ko", "fr", "de", "es", "ru"}
        if v not in allowed:
            raise ValueError(f"暂不支持的语言：{v}，支持：{', '.join(sorted(allowed))}")
        return v


class LLMUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class AIResultResponse(BaseModel):
    result: str
    provider: str
    model: str
    usage: LLMUsage


TaskType = Literal["summarize", "translate"]
