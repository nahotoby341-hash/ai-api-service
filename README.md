# AI 赋能 Web API 服务

基于 **FastAPI + SQLAlchemy + JWT + PostgreSQL + Redis + Docker** 的轻量级 AI 服务：
用户注册登录后，通过 RESTful API 调用大模型完成**文本摘要**与**翻译**，支持历史记录、限流、结构化日志与 Prometheus 监控。

> 完整设计与小白教程见 [docs/PLAN.md](docs/PLAN.md)

## 快速开始（Docker）

```bash
# 1. 准备环境变量（填入你自己的大模型 API Key）
cp .env.example .env

# 2. 一键启动（app + PostgreSQL + Redis + Nginx + Prometheus + Grafana）
docker compose up --build
```

| 地址 | 说明 |
|---|---|
| http://localhost:8080 | 在线体验测试页 |
| http://localhost:8080/docs | Swagger 接口文档 |
| http://localhost:13000 | Grafana（admin / admin123） |
| http://localhost:19090 | Prometheus |

## 本地开发（不依赖 Docker）

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows；Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # 修改 DATABASE_URL/REDIS_URL 指向本地
uvicorn app.main:app --reload --port 8000
```

## 运行测试

```bash
pytest -v          # 不依赖真实数据库/Redis/大模型，全部 mock
```

## 项目结构

```text
app/
├── main.py            # 入口：路由、中间件、异常处理
├── core/              # 配置 / JWT / 日志 / 异常
├── db/                # 数据库会话
├── models/            # ORM 模型（users / request_logs）
├── schemas/           # 请求响应模型
├── api/routes/        # 认证 / AI / 历史 / 监控
├── services/          # LLM 多Provider / Redis限流 / 历史
└── static/            # 在线体验测试页
```

## 核心特性

- **多 Provider 大模型**：OpenAI 兼容协议，改 4 个环境变量即切换供应商（DeepSeek / 通义 / 豆包 / OpenAI）
- **JWT 认证**：15 分钟 access_token + 7 天 refresh_token
- **Redis 限流**：分钟 + 天双窗口，超限返回 429
- **结构化日志**：JSON 格式 + request_id 链路追踪
- **监控**：`/metrics` 自动埋点 + 自定义大模型指标，可接 Grafana
- **统一错误响应**：`{"code", "message", "data"}` 全接口一致
