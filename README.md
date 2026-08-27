# OwnerBlog

个人技术知识库与智能问答平台。普通用户可以创建和提交自己的 Markdown 文章、阅读公开内容并发表评论；管理员负责账号和内容审核。只有审核通过且索引成功的文章才进入公开展示和 Chroma 知识库问答。

> 当前仓库已完成 Day 2 的 Article 模型、SQLite migration、Django Admin、公开文章列表/详情 API 和 Vue 前台读取链路。评论、审核、文章写入、索引和知识问答仍按后续计划实现。

## 当前进度

- Day 1：项目骨架、登录基础能力和 Health 联调已完成
- Day 2 Phase 1：Article 模型、SQLite 表和 migration 已完成
- Day 2 Phase 2：Django Admin 文章管理已完成
- Day 2 Phase 3：公开文章列表和详情 API 已完成
- Day 2 Phase 4：Vue 文章列表、详情和请求状态已完成
- Day 2 Phase 5：自动化测试、删除流程验证和 Git 提交仍待补充

## 文档入口

- [项目开发规范](docs/development-specification.md)
- [Day 1 执行计划](plan/day1.md)
- [Phase 1 MVP 总体计划](plan/phase1-mvp.md)
- [项目阶段规划](plan/project-plan.md)

文档职责：`development-specification.md` 定义全项目架构、组件、接口和技术能力；`project-plan.md` 定义长期路线；`phase1-mvp.md` 定义 Phase 1 范围；`day1.md` 定义当天任务。

## 当前状态

当前已存在：

- `plan/day1.md`
- `plan/phase1-mvp.md`
- `plan/project-plan.md`
- `deep-research-report.md`
- `docs/development-specification.md`
- `README.md`
- `backend/.venv/`（本地环境，已被 Git 忽略）
- `backend/requirements.txt`
- `backend/.env.example`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- Django Project 与四个业务 App
- Vue 3 + Vite 页面、路由、Axios 和开发代理
- `GET /api/health` 及前后端代理联调

当前尚未创建或完成：

- User、Article、Comment、ArticleChunk 数据模型和权限
- 用户认证、投稿、管理员审核和评论流程
- Chroma 索引、embedding 和知识库问答

因此，下面的 Django、前端和 Health 测试命令可以直接执行；文章、评论、审核和知识库业务接口需要等待后续 Phase 实现。

## 技术栈

| 层次 | 技术 | 说明 |
| --- | --- | --- |
| 后端 | Python、Django、Django REST Framework | API、管理入口和业务编排 |
| 内容管理 | Django Admin | Phase 1 的文章创建、编辑和发布入口 |
| 数据库 | SQLite | 保存 User、Article 和 ArticleChunk 映射 |
| 前端 | Vue 3、Vite、Vue Router、Axios | 文章展示、问答页面和 API 调用 |
| 向量库 | Chroma PersistentClient | 保存文章向量和检索 metadata |
| 模型 | OpenAI-compatible 模型服务 | embedding 和回答生成 |
| 测试 | pytest | 后续接口和 RAG 关键测试 |

## 规划目录

```text
ownerblog/
├─ plan/
│  ├─ day1.md                  # Day 1 执行步骤和验收
│  ├─ phase1-mvp.md           # Phase 1 总体范围和一周计划
│  └─ project-plan.md         # 项目整体阶段规划
├─ docs/
│  └─ development-specification.md  # 全项目开发规范
├─ backend/                   # Django 后端（项目骨架待创建）
│  ├─ manage.py
│  ├─ config/                 # Django 项目配置和总路由
│  ├─ accounts/               # 登录、Session 和角色权限（注册为 Future）
│  ├─ articles/               # Article、作者权限、投稿和公开 API
│  ├─ comments/               # 评论、本人权限和审核
│  ├─ knowledge/              # 索引、检索、问答和 ArticleChunk
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/                  # Vue/Vite 前端（源码骨架待创建）
│  ├─ src/
│  │  ├─ api/                 # Axios 请求封装
│  │  ├─ views/               # 列表、详情和问答页面
│  │  ├─ components/          # 可复用展示组件
│  │  └─ router/              # Vue Router
│  ├─ package.json
│  ├─ pnpm-lock.yaml
│  └─ vite.config.js
├─ README.md
└─ .gitignore
```

普通用户通过 Vue + REST API 登录、投稿和管理自己的内容；管理员通过 Django Admin 管理账号及全量文章、评论。Phase 1 不实现公开注册，也不实现 `/api/admin/*` 审核 API；管理员审核、下架、删除和索引重建均通过 Django Admin 或 management command 完成。

Phase 1 前端页面：`/` 公开文章列表、`/articles/{id}` 文章详情、`/my-articles` 当前用户文章管理、`/knowledge` 无需登录即可调用且只检索公开文章的知识库问答。

## 前置环境

后续开发需要：

- Git
- Python 3.13（当前验证版本：3.13.15）
- Node.js 24.x 和 pnpm（当前前端使用 pnpm 锁定依赖）
- 可访问的 OpenAI-compatible 模型服务（只有实现 embedding 和问答时需要）

Python 依赖版本固定在 `backend/requirements.txt`；前端依赖版本由 `frontend/package.json` 和 `frontend/pnpm-lock.yaml` 共同固定。更换 Python、Node.js、pnpm 或依赖版本时，需要重新验证并同步更新文档和锁定文件。

## 后端环境与启动

### 创建虚拟环境

`.venv` 是当前设备和当前操作系统专用的运行环境，不能从 Windows 直接复制到 macOS/Linux，也不能反向复制。更换设备时保留 `requirements.txt`，在新设备重新创建即可。

Windows PowerShell：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

macOS/Linux：

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

虚拟环境会根据操作系统自动生成目录：Windows 使用 `.venv/Scripts/`，macOS/Linux 使用 `.venv/bin/`。不需要手动新增 `bin` 或 `Scripts` 目录；也不要提交 `.venv`。

如果 Windows PowerShell 禁止执行激活脚本，可在当前用户范围配置执行策略后重新打开终端；也可以直接使用 `.venv\Scripts\python.exe` 执行命令，不必激活环境。

### 配置环境变量

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

macOS/Linux：

```bash
cp .env.example .env
```

`.env` 只存本地配置，不能提交。不要把真实 API Key 写入 README、Vue 代码、浏览器请求或 Git。

建议的后端变量如下：

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173

DATABASE_PATH=./data/db.sqlite3
CHROMA_PERSIST_DIRECTORY=./data/chroma

MODEL_BASE_URL=
MODEL_API_KEY=
MODEL_NAME=
EMBEDDING_MODEL=

CHUNK_SIZE=1000
CHUNK_OVERLAP=150
EMBEDDING_BATCH_SIZE=32
SIMILARITY_THRESHOLD=0.75
MAX_RETRIEVED_CHUNKS=5
MAX_CONTEXT_CHARS=8000
LLM_TIMEOUT_SECONDS=30
```

变量说明：

- `MODEL_BASE_URL`：模型服务的兼容 API 地址。
- `MODEL_API_KEY`：服务端模型密钥，只能由后端读取。
- `MODEL_NAME`：回答模型名称。
- `EMBEDDING_MODEL`：文章入库和问题查询共同使用的 embedding 模型。
- `DATABASE_PATH`：SQLite 本地数据库文件路径。
- `CHROMA_PERSIST_DIRECTORY`：Chroma 本地持久化目录。
- `CHUNK_SIZE`、`CHUNK_OVERLAP`：文章切分参数。
- `EMBEDDING_BATCH_SIZE`：embedding 批处理大小。
- `SIMILARITY_THRESHOLD`：检索结果最低相似度阈值。
- `MAX_RETRIEVED_CHUNKS`、`MAX_CONTEXT_CHARS`：模型上下文限制。
- `LLM_TIMEOUT_SECONDS`：模型请求超时时间。

### 检查和启动

```powershell
python manage.py check
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

`createsuperuser` 仅用于开发者创建 Django Admin 维护账号，不代表产品新增“超级管理员”角色。Phase 1 产品角色只有普通用户和管理员；管理员负责审核、账号启停和索引运维。

接入本地 Chroma PersistentClient 后，使用：

```powershell
python manage.py runserver 8000 --noreload
```

原因是自动重载可能启动多个进程，嵌入式 Chroma 在多个进程同时写入持久化文件时容易发生冲突。当前 Phase 1 不使用 Chroma HTTP Server，也不承诺高并发生产部署。

后端预期地址：

```text
http://127.0.0.1:8000
```

Django Admin 预期入口：

```text
http://127.0.0.1:8000/admin/
```

## 前端环境与启动

在另一个终端执行：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

如果项目尚未生成 `pnpm-lock.yaml`，首次安装可以使用：

```powershell
pnpm install
```

预期访问地址：

```text
http://localhost:5173
```

Day 1 选择 Vite Proxy 处理本地前后端转发。Vue/ Axios 使用相对路径：

```text
/api/health
```

不要在浏览器代码中硬编码：

```text
http://127.0.0.1:8000/api/health
```

前端构建验证：

```powershell
pnpm build
pnpm preview
```

Vite Proxy 和 Django CORS 只选择一种。本项目 Day 1 采用 Vite Proxy，不同时引入两套跨域方案。

## 本地测试启动

首次启动或更换设备时，先完成后端依赖安装和前端依赖安装。之后使用两个 PowerShell 终端：

终端一：启动 Django 后端。

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

终端二：启动 Vue/Vite 前端。

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

启动后访问：

```text
前端页面：http://127.0.0.1:5173/
Django Health：http://127.0.0.1:8000/api/health
前端代理 Health：http://127.0.0.1:5173/api/health
Django Admin：http://127.0.0.1:8000/admin/
```

Health 联调验证：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
Invoke-WebRequest http://127.0.0.1:5173/api/health
```

两个请求都应返回 HTTP `200` 和 `{"status":"ok"}`。第一个请求验证 Django，第二个请求验证 Vue 页面经过 Vite Proxy 访问 Django 的完整链路。

停止服务时，在对应终端按 `Ctrl+C`。如果端口被占用，先关闭旧的 Django/Vite 进程，或更换端口并同步修改 `frontend/vite.config.js`。

## 快速启动与排查

### 启动

后端终端：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py runserver 127.0.0.1:8000
```

前端终端：

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev --host 127.0.0.1
```

### 配置

后端首次使用：`Copy-Item backend/.env.example backend/.env`

前端 `frontend/.env`：

```env
VITE_API_BASE_URL=/api
VITE_USE_MOCKS=false
```

前端文章列表和详情使用 Django API；知识问答页面仍保留 mock 逻辑，直到后续知识库接口完成。

### Health

```text
后端接口：http://127.0.0.1:8000/api/health
代理接口：http://127.0.0.1:5173/api/health
测试页面：http://127.0.0.1:5173/health
```

预期返回：`{"status":"ok"}`。

### 排查

- 页面空白：运行 `pnpm build`，检查 Vue import 和变量拼写。
- Health 失败：确认 Django 是否运行在 `8000` 端口。
- Health 404：检查 `backend/config/urls.py`。
- 请求出现完整后端地址：检查 `frontend/src/api/client.js` 是否使用 `/api`。
- 安装失败：确认使用 pnpm，且 `pnpm-lock.yaml` 与 `package.json` 匹配。

## API 验证

### 当前接口基线

项目开发规范定义以下 Phase 1 接口；Day 2 已实现公开文章读取接口，其余写入、审核和知识库接口仍在后续阶段实现：

| 方法 | 路径 | 用途 | 登录要求 |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | Future：普通用户注册，Phase 1 不实现 | 不需要 |
| `POST` | `/api/auth/login` | Session 登录 | 不需要 |
| `POST` | `/api/auth/logout` | 退出登录 | 需要登录 |
| `GET` | `/api/auth/me` | 当前用户和角色 | 需要登录 |
| `GET` | `/api/articles` | 获取已公开且已索引文章列表 | 不需要 |
| `GET` | `/api/articles/{id}` | 获取已公开且已索引文章详情 | 不需要 |
| `GET` | `/api/my-articles` | 获取当前用户自己的文章 | 需要登录 |
| `POST` | `/api/articles` | 创建自己的文章草稿 | 需要登录 |
| `PATCH/DELETE` | `/api/articles/{id}` | 修改/删除自己的文章，管理员可管理全部 | owner/admin |
| `POST` | `/api/articles/{id}/submit-review` | 提交文章审核 | owner/admin |
| `GET/POST` | `/api/articles/{id}/comments` | 查看通过评论/创建评论 | 读公开；写需登录 |
| `DELETE` | `/api/comments/{id}` | 删除自己的评论，管理员可删除全部 | owner/admin |
| `POST` | `/api/admin/articles/{id}/approve` | Future：管理员通过文章并触发索引 | admin |
| `POST` | `/api/admin/articles/{id}/offline` | Future：管理员下架文章 | admin |
| `GET` | `/api/health` | 检查后端和代理链路 | 不需要 |
| `POST` | `/api/knowledge/chat` | 单轮知识库问答，允许匿名访问 | 不需要 |

`/admin/` 是 Django Session/staff 管理入口，不属于 Vue 公开 API。完整请求/响应和权限规则见项目开发规范。

### Health 验证

PowerShell：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health
```

预期：HTTP `200`，响应 JSON：

```json
{
  "status": "ok"
}
```

health 不应访问 SQLite、Chroma 或外部模型服务。

浏览器联调预期：

```text
Vue 页面 loading
  -> Axios 请求 /api/health
      -> Vite Proxy 转发到 Django
          -> Django 返回 {"status":"ok"}
              -> 页面显示 success / ok
```

主动停止 Django 后刷新页面：

```text
Axios 请求失败
  -> Vue 进入 error 状态
  -> 页面显示后端请求失败提示
```

### 测试（测试文件创建后执行）

```powershell
pytest
```

Phase 1 后续至少需要覆盖文章公开范围、草稿过滤、问答无结果、模型失败和关键 API 状态码。

## Git 忽略规则

`.gitignore` 必须忽略以下本地文件和目录：

```text
.venv/
backend/.venv/
__pycache__/
*.py[cod]
node_modules/
.env
*.sqlite3
*.sqlite
*.db
backend/data/
chroma/
backend/chroma/
.vite/
dist/
```

以下内容不应提交：

- `.env` 和真实 API Key
- Python 虚拟环境和 `node_modules`
- SQLite 数据库文件
- Chroma 持久化数据
- 构建产物和缓存

以下内容应提交，以保证依赖安装可复现：

- `backend/requirements.txt`
- `frontend/package.json`
- `frontend/pnpm-lock.yaml`

## 常见问题排查

### 1. `python` 或 `pip` 找不到

确认 Python 已安装，并检查当前终端是否使用了正确的 Python。进入后端目录后重新创建并激活虚拟环境。

### 2. PowerShell 无法激活虚拟环境

确认执行策略限制，并确保使用的是当前项目的 `backend/.venv`。不要直接删除或提交虚拟环境目录。

### 3. `pip install` 失败

先确认虚拟环境已激活，再检查网络、Python 版本和 `requirements.txt`。不要用未固定或来源不明的依赖替代项目依赖文件。

### 4. `pnpm install` 或 `pnpm install --frozen-lockfile` 失败

确认 Node.js 和 pnpm 已安装。`pnpm install --frozen-lockfile` 需要与 `package.json` 匹配的 `pnpm-lock.yaml`；项目首次生成或更新锁定文件时使用 `pnpm install`。

### 5. 前端显示请求失败

确认 Django 已启动、端口为 `8000`，并确认 `vite.config.js` 的 Proxy 目标与实际后端地址一致。后端停止时前端显示 error 是基础联调的预期行为。

### 6. 端口被占用

更换 Django 或 Vite 端口，并同步修改 Proxy 配置；不要通过硬编码多个后端地址掩盖配置问题。

### 7. 模型 API Key 或模型服务错误

确认只在后端 `.env` 配置模型变量，检查 `MODEL_BASE_URL`、`MODEL_API_KEY` 和 `MODEL_NAME`。Health API 不依赖模型服务，模型问题不应影响基础健康检查。

### 8. Chroma 写入冲突

确认本地开发使用单进程：

```powershell
python manage.py runserver --noreload
```

不要在多个 Django 进程中同时使用同一个嵌入式 Chroma 持久化目录。

### 9. 敏感文件出现在 Git 状态

立即停止提交操作，检查 `.gitignore` 和文件内容。确认 `.env`、API Key、数据库、Chroma 数据、`.venv` 和 `node_modules` 没有被追踪。

## 当前尚未实现内容

以下内容属于后续开发，不应因为 README 已经写出启动命令就视为完成：

1. 创建 Django 项目和 `accounts`、`articles`、`comments`、`knowledge` App。
2. 实现 `GET /api/health`。
3. 创建 Vue 3 + Vite 页面并联调 health。
4. 创建 User、Article、Comment、ArticleChunk 模型和 migrations。
5. 实现登录、Session/CSRF 和对象级权限；注册接口保留为 Future，不在 Phase 1 实现。
6. 实现普通用户文章投稿、本人编辑/删除和提交审核。
7. 实现管理员文章/评论审核、下架、删除和账号管理。
8. 实现已公开且已索引文章列表、详情和已通过评论 API。
9. 实现 Markdown 清洗、切分、embedding 和 Chroma 索引门禁。
10. 实现单轮问答、来源返回、无结果、模型和权限错误处理。
11. 编写权限、审核、索引、日志和 Phase 1 最终运行说明。

Day 1 的下一步入口是 [`plan/day1.md`](plan/day1.md) 中的 Phase 2；项目级开发规范见 [`docs/development-specification.md`](docs/development-specification.md)。
