# 小童 AI Agent 智能学习助手

这是一个基于 FastAPI 的个人学习助手项目，已完成 9 月 23 日容器化验收基线：RBAC 权限、MySQL/ChromaDB/Agent 三层数据隔离、问答日志、管理员基础接口、双存储一致性修复、可重复执行的权限与主链路测试，以及 Docker Compose 一键启动。当前版本对应 Git 标签：`enterprise-mvp`

## 核心能力

- 用户注册、登录、JWT 鉴权和个人资料查询。
- 学习目标、学习任务的新增、查询、更新和删除。
- 上传 PDF/DOCX，解析文本、切分分块并写入 ChromaDB 向量库。
- 基于个人知识库的普通 RAG 问答和 SSE 流式问答。
- 基于 DeepSeek Function Calling 的 Agent 对话与 Redis 多轮会话。
- `user/admin` 双角色权限控制。
- 管理员分页查询用户、全局文档和问答日志。
- 问答日志脱敏、耗时记录、知识命中状态和失败信息记录。
- 文档上传失败回滚 MySQL，删除文档时同步清理 ChromaDB 分块。

## 技术栈

| 类型        | 技术                           |
| --------- | ---------------------------- |
| Web 框架    | FastAPI + Uvicorn            |
| 数据库       | MySQL + SQLAlchemy + PyMySQL |
| 数据库迁移     | Alembic                      |
| 鉴权        | JWT + passlib/bcrypt         |
| 向量库       | ChromaDB 持久化模式               |
| Embedding | 硅基流动 BGE 中文向量模型              |
| 大模型       | DeepSeek                     |
| 缓存与会话     | Redis                        |
| 文档解析      | PyMuPDF、python-docx          |
| 前端        | 原生 HTML/CSS/JavaScript + SSE |
| 测试        | pytest + FastAPI TestClient  |

## 目录结构

```text
fastapi-demo/
├── alembic/                 # 数据库迁移
├── app/
│   ├── api/                 # FastAPI 路由
│   ├── core/                # 鉴权、依赖、响应、异常和日志
│   ├── db/                  # SQLAlchemy 数据库连接
│   ├── models/              # ORM 模型
│   ├── schemas/             # Pydantic 请求与响应模型
│   ├── services/            # 业务服务
│   ├── utils/               # Redis、ChromaDB、LLM 等外部能力封装
│   └── main.py              # 应用入口
├── data/chroma_db/          # ChromaDB 本地持久化目录
├── docs/                    # 权限矩阵和开发记录
├── static/index.html        # 演示前端
├── tests/                   # 权限、主链路和异常回归测试
├── .env.example             # 环境变量模板
└── requirements.txt         # 依赖清单
```

## 本地启动

### 1. 前置服务

- MySQL 8.x 已启动。
- Redis 已启动，默认地址为 `127.0.0.1:6379`。
- 已准备 DeepSeek API Key 和硅基流动 API Key。

当前版本的数据库、JWT、Redis、ChromaDB、上传目录、DeepSeek 和硅基流动配置均从 `.env` 读取。新环境复制 `.env.example` 并填写真实值后即可启动。

本地直接运行应用时，`DB_HOST`、`REDIS_HOST` 和 `CHROMA_HOST` 应指向本机服务地址；Docker Compose 会覆盖为容器服务名，不需要手工修改业务代码。

### 2. 安装依赖

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. 配置环境变量

```powershell
Copy-Item .env.example .env
```

在 `.env` 中填写真实密钥，不要提交 `.env`：

```dotenv
DEEPSEEK_API_KEY=你的DeepSeek密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
SILICONFLOW_API_KEY=你的硅基流动密钥
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5
DB_HOST=localhost
DB_PORT=3306
DB_USER=你的数据库用户
DB_PASSWORD=你的数据库密码
DB_NAME=ai_agent_db
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
JWT_SECRET_KEY=你的JWT密钥
```

### 4. 初始化数据库

```powershell
alembic upgrade head
```

### 5. 启动服务

```powershell
uvicorn app.main:app --reload
```

启动后访问：

- 接口文档：`http://127.0.0.1:8000/docs`
- 演示页面：`http://127.0.0.1:8000/static/index.html`

### 6. Docker Compose 一键启动

已安装 Docker Engine 和 Docker Compose 插件时，可使用容器方式从空数据卷启动：

```powershell
Copy-Item .env.example .env
# 填写 DB_PASSWORD、REDIS_PASSWORD、DEEPSEEK_API_KEY 和 SILICONFLOW_API_KEY
docker compose up -d --build
docker compose ps
```

Compose 会自动：

- 启动 FastAPI、MySQL 8、Redis 7 和 ChromaDB。
- 等待 MySQL、Redis 健康后执行 `alembic upgrade head`。
- 将容器内数据库、Redis 和 ChromaDB 地址切换为服务名。
- 将 MySQL、Redis 和 ChromaDB 数据保存到命名数据卷。

启动完成后访问：

- 接口文档：`http://127.0.0.1:8000/docs`
- 演示页面：`http://127.0.0.1:8000/static/index.html`
- ChromaDB 宿主机端口：`http://127.0.0.1:8001`

停止容器：

```powershell
docker compose down
```

如需从空数据重新验收，可在确认不需要现有数据后执行 `docker compose down -v`，再重新运行 `docker compose up -d --build`。

## 权限与数据隔离

系统包含 `user` 和 `admin` 两个角色。

| 能力            | 普通用户    | 管理员     |
| ------------- | ------- | ------- |
| 个人资料          | 仅本人     | 仅本人     |
| 目标、任务、文档      | 仅本人数据   | 仅本人数据   |
| RAG 与 Agent   | 仅使用本人数据 | 仅使用本人数据 |
| 管理员用户、文档、日志查询 | 403     | 200     |

未登录或 Token 无效返回 `401`，角色不足返回 `403`，资源不存在或跨用户访问返回 `404`。

管理员角色可通过数据库调整，修改后需要重新登录：

```sql
UPDATE users SET role = 'admin' WHERE username = '你的用户名';
```

## 问答日志

普通 RAG、流式 RAG 和缓存命中都会写入 `qa_logs`，记录以下信息：

- 用户 ID、问题、回答摘要。
- 耗时、是否命中知识库。
- 成功或失败状态、错误信息。
- 创建时间。

问题、回答摘要和错误信息写入前会进行长度限制和基础脱敏。日志写入失败只记录应用日志，不影响问答主流程。

## 测试

运行全部正式测试：

```powershell
.\venv\Scripts\python.exe -m pytest
```

测试使用独立 SQLite 内存数据库模拟 MySQL 请求链路，并替换 LLM、向量库和 Redis 调用，不会污染开发数据库。当前共 41 条测试，覆盖：

- 至少 10 条权限测试，包含 `401`、`403`、`200` 和跨用户访问。
- 注册、登录、目标、任务、文档、RAG、Agent 主链路。
- Agent 目标/任务工具、RAG 工具和跨用户数据隔离。
- 前端学习管家入口。
- 空参数、无 Token、错误角色、跨用户、日志写入失败、上传失败回滚。
- 环境变量必填项、数据库 URL 和 JWT 配置来源。

## 主要接口

| 方法       | 路径                        | 说明          |
| -------- | ------------------------- | ----------- |
| POST     | `/api/v1/register`        | 用户注册        |
| POST     | `/api/v1/login`           | 用户登录并获取 JWT |
| GET      | `/api/v1/users/me`        | 获取当前用户      |
| POST/GET | `/api/v1/goals`           | 创建或查询目标     |
| POST/GET | `/api/v1/tasks`           | 创建或查询任务     |
| POST     | `/api/v1/files/upload`    | 上传并解析文档     |
| GET      | `/api/v1/files`           | 查询当前用户文档    |
| POST     | `/api/v1/rag/ask`         | RAG 问答      |
| POST     | `/api/v1/rag/ask/stream`  | RAG 流式问答    |
| POST     | `/api/v1/agent/chat`      | Agent 统一对话  |
| GET      | `/api/v1/admin/users`     | 管理员查询用户     |
| GET      | `/api/v1/admin/documents` | 管理员查询文档元数据  |
| GET      | `/api/v1/admin/qa-logs`   | 管理员查询问答日志   |

## 9 月 19 日验收结果

- 权限测试不少于 10 条。
- 双角色全流程和跨用户访问均有自动化测试。
- 无 Token、错误角色、空参数、日志失败和上传失败均有回归覆盖。
- `README.md`、`.env.example` 和 `requirements.txt` 已补齐。
- 文档上传回滚、删除一致性和敏感字段治理已纳入测试。

完整回归记录见 `docs/9月19日验收记录.md`。

9 月 20 日配置治理和冒烟测试记录见 `docs/9月20日验收记录.md`。

9 月 23 日容器化、迁移和真实服务端到端验收记录见 `docs/9月23日验收记录.md`。

## 注意事项

- 根目录的 `test_*.py` 是历史原型和调试脚本，不属于正式测试集；正式测试由 `pytest.ini` 限定在 `tests/`。
- 当前 `.env` 可能包含真实密钥，必须保持被 `.gitignore` 忽略。
- 运行历史原型脚本可能真实创建目标、任务和向量数据，建议只使用测试数据库或确认数据后可回滚的环境。
