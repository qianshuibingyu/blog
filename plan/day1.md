# Phase 1 Day 1（8 月 22 日）：需求、架构和骨架

- 所属阶段：[Phase 1 基础版本计划](./phase1-mvp.md)
- 上级路线：[项目阶段规划](./project-plan.md)

## 本日目标

完成整体设计和最小可运行骨架。今天不开发文章业务，学习内容必须服务于架构设计和项目初始化。

## 现在从哪里开始

今天严格按以下顺序执行：

```text
Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 -> Phase 4
  -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8
```

先从 Phase 0 确认范围和职责，再完成设计文档、Django 后端骨架、`GET /api/health`、Vue/Vite 前端骨架和 Axios 联调。未通过当前 Phase 的验收标准时，不进入下一阶段。

Day 1 只交付“设计完成、骨架可运行”，不实现完整认证、文章审核、评论、RAG 或业务页面。角色和权限必须完成设计，但不在当天实现。Phase 1 的完整范围请参阅 [Phase 1 MVP 总体计划](./phase1-mvp.md)。

## Day 1 可执行 Phase 拆分

每个 Phase 都遵循“先理解框架和代码职责，再实现，再验证”的方式。

### Phase 0：工作区与目标确认

目标：确认今天只完成前后端分离骨架，不进入文章业务开发。

执行内容：

- 确认 Phase 1 核心闭环和 Day 1 边界
- 确认前端、后端、数据库、向量库和模型服务的职责
- 确认 Day 1 实现 `GET /api/health`
- 确认文章列表、文章详情、知识库问答只进入 API 设计清单

验收：能够说明今天不实现 Article、Admin、Chroma、GPT 和 Docker。

### Phase 1：项目设计文档

目标：先完成今天要求的架构图、数据流图和 API 清单。

产出文件：

```text
docs/development-specification.md
```

Day 1 在这里建立项目级开发规范的第一版技术基线；该规范适用于整个 OwnerBlog，不是 Day 1 专属文档。文档必须包含：

- Phase 1 核心闭环和项目边界
- 系统架构图和组件职责
- 文章发布到问答的数据流图
- `accounts`、`articles`、`comments`、`knowledge` 模块职责
- 匿名访问状态、普通用户和管理员角色矩阵
- Article、Comment、ArticleChunk、User 和审核审计的规划字段与状态机
- 认证、文章、评论、审核和问答 API 的方法、路径、用途和登录/角色要求
- health 请求的完整链路
- 前端、后端、RAG、配置和主要技术能力规范
- 项目级安全、测试和扩展边界

Day 1 当日任务、学习内容和验收仍以本文档的 `plan/day1.md` 为准；项目级架构、组件、API 和技术能力以 `[docs/development-specification.md](../docs/development-specification.md)` 为准。

验收：架构图明确 Vue、Django、SQLite、Chroma 和模型服务的关系；数据流图明确文章发布、索引、提问、检索和回答流程。

### Phase 2：Git 与环境基础

目标：建立可恢复、可迁移的开发环境。

先理解 Git、Python 虚拟环境、npm、依赖锁定、`.gitignore` 和环境变量模板的作用，再执行：

- 初始化 Git 仓库
- 创建 Python 虚拟环境
- 创建 `.gitignore`
- 创建 `backend/requirements.txt`
- 创建 `backend/.env.example`
- 创建前端 `package.json` 和 `package-lock.json`

验收：`.venv`、`node_modules`、`.env` 和运行时数据库文件不会出现在 Git 状态中，且不写入真实 API Key。

### Phase 3：Django 后端骨架

目标：理解 Django Project、App、配置和路由。

先学习 `manage.py`、`settings.py`、`urls.py` 以及 Project 和 App 的区别，再创建：

```text
backend/
├─ manage.py
├─ config/
├─ accounts/
├─ articles/
├─ comments/
└─ knowledge/
```

`accounts` 和 `comments` 纳入项目架构规划；完整认证、权限、文章模型和评论实现放到 Day 2 之后。Day 1 只创建可供后续扩展的模块骨架，不实现业务授权。

验收：`accounts`、`articles`、`comments` 和 `knowledge` App 的职责边界明确，并正确加入 Django 配置。

### Phase 4：Django REST Framework 与 Health API

目标：用 DRF 实现第一个可验证接口。

先理解 DRF 与 Django View 的关系、API View、HTTP 方法、HTTP 状态码和 JSON 响应；今天暂不学习或实现 Serializer、Model 和 ViewSet。

实现：

```text
GET /api/health
```

返回：

```json
{"status": "ok"}
```

验收：`python manage.py check` 成功，Django 服务可以启动，接口返回 HTTP 200，且不访问数据库或外部模型服务。

### Phase 5：Vue 与 Vite 前端骨架

目标：理解 Vue 单文件组件和 Vite 开发服务器。

先学习 Vite 的作用，以及 Vue 单文件组件中的 `<template>`、`<script setup>` 和 `<style>` 职责，再创建 Vue 3 + Vite 项目。

页面只实现三种状态：

```text
loading
success
error
```

验收：Vite 开发服务器可以启动，浏览器可以打开页面，不引入 UI 组件库，只使用原生 CSS。

### Phase 6：Axios 与前后端联调

目标：完成真正的前后端分离请求链路。

先理解 Axios 实例、GET 请求、async/await、成功和失败处理，以及 Vite proxy 的作用，再实现：

```text
Vue 页面
  -> Axios
  -> /api/health
  -> Vite Proxy
  -> Django + DRF
  -> JSON 响应
  -> Vue 状态更新
```

验收：浏览器显示后端返回的 `ok`；停止 Django 后刷新页面，前端显示请求失败状态；前端不硬编码完整后端地址。

### Phase 7：文档、代码解释与复盘

目标：确保代码不仅能运行，而且能够解释。

执行内容：

- 编写 `README.md` 启动说明
- 补充目录和模块职责
- 补充 health 请求链路
- 记录常见错误和解决方式
- 记录 Day 1 未完成内容

验收：能够用自己的话说明每个主要文件的职责，并指出请求失败时可能出错的层次。

### Phase 8：Git 提交与最终验收

目标：留下第一个可恢复版本。

执行内容：

- 检查 `git status`
- 确认敏感文件和依赖目录未被追踪
- 创建第一次 Git commit
- 按 Day 1 量化验收标准逐项复测

验收：设计图、数据流图、API 清单、可运行后端、可运行前端和第一次有效 commit 全部存在。

Docker、Article/Comment migration、审核型 Django Admin 和完整业务权限放到后续 Phase，不混入今天的执行范围；Day 1 只完成这些能力的设计。

## Day 1 执行清单

以下清单用于当天逐项执行和验收。

### Phase 0：目标确认

- [x] 明确 Phase 1 核心链路
- [x] 明确前后端分离边界
- [x] 明确今天不做 Article、ArticleChunk、Admin、登录、Chroma、Embedding、GPT 和 Docker



### Phase 1：设计文档

- [x] 创建或完善 `docs/development-specification.md`
- [x] 写明 Phase 1 核心闭环和不做清单
- [x] 绘制系统架构图
- [x] 绘制文章发布到问答的数据流图
- [x] 说明 `accounts`、`articles`、`comments`、`knowledge` 的职责
- [x] 记录角色权限矩阵
- [x] 记录 Article、Comment、ArticleChunk、User 和审核审计的规划字段与状态机
- [x] 完成认证、文章、评论、审核和问答 API 清单
- [x] 写明 health 请求链路
- [x] 区分 Day 1 实现范围和后续阶段范围



### Phase 2：环境与 Git

- [x] 初始化 Git 仓库
- [x] 创建 Python 虚拟环境
- [x] 创建 `.gitignore`
- [x] 创建 `backend/requirements.txt`
- [x] 创建 `backend/.env.example`
- [x] 创建前端 `package.json`
- [x] 生成 `package-lock.json`
- [x] 确认 `.env`、`.venv`、`node_modules` 和运行时数据库不会被提交



### Phase 3：Django 后端骨架

- [x] 学习 Django Project 与 App 的区别
- [x] 创建 `backend/manage.py`
- [x] 创建 `config`、`accounts`、`articles`、`comments`、`knowledge`
- [x] 配置 `settings.py`
- [x] 配置 `config/urls.py`
- [x] 注册上述 App
- [x] 执行 `python manage.py check`



### Phase 4：DRF Health API

- [x] 学习 DRF API View、HTTP 方法、状态码和 JSON 响应
- [x] 实现 `GET /api/health`
- [x] 返回 `{"status": "ok"}`
- [x] 启动 Django 服务
- [x] 验证接口返回 HTTP 200
- [x] 确认接口不访问数据库和外部模型



### Phase 5：Vue 与 Vite

- [x] 学习 Vite 的作用
- [x] 学习 Vue 单文件组件
- [x] 理解 `<template>`、`<script setup>` 和 `<style>`
- [x] 创建 Vue 3 + Vite 项目
- [x] 创建最小页面
- [x] 使用原生 CSS
- [x] 配置 Vite 开发代理



### Phase 6：Axios 联调

- [x] 学习 Axios GET 请求和 `async/await`
- [x] 创建 `frontend/src/api/client.js`
- [x] 创建 health 页面
- [x] 实现 loading 状态
- [x] 实现 success 状态
- [x] 实现 error 状态
- [x] 浏览器显示后端返回的 `ok`
- [x] 停止 Django 后，前端显示请求失败
- [x] 确认前端未硬编码完整后端地址



### Phase 7：README 与复盘

- [x] 补充 `README.md`
- [x] 写明后端启动方式
- [x] 写明前端启动方式
- [x] 写明 health API 地址
- [x] 写明环境变量配置方式
- [x] 记录常见错误排查方式
- [x] 能说明主要文件职责
- [x] 能用自己的话说明完整请求链路



### Phase 8：最终验收与提交

- [x] `python manage.py check` 成功
- [x] Django 服务可以启动
- [x] `/api/health` 返回 HTTP 200
- [x] Vite 服务可以启动
- [x] 浏览器显示 `ok`
- [x] 后端停止后前端显示失败状态
- [x] 架构图、数据流图和 API 清单存在
- [x] Git 状态不包含敏感文件和依赖目录
- [x] 创建第一次有效 Git commit

目标目录：

```text
ownerblog/
├─ backend/
├─ frontend/
├─ docs/
│  └─ development-specification.md
├─ README.md
└─ .gitignore
```



## 今天需要学习的最小知识

只学习以下内容，遇到其他框架知识先记录，不在今天展开：


| 学习内容               | 学到什么程度                  | 必须产生的结果                            |
| ------------------ | ----------------------- | ---------------------------------- |
| Git 基础             | 能初始化、查看状态、提交代码          | 第一次可恢复提交                           |
| Python 虚拟环境        | 能创建、激活和安装依赖             | 后端独立运行环境                           |
| Django 项目和 App     | 理解项目配置与业务 App 的区别       | 创建 `config`、`articles`、`knowledge` |
| Django URL 和 View  | 能把一个 URL 映射到返回 JSON 的函数 | `GET /api/health`                  |
| Node.js、npm 和 Vite | 理解前端开发服务器、脚本和入口文件       | Vue 项目可以启动                         |
| Vue 单文件组件          | 能修改模板并显示数据              | 页面显示后端健康状态                         |
| Axios              | 能发起一次 GET 请求并处理成功/失败    | 前端请求 health API                    |
| 环境变量               | 知道密钥和服务地址不应写死           | 创建 `.env.example`                  |




## 设计任务

- [x] 写明 Phase 1 的核心闭环和不做清单
- [x] 画 1 张系统架构图
- [x] 画 1 张文章发布到问答的数据流图
- [x] 确认 `accounts`、`articles`、`comments`、`knowledge` 的职责
- [x] 确认匿名访问状态、普通用户和管理员权限矩阵；开发者维护身份不纳入产品角色
- [x] 确认 Article、Comment、ArticleChunk、User 和审核审计的最小字段与状态机
- [x] 确认认证、文章、评论、审核和知识库问答 API 的方法、路径、用途和角色要求
- [x] 确认只有审核通过且索引成功的文章公开并进入 RAG
- [x] 确认今天不实现注册、登录、文章/评论模型、Admin 审核、RAG 和业务页面



## 骨架开发任务

- [x] 初始化 Git 仓库并创建 `.gitignore`
- [x] 创建 Python 虚拟环境
- [x] 创建 Django 项目和基础目录
- [x] 创建 `accounts`、`articles`、`comments`、`knowledge` App 骨架；完整认证和业务权限放后续阶段
- [x] 创建 `GET /api/health`，返回 JSON：`{"status":"ok"}`
- [x] 创建 Vue 3 + Vite 项目
- [x] 创建一个最小页面，使用 Axios 请求 health API
- [x] 配置 Vite 开发代理或 Django CORS，但只选择一种方式
- [x] 创建 `.env.example`，不得写入真实 API Key
- [x] 提交架构文档和第一次可运行代码



## Day 1 可量化验收标准

全部满足才算 Day 1 完成：

- [x] 产出 1 张架构图、1 张数据流图和 1 份 API 清单
- [x] 架构图明确 Vue、Django、SQLite、Chroma 和模型服务的关系
- [x] API 清单至少包含 3 个接口，且写明方法和路径
- [x] `python manage.py check` 执行成功
- [x] Django 开发服务器可以启动
- [x] `GET /api/health` 返回 HTTP `200`
- [x] Vue/Vite 开发服务器可以启动
- [x] 浏览器页面成功显示后端返回的 `ok`
- [x] 主动停止后端时，前端能显示请求失败状态
- [x] `git status` 不包含 `.env`、虚拟环境和 `node_modules`
- [x] 至少有 1 个 Git commit，提交内容可以重新运行
- [x] 不依赖 AI 逐字解释，也能用自己的话说明一次请求链路



## Day 1 时间约束

确定性任务最多占当天可用时间的 70%，至少 30% 保留给环境安装、依赖冲突、文档查阅和调试。建议按以下顺序：

1. 60-90 分钟：范围、架构图、数据流和 API 清单。
2. 90-120 分钟：Django、Python 环境和 health API。
3. 60-90 分钟：Vue、Vite 和 Axios 页面。
4. 剩余时间：排错、整理目录、提交代码和记录问题。



## Day 1 明确边界

今天禁止为了“顺手”提前做以下内容：

- 注册、登录、Session/CSRF 联调和业务权限实现
- Article、Category、Tag、Comment、ArticleChunk 数据模型和 migration
- Django Admin 审核配置和管理员业务账号流程
- 文章/评论 CRUD、审核、下架和删除
- Markdown 编辑器
- Chroma、embedding 和 GPT 调用
- UI 组件库和页面美化
- Docker、PostgreSQL、Redis 和部署

如果前后端骨架或 health API 遇到问题，优先解决环境和启动问题，不通过增加业务代码掩盖基础问题。今天的交付物是“设计完成、骨架可运行”，不是“功能越多越好”。