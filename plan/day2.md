# Phase 1 Day 2：文章基础功能与前后端联动

- 所属阶段：[Phase 1 基础版本计划](./phase1-mvp.md)
- 前置任务：[Day 1 需求、架构和骨架](./day1.md)
- 上级路线：[项目阶段规划](./project-plan.md)

## 1. 本日目标

今天不专门学习 Django，也不追求把某个框架学完，而是围绕文章功能推进项目：

```text
Article 数据模型
  -> SQLite 数据表
      -> Django Admin 管理文章
          -> 文章列表和详情 API
              -> Vue 前台展示
```

今天完成“文章创建、管理、读取和展示”的基础闭环。登录 API、文章写入 API、RAG 和问答暂不作为今天的必做项。

## 2. 今日工作量

建议安排 5-6 小时确定工作，额外预留 1-2 小时处理迁移、依赖、接口字段和前后端联调问题。

确定工作按以下优先级执行：

1. Article 模型和 SQLite 表
2. Django Admin 创建测试文章
3. 文章列表和详情 API
4. Vue 文章列表和详情展示
5. 测试、修复和提交

如果时间不足，必须保住前 3 项；Vue 页面可以只完成列表页，详情页顺延。

## 3. 今天边做边学习的内容


| 当前任务        | 只学习完成任务所需的知识                   | 代码产出              |
| ----------- | ------------------------------ | ----------------- |
| 创建 Article  | Django Model、字段和外键             | `Article` 模型      |
| 创建 SQLite 表 | Django migration 基本流程          | migration 文件和数据库表 |
| 管理文章        | Django Admin 注册、列表和搜索配置        | Admin 文章管理页       |
| 创建读取接口      | DRF API View、Serializer、状态码    | 列表和详情 API         |
| 展示文章        | Vue `ref`、`v-for`、Router、Axios | 列表和详情页面           |
| 联调          | JSON 字段、Network 和错误状态          | 前后端可运行闭环          |


不单独学习 Django、Vue 或 DRF 的完整体系；遇到不影响今天功能的概念先记录，不扩展学习范围。

## 4. Phase 拆分



### Phase 0：开始前检查和范围确认

目标：确认 Day 1 骨架可用，避免在错误环境上继续开发。

清单：

- [x] 阅读 Day 1 的目录、架构和 API 约定
- [x] 启动 Django 后端
- [x] 启动 Vue/Vite 前端
- [x] 执行 `python manage.py check`
- [x] 确认 `/api/health` 返回 HTTP 200
- [x] 确认今天只推进文章功能
- [x] 确认不实现登录 API、RAG、评论和审核 API

验收：前后端都能启动，health 接口仍然可用。

### Phase 1：Article 数据模型和数据库

目标：创建能够支撑文章列表、详情和后续索引的最小模型。

字段：

```text
id
author
title
summary
content
status: draft | published
created_at
updated_at
published_at
```

清单：

- [x] 在 `articles/models.py` 创建 Article
- [x] 配置标题、摘要、Markdown 正文字段
- [x] 配置草稿和已发布状态
- [x] 配置作者字段；如果登录尚未实现，允许使用测试用户或临时默认作者
- [x] 配置创建、更新时间和发布时间
- [x] 配置默认排序
- [x] 增加 `__str__`
- [x] 生成并检查 migration
- [x] 执行 `python manage.py migrate`
- [x] 执行 `python manage.py makemigrations --check`

验收标准：

- Article 表成功创建
- 新文章默认是 `draft`
- `published_at` 可以为空
- migration 可重复执行
- 模型中不写 API、Vue、Chroma 或 GPT 逻辑



### Phase 2：Django Admin 文章管理

目标：先拥有可用的内容管理入口，不开发 Vue 管理后台。

清单：

- [x] 在 `articles/admin.py` 注册 Article
- [x] 配置列表字段：标题、状态、作者、创建时间、更新时间
- [x] 配置标题搜索
- [x] 配置状态筛选
- [x] 配置时间字段只读或合理展示
- [x] 创建超级管理员
- [ ] 通过 `/admin/` 创建至少 2 篇草稿
- [x] 发布至少 1 篇文章
- [x] 修改一篇文章并观察更新时间
- [x] 验证草稿和已发布文章可以区分

验收标准：

- Admin 可以创建、编辑和删除文章
- 至少有 2 篇草稿、1 篇已发布文章
- 文章状态和内容保存正确
- 不实现 `/api/admin/*` 管理接口



### Phase 3：文章读取 API

目标：提供前台所需的最小只读接口。

接口：

```text
GET /api/articles
GET /api/articles/{id}
```

清单：

- [x] 创建 Article Serializer
- [x] 实现文章列表 API
- [x] 实现文章详情 API
- [x] 列表只返回 `published` 文章
- [x] 详情只允许读取 `published` 文章
- [x] 草稿访问返回 `404` 或统一的不存在响应
- [x] 文章不存在返回 `404`
- [x] 处理空列表
- [x] 验证 JSON 字段名称与前端约定一致
- [x] 使用 API 工具手动测试接口

验收标准：

- 列表能返回已发布文章
- 草稿不会出现在列表
- 详情能返回已发布文章正文
- 不存在和未公开文章不会泄露状态信息
- 接口不要求今天实现登录和 CSRF



### Phase 4：Vue 前台文章展示

目标：将 API 数据接入已有 Vue/Vite 骨架，完成最小页面。

页面：

```text
/                    文章列表
/articles/{id}       文章详情
```

清单：

- [x] 配置文章 API 请求文件
- [x] 创建文章列表页面
- [x] 使用 `ref` 管理列表、loading 和 error
- [x] 使用 `v-for` 展示文章卡片
- [x] 创建详情页面和路由参数
- [x] 使用 Axios 请求文章详情
- [x] 展示标题、摘要、正文和发布时间
- [x] 增加 loading 状态
- [x] 增加空列表状态
- [x] 增加请求失败状态
- [x] 增加基础返回首页入口
- [x] 暂不引入 UI 组件库和复杂样式

验收标准：

- 浏览器可以打开文章列表
- 点击文章可以进入详情
- 页面展示的数据来自 Django API，而不是前端硬编码
- 后端停止时页面显示失败提示
- 刷新详情页仍能根据 URL 获取文章



### Phase 5：联调、测试和复盘

目标：验证文章从 Admin 到前台的完整读取链路。

清单：

- [x] 在 Admin 新建一篇草稿，确认前台不可见
- [x] 将文章发布，确认前台可见
- [x] 修改文章，确认详情内容更新
- [ ] 删除文章，确认前台返回不存在
- [x] 同时准备草稿和已发布文章，确认列表过滤正确
- [x] 测试空列表状态
- [x] 测试错误 ID
- [x] 测试后端停止时的前端错误状态
- [x] 补充 Article 模型和读取 API 的基础测试
- [x] 更新 README 当前进度
- [x] 记录今天遇到的错误和解决方式
- [x] 提交 Git commit

建议提交信息：

```text
feat(articles): add article management and public read flow
```



## 5. Day 2 可量化验收标准

核心项全部完成才算 Day 2 完成：

- [x] `python manage.py check` 成功
- [x] Article 模型和 SQLite 表存在
- [x] `makemigrations --check` 成功
- [x] Admin 可以创建、编辑、发布和删除文章
- [ ] 数据库至少有 2 篇草稿和 1 篇已发布文章
- [x] `GET /api/articles` 返回已发布文章
- [x] `GET /api/articles/{id}` 返回已发布文章详情
- [x] 草稿不会出现在公开列表和详情中
- [x] Vue 列表页能显示 API 返回的文章
- [x] Vue 详情页能显示 API 返回的 Markdown 正文
- [x] 至少覆盖 4 个场景：已发布、草稿、不存在文章、空列表
- [x] 至少有 1 个 Git commit
- [x] 没有把文章数据硬编码到前端

当前复核结果：后端 `articles` 测试 4 个场景全部通过，`manage.py check` 和
`makemigrations --check` 均通过，前端 `pnpm build` 通过。当前数据库只有 1 篇已发布文章、
没有草稿，因此数量验收和删除流程需要重新进行人工验证。

## 8. 今日遇到的问题和解决方式

- 未激活后端虚拟环境时执行 `python manage.py` 会提示找不到 Django；进入 `backend` 后激活
  `.venv`，或直接使用 `.venv\Scripts\python.exe` 执行命令。
- 文章详情请求必须使用带斜杠的路径 `/api/articles/{id}/`，否则 Django 路由无法匹配。
- 前端文章页面不能依赖 mock 数据；关闭 `VITE_USE_MOCKS` 后，通过 Axios 请求 Django 文章 API，
  并分别处理 loading、空列表和请求失败状态。



## 6. 明确边界

今天不做：

- 不做注册、登录 API、Session/CSRF 和对象级权限
- 不做 `/my-articles` 写入页面；它放在登录和文章写入阶段
- 不做 `/api/admin/*` 审核 API；管理员继续使用 Django Admin
- 不做文章审核状态机
- 不做 Comment、Notification、分类标签管理
- 不做搜索、复杂分页和推荐
- 不接入 Chroma、Embedding、GPT、RAG 或 Agent
- 不做 Docker、PostgreSQL、Redis、Celery 和部署

如果时间不足，按以下顺序降级：

1. 保留 Article、SQLite、Admin 和公开读取 API。
2. Vue 只完成文章列表，详情页顺延。
3. 暂不补充样式，只保留 loading、空数据和错误状态。
4. 测试先保留已发布、草稿和不存在文章三个场景。



## 7. Day 2 完成后的下一步

下一阶段再处理：

1. 用户登录和 Session/CSRF。
2. `/my-articles` 和文章创建、编辑、删除 API。
3. 文章提交审核和 Django Admin 审核流程。
4. Chroma 索引和知识库问答。
