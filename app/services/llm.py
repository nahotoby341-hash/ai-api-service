"""大模型调用服务（核心亮点：多 Provider，OpenAI 兼容协议）。

设计要点：
- 统一使用 openai SDK，通过环境变量切换 base_url / api_key / model，
  即可在 DeepSeek、通义千问、豆包、OpenAI 等任意兼容服务之间切换，零代码改动。
- 同一实例复用 openai.AsyncClient（连接复用，性能更好）。
"""

import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.exceptions import UpstreamError
from app.core.logging import get_logger

logger = get_logger("llm")


@dataclass
class LLMResult:
    """一次大模型调用的结果。"""

    content: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: int | None = None


class LLMClient:
    """OpenAI 兼容协议客户端封装。"""

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """懒加载客户端（首次调用时创建）。"""
        if self._client is None:
            if not settings.LLM_API_KEY:
                raise UpstreamError(
                    "LLM_API_KEY 未配置，请在 .env 中设置大模型密钥"
                )
            self._client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                timeout=settings.LLM_TIMEOUT_SECONDS,
                max_retries=1,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResult:
        """发送一次 chat/completions 请求。

        :param messages: [{"role": "system", "content": "..."}, ...]
        :return: LLMResult
        :raises UpstreamError: 上游 API 异常（网络/鉴权/限流等）
        """
        start = time.perf_counter()
        try:
            resp = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # 网络、超时、鉴权失败等统一兜底
            logger.warning("llm_call_failed", error=str(exc)[:500])
            raise UpstreamError() from exc

        latency_ms = round((time.perf_counter() - start) * 1000)
        content = (resp.choices[0].message.content or "").strip()
        usage = resp.usage

        logger.info(
            "llm_call_succeeded",
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            latency_ms=latency_ms,
            total_tokens=usage.total_tokens if usage else None,
        )

        return LLMResult(
            content=content,
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
            latency_ms=latency_ms,
        )

    async def summarize(self, text: str, max_length: int, temperature: float) -> LLMResult:
        """文本摘要。"""
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的中文文本摘要助手。",
            },
            {
                "role": "user",
                "content": (
                    f"请对以下文本进行摘要，输出 {max_length} 字以内的摘要。\n"
                    "直接输出摘要内容，不要任何解释或前缀。\n"
                    "【文本】\n" + text
                ),
            },
        ]
        return await self.chat(messages, temperature, settings.LLM_MAX_TOKENS)

    async def translate(self, text: str, target_lang: str, temperature: float) -> LLMResult:
        """文本翻译。"""
        lang_names = {
            "zh": "简体中文", "en": "英文", "ja": "日文", "ko": "韩文",
            "fr": "法文", "de": "德文", "es": "西班牙文", "ru": "俄文",
        }
        messages = [
            {"role": "system", "content": "你是一个专业的翻译引擎。"},
            {
                "role": "user",
                "content": (
                    f"请把下面的文本翻译成{lang_names.get(target_lang, target_lang)}。\n"
                    "直接输出译文，不要任何解释或前缀。\n"
                    "【文本】\n" + text
                ),
            },
        ]
        return await self.chat(messages, temperature, settings.LLM_MAX_TOKENS)


# 全局单例
llm_client = LLMClient()
