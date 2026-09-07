"""统一异常体系。

业务层 / 服务层抛出 AppError，由全局异常处理器转换为统一 JSON 响应：
    {"code": <业务错误码>, "message": <用户可读信息>, "data": null}
HTTP 状态码与业务错误码分离，前端按 code 处理业务逻辑。
"""

from typing import Any, Optional


class AppError(Exception):
    """业务异常基类。

    :param code: 业务错误码（如 40101），0 表示成功
    :param message: 用户可读的错误信息
    :param http_status: 对应的 HTTP 状态码
    """

    def __init__(
        self,
        code: int,
        message: str,
        http_status: int = 400,
        data: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.data = data


# ===== 常用业务异常快捷类 =====

class AuthError(AppError):
    """认证相关：未登录、令牌无效、无权限。"""

    def __init__(self, code: int = 40101, message: str = "未登录或登录已过期") -> None:
        super().__init__(code=code, message=message, http_status=401)


class RateLimitError(AppError):
    """限流：请求过于频繁。"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试") -> None:
        super().__init__(code=42901, message=message, http_status=429)


class NotFoundError(AppError):
    """资源不存在。"""

    def __init__(self, code: int = 40401, message: str = "资源不存在") -> None:
        super().__init__(code=code, message=message, http_status=404)


class UpstreamError(AppError):
    """上游大模型 API 异常。"""

    def __init__(
        self, message: str = "大模型服务暂不可用，请稍后再试", code: int = 50201
    ) -> None:
        super().__init__(code=code, message=message, http_status=502)
