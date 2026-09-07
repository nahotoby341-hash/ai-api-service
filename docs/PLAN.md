# AI 赋能 Web API 服务 —— 项目计划文档

> 版本：v1.0 ｜ 日期：2026-09-07 ｜ 状态：技术方案已确认，进入框架搭建阶段
>
> 本文档面向所有读者编写，即使你不懂后端开发，按顺序读完也能明白这个项目**是什么、怎么运转、如何跑起来**。

---

## 目录

1. [项目是什么](#1-项目是什么)
2. [功能清单](#2-功能清单)
3. [技术栈总览](#3-技术栈总览)
4. [系统架构](#4-系统架构)
5. [项目目录结构](#5-项目目录结构)
6. [API 接口设计](#6-api-接口设计)
7. [数据库设计](#7-数据库设计)
8. [核心机制详解](#8-核心机制详解)
9. [部署架构](#9-部署架构)
10. [本地开发：小白一步步跑起来](#10-本地开发小白一步步跑起来)
11. [测试方案](#11-测试方案)
12. [分阶段实施计划](#12-分阶段实施计划)
13. [安全清单](#13-安全清单)
14. [后续可扩展方向](#14-后续可扩展方向)

---

## 1. 项目是什么

一句话：**我们构建一个"AI 能力"的 API 服务**——用户注册登录后，调用一个接口就能让大模型帮他做**文本摘要**或**翻译**，系统把每一次调用记录在数据库里，并通过监控面板实时观察服务健康状况。

类比理解：

- **FastAPI** 就像餐厅的前台：负责"接客"（接收 HTTP 请求）、"派单"（路由到对应处理逻辑）、"回话"（返回 JSON 响应）。
- **大模型 API** 是后厨：真正干活（摘要、翻译）。
- **PostgreSQL** 是账本：记录谁注册了、谁调用了什么。
- **Redis** 是门卫：限制每个用户每分钟/每天最多调用几次，防止滥用。
- **JWT** 是进门凭证：用户登录后拿到一张"令牌"，之后每次请求出示令牌即可，不用反复输密码。
- **Docker** 是打包箱：把服务、数据库、Redis、Nginx 等全部装进标准容器，在任何服务器上一条命令启动。

---

## 2. 功能清单

| 模块 | 功能 | 说明 |
|---|---|---|
| 用户认证 | 注册 | 邮箱 + 密码注册，密码加密存储（bcrypt） |
| 用户认证 | 登录 | 校验密码，签发 JWT 访问令牌 |
| 用户认证 | 令牌刷新 | 过期后凭刷新令牌换新令牌 |
| AI 能力 | 文本摘要 | 调用大模型压缩长文本，支持自定义长度 |
| AI 能力 | 文本翻译 | 调用大模型翻译，支持指定目标语言 |
| 历史记录 | 查询历史 | 分页查看自己的调用记录（摘要/翻译各多少次等） |
| 限流 | Redis 限流 | 每分钟 N 次、每天 M 次，超限返回 429 |
| 监控 | 健康检查 | `/healthz` 存活探针 + `/readyz` 就绪探针 |
| 监控 | Prometheus 指标 | `/metrics` 暴露 HTTP 请求量、耗时、错误率等 |
| 日志 | 结构化日志 | JSON 格式，携带 request_id 可串联一次完整请求链路 |
| 测试页 | 在线体验 | 浏览器打开一个简单页面，输入文本即可体验摘要/翻译 |
| 部署 | 容器化 | Docker + docker-compose 一键启动全套服务 |

---

## 3. 技术栈总览

| 技术 | 在本项目中的角色 | 为什么选它 |
|---|---|---|
| Python 3.12 | 开发语言 | 生态最成熟，AI 领域事实标准 |
| FastAPI | Web 框架 | 高性能（基于 Starlette），自动生成 OpenAPI 文档（/docs），类型提示驱动校验，写代码少、不易错 |
| Uvicorn | ASGI 服务器 | FastAPI 官方推荐的运行服务器，支持异步高并发 |
| SQLAlchemy 2.0（async） | ORM 对象关系映射 | 用 Python 类操作数据库，不用手写 SQL；异步版不阻塞事件循环 |
| asyncpg | PostgreSQL 异步驱动 | 配合 SQLAlchemy 异步模式 |
| Alembic | 数据库迁移工具 | 数据库表结构变更版本化管理，可回滚 |
| PostgreSQL 16 | 主数据库 | 功能强、开源、生产级 |
| Redis 7 | 限流计数 / 缓存 | 内存数据库，INCR + 过期时间实现限流，天然支持 TTL |
| PyJWT | JWT 令牌签发/校验 | 轻量、维护活跃、标准实现 |
| bcrypt | 密码哈希 | 加盐哈希，抗彩虹表攻击，业界标准 |
| pydantic-settings | 配置管理 | 从环境变量/.env 读取配置，类型安全，一处定义处处可用 |
| openai SDK | 调用大模型 | 官方 SDK，支持自定义 `base_url`，天然适配所有 OpenAI 兼容服务 |
| structlog | 结构化日志 | 输出 JSON 格式日志，便于 ELK/Loki 等日志系统采集 |
| prometheus-client | 指标采集 | 标准 Prometheus 协议，暴露 /metrics |
| prometheus-fastapi-instrumentator | 自动埋点 | 一行代码自动统计每个接口的请求量、耗时、状态码分布 |
| pytest | 测试框架 | Python 事实标准，配合 httpx 做接口测试 |
| Docker / docker-compose | 容器化部署 | 开发与生产环境一致，一键起全套 |
| Nginx | 反向代理 | 对外统一入口：HTTPS 终结、静态文件、请求转发 |
| Prometheus + Grafana | 监控展示 | Prometheus 采集指标，Grafana 画仪表盘 |

---

## 4. 系统架构

```text
                    ┌─────────────────────────────────────────────┐
                    │                 客户端（浏览器 / curl）        │
                    └──────────────────────┬──────────────────────┘
                                           │ HTTPS
                    ┌──────────────────────▼──────────────────────┐
                    │                Nginx（反向代理）              │
                    │       TLS 终止 / 静态页面 / 请求转发          │
                    └──────────────────────┬──────────────────────┘
                                           │ HTTP
                    ┌──────────────────────▼──────────────────────┐
                    │              FastAPI 应用（app/）            │
                    │                                              │
                    │  认证路由 ──► 依赖注入(校验JWT) ──► AI 路由    │
                    │       │                       │             │
                    │       ▼                       ▼             │
                    │  JWT 签发/校验          LLM 服务(多Provider)  │
                    │       │                       │             │
                    │       ▼                       ▼             │
                    │  用户/历史 模型 ←──── 历史记录服务             │
                    └──────┬───────────────┬───────────────┬──────┘
                           │               │               │
                    ┌──────▼─────┐  ┌──────▼──────┐  ┌─────▼──────────┐
                    │ PostgreSQL │  │   Redis     │  │ 外部大模型 API   │
                    │  用户/历史  │  │ 限流计数    │  │ DeepSeek / 通义  │
                    │  请求记录   │  │             │  │ OpenAI 兼容     │
                    └────────────┘  └─────────────┘  └────────────────┘
```

**请求一次"翻译"的完整旅程（以理解架构）：**

1. 用户登录拿到 JWT 令牌。
2. 用户带令牌调用 `POST /api/v1/ai/translate`。
3. Nginx 把请求转发给 FastAPI。
4. FastAPI 先校验 JWT（你是谁）→ 再查 Redis 限流（你还能不能用）→ 通过后调用 LLM 服务。
5. LLM 服务按配置的 provider（如 DeepSeek）拼好 prompt，发 HTTP 请求给大模型。
6. 拿到翻译结果后，把"谁、什么时间、输入多长、花了多少 token、成功与否"写入 PostgreSQL。
7. 返回 JSON 给用户；同时 Prometheus 自动记录这次请求的耗时和状态码。

---

## 5. 项目目录结构

```text
ai-api-service/
├── docs/
│   └── PLAN.md                  # 本文档
├── app/                         # 应用主代码（全部业务逻辑）
│   ├── main.py                  # 入口：创建 FastAPI 实例、挂载路由/中间件/静态页
│   ├── core/                    # 核心基础设施
│   │   ├── config.py            #   配置管理（.env → pydantic-settings）
│   │   ├── security.py          #   JWT 签发/校验、密码哈希
│   │   ├── logging.py           #   结构化 JSON 日志 + request_id 中间件
│   │   └── exceptions.py        #   统一异常与统一错误响应格式
│   ├── db/
│   │   ├── base.py              #   ORM 基类（所有模型继承它）
│   │   └── session.py           #   数据库连接引擎与会话管理
│   ├── models/                  # 数据库表对应的 ORM 模型
│   │   ├── user.py              #   users 表
│   │   └── request_log.py       #   request_logs 表
│   ├── schemas/                 # 请求/响应数据模型（Pydantic，自动校验）
│   │   ├── auth.py              #   注册/登录/令牌响应
│   │   ├── ai.py                #   摘要/翻译请求与响应
│   │   └── history.py           #   历史记录查询
│   ├── api/
│   │   ├── deps.py              # 依赖注入：获取当前用户、校验限流
│   │   └── routes/
│   │       ├── auth.py          # 注册/登录/刷新令牌
│   │       ├── ai.py            # 摘要/翻译接口
│   │       ├── history.py       # 历史记录接口
│   │       └── monitor.py       # 健康检查 / metrics
│   ├── services/                # 业务逻辑层（路由只做转发，逻辑在这）
│   │   ├── llm.py               #   多 Provider 大模型调用（核心）
│   │   ├── rate_limit.py        #   Redis 限流器
│   │   └── history.py           #   历史记录读写
│   ├── utils/
│   │   └── metrics.py           # Prometheus 指标注册
│   └── static/
│       └── index.html           # 在线体验测试页（纯静态）
├── alembic/                     # 数据库迁移脚本
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                # 每次表结构变更生成一个版本文件
├── alembic.ini
├── tests/                       # 自动化测试
│   ├── conftest.py              #   测试夹具（测试数据库、测试客户端）
│   ├── test_auth.py             #   注册/登录/令牌测试
│   ├── test_ai.py               #   摘要/翻译接口测试
│   └── test_history.py          #   历史记录测试
├── nginx/
│   └── nginx.conf               # 反向代理配置
├── prometheus/
│   └── prometheus.yml           # 指标采集配置
├── Dockerfile                   # 应用镜像构建
├── docker-compose.yml           # 一键编排：app+pg+redis+nginx+prometheus+grafana
├── requirements.txt             # Python 依赖清单
├── .env.example                 # 环境变量模板（复制为 .env 后填写）
├── .gitignore
└── README.md
```

**分层原则（重要设计决策）**：

- `api/routes`（表现层）：只做参数接收、调用服务、返回结果，**不含业务逻辑**。
- `services`（业务层）：核心逻辑（调大模型、限流、写历史）。
- `models`（数据层）：纯数据映射。
- 这样分层的好处：改数据库不影响接口，换大模型供应商不动路由，测试时可以单独测每一层。

---

## 6. API 接口设计

统一前缀：`/api/v1`。所有响应遵循统一格式：

```json
{
  "code": 0,            // 0=成功，非0=业务错误码
  "message": "ok",
  "data": { ... }       // 具体业务数据
}
```

### 6.1 认证接口

| 方法 | 路径 | 说明 | 是否需要登录 |
|---|---|---|---|
| POST | `/api/v1/auth/register` | 注册（邮箱+密码） | 否 |
| POST | `/api/v1/auth/login` | 登录，返回 access_token + refresh_token | 否 |
| POST | `/api/v1/auth/refresh` | 用 refresh_token 换新 access_token | 否 |

**注册请求示例：**

```json
{
  "email": "demo@example.com",
  "password": "Abc123456"
}
```

**登录响应示例：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### 6.2 AI 功能接口

| 方法 | 路径 | 说明 | 是否需要登录 |
|---|---|---|---|
| POST | `/api/v1/ai/summarize` | 文本摘要 | 是 |
| POST | `/api/v1/ai/translate` | 文本翻译 | 是 |

**摘要请求：**

```json
{
  "text": "（长文本……）",
  "max_length": 200,
  "temperature": 0.3
}
```

**翻译请求：**

```json
{
  "text": "Hello world",
  "target_lang": "zh",
  "temperature": 0.2
}
```

**响应：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "result": "翻译或摘要结果文本",
    "provider": "deepseek",
    "model": "deepseek-chat",
    "usage": { "prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165 }
  }
}
```

### 6.3 历史记录接口

| 方法 | 路径 | 说明 | 是否需要登录 |
|---|---|---|---|
| GET | `/api/v1/history` | 分页查询自己的调用历史 | 是 |

支持查询参数：`page`（页码，默认1）、`page_size`（每页条数，默认10，最大100）、`task_type`（可选：summarize / translate）。

**响应：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "task_type": "translate",
        "input_length": 11,
        "output_length": 22,
        "provider": "deepseek",
        "status": "success",
        "created_at": "2026-09-07T10:00:00+08:00"
      }
    ],
    "total": 42,
    "page": 1,
    "page_size": 10
  }
}
```

> 隐私设计：历史记录**不存原文**，只存输入/输出长度、使用的模型、状态、耗时，避免敏感文本落库。

### 6.4 监控接口

| 方法 | 路径 | 说明 | 是否需要登录 |
|---|---|---|---|
| GET | `/healthz` | 存活探针（服务进程在跑即返回 ok） | 否 |
| GET | `/readyz` | 就绪探针（数据库、Redis 连通才返回 ok） | 否 |
| GET | `/metrics` | Prometheus 指标 | 否（生产建议内网或 Nginx 层限制） |
| GET | `/` | 在线体验测试页 | 否 |
| GET | `/docs` | Swagger UI（FastAPI 自动生成，可在线调试） | 否 |

### 6.5 统一错误响应示例

```json
{
  "code": 40101,
  "message": "登录已过期，请重新登录",
  "data": null
}
```

| HTTP 状态码 | 业务含义 |
|---|---|
| 400 | 参数校验失败 |
| 401 | 未登录 / 令牌无效或过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 邮箱已注册 |
| 422 | 请求体格式错误（FastAPI 自动） |
| 429 | 触发限流 |
| 500 | 服务器内部错误 |
| 502 | 上游大模型 API 异常 |

---

## 7. 数据库设计

### 7.1 users 用户表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGINT | 主键，自增 | 用户 ID |
| email | VARCHAR(255) | 唯一，非空 | 登录邮箱 |
| hashed_password | VARCHAR(255) | 非空 | bcrypt 哈希后的密码 |
| is_active | BOOLEAN | 默认 true | 是否启用 |
| created_at | TIMESTAMPTZ | 默认 now() | 注册时间 |
| updated_at | TIMESTAMPTZ | 默认 now()，更新自动刷新 | 更新时间 |

### 7.2 request_logs 请求日志表

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | BIGINT | 主键，自增 | 记录 ID |
| user_id | BIGINT | 外键→users.id，索引 | 所属用户 |
| task_type | VARCHAR(20) | 非空 | summarize / translate |
| provider | VARCHAR(50) | 非空 | 实际调用的大模型供应商 |
| model | VARCHAR(100) | 可空 | 模型名 |
| input_length | INTEGER | 非空 | 输入文本字符数 |
| output_length | INTEGER | 可空 | 输出文本字符数 |
| prompt_tokens | INTEGER | 可空 | 输入 token 数（大模型计费依据） |
| completion_tokens | INTEGER | 可空 | 输出 token 数 |
| total_tokens | INTEGER | 可空 | 总 token 数 |
| latency_ms | INTEGER | 可空 | 大模型调用耗时（毫秒） |
| status | VARCHAR(20) | 非空 | success / failed |
| error_message | TEXT | 可空 | 失败原因（截断保存） |
| created_at | TIMESTAMPTZ | 默认 now()，索引 | 调用时间 |

> 索引设计：`request_logs(user_id, created_at DESC)` 支撑"我的历史分页查询"；`request_logs(task_type)` 支撑统计。

### 7.3 迁移管理（Alembic）

- 每次表结构变更：`alembic revision --autogenerate -m "说明"` 生成迁移脚本，`alembic upgrade head` 应用。
- 迁移脚本进入 git 版本管理，任何环境（开发/测试/生产）执行同一套脚本，保证表结构一致。

---

## 8. 核心机制详解

### 8.1 JWT 认证流程

```text
注册 ──► 密码 bcrypt 哈希 ──► 写入 users 表
登录 ──► 校验密码 ──► 签发 access_token(15分钟) + refresh_token(7天)
请求 ──► 请求头 Authorization: Bearer <access_token>
        ──► 依赖注入校验签名/过期时间 ──► 从 token 解出 user_id ──► 查库确认用户有效
刷新 ──► 用 refresh_token 调 /auth/refresh ──► 签发新的 access_token
```

- access_token 短时效（15 分钟）：即使泄露，危害窗口小。
- refresh_token 长时效（7 天）：用于无感续期，减少用户反复登录。
- 密码绝不存明文，也不可逆解出（bcrypt 单向哈希 + 随机盐）。

### 8.2 多 Provider 大模型调用（核心亮点）

**设计目标：一套代码，任意切换供应商。**

所有兼容 OpenAI 协议的供应商（OpenAI、DeepSeek、通义千问、豆包、Moonshot、本地 vLLM/Ollama 等）都暴露相同的 `/chat/completions` 接口。我们统一用 `openai` SDK，只通过**环境变量**切换：

```text
LLM_PROVIDER=deepseek            # 当前供应商名（用于记录日志/历史）
LLM_BASE_URL=https://api.deepseek.com/v1   # 供应商兼容接口地址
LLM_API_KEY=sk-xxxx              # 该供应商的密钥
LLM_MODEL=deepseek-chat          # 模型名
```

代码里用一个 `LLMClient` 类封装：`chat(messages, temperature, max_tokens)` 统一入口。换供应商 = 改 `.env` 里 4 个变量，**零代码改动**。

**请求摘要时我们给大模型的 Prompt（提示词工程）：**

```
你是一个专业的中文文本摘要助手。
请对以下文本进行摘要，输出{max_length}字以内的摘要，直接输出摘要内容，不要任何解释。
【文本】
{用户输入的文本}
```

**请求翻译时：**

```
你是一个专业的翻译引擎。请把下面的文本翻译成{target_lang}，直接输出译文，不要任何解释。
【文本】
{用户输入的文本}
```

### 8.3 Redis 限流（滑动窗口）

- 每分钟限制：`LLM_RATE_LIMIT_PER_MINUTE=5`（示例值，可配）
- 每天限制：`LLM_RATE_LIMIT_PER_DAY=200`（示例值，可配）

实现原理（非常简单）：

```text
每个用户 + 每个时间桶 一个 Redis key：
  key = rate:min:{user_id}:{当前分钟}
  INCR key → 若结果 > 5 → 拒绝(429)
  EXPIRE key 120 秒 → 自动清理，Redis 不膨胀
```

用两个桶（分钟桶 + 天桶）分别判断，任一超限即拒绝，响应头返回 `X-RateLimit-Remaining` 让客户端知道剩余额度。

### 8.4 结构化日志

- 使用 **structlog** 输出 JSON 格式，每行日志是一个 JSON 对象，方便 grep / 接入 Loki / ELK。
- 中间件为每个请求生成 **request_id**（UUID），并注入日志上下文：`request_id`、`path`、`method`、`user_id`、`status_code`、`duration_ms`。
- 日志分级：`INFO`（请求进出）、`WARNING`（限流/上游超时）、`ERROR`（异常堆栈，含 request_id 可追踪）。
- 敏感信息过滤：**绝不打印**密码、令牌、API Key、请求原文。

示例日志行：

```json
{"event": "request_finished", "request_id": "a3f9...", "method": "POST",
 "path": "/api/v1/ai/translate", "status_code": 200, "duration_ms": 812,
 "user_id": 7, "level": "info", "timestamp": "2026-09-07T10:00:00Z"}
```

### 8.5 Prometheus 监控

- 用 `prometheus-fastapi-instrumentator` 自动统计每个路由的：请求总数、请求耗时直方图、状态码计数。
- 自定义指标：`llm_requests_total{provider, task_type, status}`（大模型调用次数）、`llm_latency_seconds`（大模型耗时）、`rate_limit_rejections_total`（限流拒绝次数）。
- Grafana 连 Prometheus 后，可画：QPS、P95 延迟、错误率、按 provider 的调用占比、限流拒绝趋势。

### 8.6 统一错误处理

- 自定义异常类 `AppError(code, message, http_status)`。
- 全局异常处理器：捕获 `AppError` → 返回统一 JSON；捕获未预期异常 → 记 ERROR 日志 + 返回 500 统一格式（不泄露堆栈给客户端）。
- 好处：前端解析逻辑统一，错误信息可控不泄密。

---

## 9. 部署架构

### 9.1 docker-compose 服务编排

| 服务 | 镜像 | 端口（对外） | 说明 |
|---|---|---|---|
| app | 本地构建 | 仅内网 8000 | FastAPI 应用（gunicorn+uvicorn workers） |
| db | postgres:16-alpine | 仅内网 5432 | PostgreSQL，数据卷持久化 |
| redis | redis:7-alpine | 仅内网 6379 | 限流计数 |
| nginx | nginx:alpine | **80/443（唯一对外入口）** | 反向代理 + TLS + 静态页 |
| prometheus | prom/prometheus | 仅内网 9090 | 指标采集 |
| grafana | grafana/grafana | 仅内网 3000 | 监控面板 |

> 安全设计：**只有 Nginx 暴露到公网**，其余服务都在 docker 内部网络，外部无法直连数据库和 Redis。

### 9.2 生产化要点

- **进程管理**：应用容器内用 `gunicorn`（多 worker）+ `uvicorn` worker 类（异步），提升吞吐。
- **反向代理**：Nginx 负责 TLS 证书（Let's Encrypt）、请求转发、静态资源缓存、限速兜底。
- **日志采集**：应用 JSON 日志输出到 stdout，由 docker 收集；生产可接 Loki 或云日志服务。
- **健康检查**：docker-compose 配置 `healthcheck`，app 依赖 db/redis 就绪后才启动。
- **数据持久化**：PostgreSQL 与 Grafana 数据挂载 volume，重启不丢。

---

## 10. 本地开发：小白一步步跑起来

### 前置条件（装一次）

1. 安装 **Docker Desktop**（https://www.docker.com/products/docker-desktop/）
2. 安装 **Python 3.12+**（https://www.python.org/downloads/）
3. （可选）安装 Git

### 第一步：准备环境变量

```bash
cd ai-api-service
copy .env.example .env        # Windows
# 或 cp .env.example .env     # Mac/Linux
```

打开 `.env`，把 `LLM_API_KEY` 换成你自己的大模型 API Key（DeepSeek/通义/OpenAI 兼容均可）。

### 第二步：一键启动全部服务（推荐方式）

```bash
docker compose up --build
```

等启动完成后：

| 地址 | 内容 |
|---|---|
| http://localhost | 在线体验测试页 |
| http://localhost/docs | Swagger 接口文档（可在线调试） |
| http://localhost:3000 | Grafana（admin/admin） |
| http://localhost:9090 | Prometheus |

### 第三步：手动体验完整流程（纯命令行，理解原理）

```bash
# 1. 注册
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Abc123456"}'

# 2. 登录，拿到令牌
curl -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Abc123456"}'
# 响应里复制 access_token

# 3. 调用翻译
curl -X POST http://localhost/api/v1/ai/translate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <你的access_token>" \
  -d '{"text":"Hello world","target_lang":"zh"}'

# 4. 查看历史
curl "http://localhost/api/v1/history?page=1&page_size=10" \
  -H "Authorization: Bearer <你的access_token>"
```

### 第四步：数据库结构变更（进阶）

```bash
docker compose exec app alembic revision --autogenerate -m "描述"
docker compose exec app alembic upgrade head
```

### 第五步：跑测试

```bash
docker compose exec app pytest -v
```

### 常见问题排查

| 现象 | 原因与解决 |
|---|---|
| `docker compose up` 后 app 一直重启 | db/redis 未就绪，首次会自动等待，稍候；或看 `docker compose logs app` |
| 调用 AI 接口报 502 | `.env` 中 `LLM_BASE_URL`/`LLM_API_KEY` 配置错误或网络不通 |
| 429 限流 | 默认每分钟 5 次，改 `.env` 中 `LLM_RATE_LIMIT_PER_MINUTE` 后重启 |
| 端口被占用 | 修改 `docker-compose.yml` 中对应端口映射 |

---

## 11. 测试方案

| 测试文件 | 覆盖内容 | 关键点 |
|---|---|---|
| tests/conftest.py | 测试夹具 | 独立测试数据库、内存/测试 Redis、测试客户端、临时用户工厂 |
| tests/test_auth.py | 认证 | 注册成功/重复邮箱/弱密码、登录成功/错误密码、无令牌访问 401、刷新令牌 |
| tests/test_ai.py | AI 接口 | 未登录 401、限流 429、模拟上游成功/失败（mock LLM 服务，不真实调用大模型） |
| tests/test_history.py | 历史 | 分页、按类型过滤、只能看自己的记录 |

**测试原则**：
- 测试中**不真实调用**大模型（用 `unittest.mock` 替换 LLM 服务），保证测试快速、稳定、免费。
- 数据库用独立测试库，每个用例结束清理数据，互不干扰。
- 覆盖核心路径 + 关键异常路径（401/429/502）。

---

## 12. 分阶段实施计划

| 阶段 | 内容 | 交付物 | 验收标准 |
|---|---|---|---|
| **P0 框架搭建**（当前） | 目录结构、配置管理、日志、异常处理、Docker 基础 | 可启动的空服务 + 本文档 | `docker compose up` 能起、/healthz 返回 ok |
| **P1 数据层** | SQLAlchemy 模型 + Alembic 迁移 | users/request_logs 表 | 迁移可执行、可回滚 |
| **P2 认证** | 注册/登录/刷新 + JWT + 密码哈希 | auth 路由 + 测试 | curl 全流程通过，test_auth 全绿 |
| **P3 AI 能力** | LLM 多 provider 服务 + 摘要/翻译路由 | ai 路由 + 测试 | 真实调用任一兼容 API 成功；mock 测试全绿 |
| **P4 历史与限流** | 历史记录服务 + Redis 限流 | history 路由 + 限流中间件 | 分页查询正确；超限返回 429 |
| **P5 监控与日志** | Prometheus 指标 + 结构化日志完善 | /metrics + 日志中间件 | Grafana 能看到请求量/延迟/错误率 |
| **P6 测试页与打磨** | 静态体验页 + 错误文案完善 | index.html | 浏览器可完成注册→摘要→翻译→看历史 |
| **P7 生产部署** | Nginx+TLS、gunicorn、生产配置 | 部署文档 + compose 生产配置 | 服务器一键部署，HTTPS 访问正常 |

> 当前状态：P0 完成框架骨架 + 计划文档；P1~P7 按里程碑推进。

---

## 13. 安全清单

- [x] 密码 bcrypt 加盐哈希存储，不存明文
- [x] JWT 短时效（15 分钟 access + 7 天 refresh）
- [x] 统一错误响应不泄露堆栈与内部信息
- [x] 日志过滤敏感字段（密码/令牌/API Key/原文）
- [x] Redis 限流防滥用
- [ ] 生产启用 HTTPS（Let's Encrypt + Nginx）【P7 实施】
- [ ] 数据库仅内网可达（compose 网络隔离）【P7 校验】
- [ ] CORS 白名单配置（仅允许指定前端域名）【P7 实施】
- [ ] 输入长度上限校验（如摘要文本 ≤ 20000 字符）【P3 实施】
- [ ] 依赖定期升级与安全扫描（pip-audit / trivy）【持续】
- [ ] 大模型密钥走密钥管理（生产可用 Docker Secret / Vault）【P7 可选】

---

## 14. 后续可扩展方向

- 增加"情感分析 / 关键词提取 / 润色改写"等新任务类型（复用现有 LLM 服务，加一个 prompt 模板即可）
- 用户用量统计与配额包（免费 100 次/月、付费 10000 次/月）
- 异步任务队列（超长文本用 Celery/RQ 后台处理 + 轮询结果）
- 多租户 / 管理员后台（管理用户、查看全局用量）
- 数据看板（Grafana 面板 + 用户侧用量报表接口）
- 缓存层：相同输入命中 Redis 缓存直接返回，节省 token 费用
- 流式输出（SSE）：大模型边生成边返回，提升长文体验

---

*本文档与技术栈如有调整，以最新提交为准；所有配置示例均为开发默认值，生产环境需按实际调整。*
