"""应用配置管理。

所有配置都从环境变量 / .env 文件读取，由 pydantic-settings 统一校验。
新增配置项：在这里加一个带默认值的字段即可，全项目通过 settings.xxx 使用。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置。字段名对应 .env 中的变量名（不区分大小写）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用基础 =====
    APP_NAME: str = "ai-api-service"
    APP_ENV: str = "dev"  # dev / test / prod
    DEBUG: bool = True
    SECRET_KEY: str = "please-change-me-to-a-random-64-char-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== 数据库 =====
    DATABASE_URL: str = (
        "postgresql+asyncpg://ai_user:ai_pass_123456@db:5432/ai_api"
    )

    # ===== Redis =====
    REDIS_URL: str = "redis://redis:6379/0"

    # ===== 大模型（OpenAI 兼容多 Provider） =====
    LLM_PROVIDER: str = "deepseek"
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_MAX_TOKENS: int = 4096

    # ===== 限流 =====
    LLM_RATE_LIMIT_PER_MINUTE: int = 5
    LLM_RATE_LIMIT_PER_DAY: int = 200

    # ===== 输入限制 =====
    MAX_INPUT_LENGTH: int = 20000

    # ===== 服务端口 =====
    APP_PORT: int = 8000

    # ===== 派生属性（非 .env 配置，计算得出） =====
    @property
    def is_prod(self) -> bool:
        """是否生产环境。"""
        return self.APP_ENV == "prod"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例（带缓存，整个进程只解析一次 .env）。"""
    return Settings()


settings = get_settings()
