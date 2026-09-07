"""Prometheus 自定义指标。

自动埋点（请求量/耗时/状态码）由 prometheus-fastapi-instrumentator 在 main.py 中
一行代码挂载；这里只注册业务自定义指标。
"""

from prometheus_client import Counter, Histogram

# 大模型调用次数：按 供应商/任务类型/成功失败 维度统计
llm_requests_total = Counter(
    "llm_requests_total",
    "大模型调用总次数",
    ["provider", "task_type", "status"],
)

# 大模型调用耗时（秒）
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "大模型调用耗时（秒）",
    ["provider", "task_type"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
)

# 限流拒绝次数
rate_limit_rejections_total = Counter(
    "rate_limit_rejections_total",
    "限流拒绝总次数",
    ["user_id"],
)
