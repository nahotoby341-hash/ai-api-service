# ===== 构建阶段：安装依赖 =====
FROM python:3.12-slim AS builder

WORKDIR /build
ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt .
# 安装所有依赖到独立目录，便于最终镜像瘦身
RUN pip install --prefix=/install -r requirements.txt

# ===== 运行阶段：只复制依赖与代码 =====
FROM python:3.12-slim

WORKDIR /app

# 时区与基础工具（curl 用于健康检查）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tzdata \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 非 root 用户运行（安全最佳实践）
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 生产默认用 gunicorn 多 worker；开发可覆盖为 uvicorn --reload
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
