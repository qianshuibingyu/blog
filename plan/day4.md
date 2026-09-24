# Day 4 实操手册：文章审核与 Django Admin 审核流程

> 阅读规则：代码示例中的注释说明每一行“做什么”；紧跟代码的文字说明“为什么这样做”。遇到没有注释的命令或 JSON，先看其上一行的目标说明，不要把示例代码当成黑盒直接复制。

本手册必须从上到下执行。每一步都说明：

```text
1. 打开哪个文件
2. 修改什么内容
3. 为什么修改
4. 执行什么命令
5. 预期看到什么
6. 出错时检查什么
```

不要跳过验证直接进入下一步。

> **先确认你打开的是哪一份文件**：本文只对应 `E:\Desktop\VibeCoding\ownerblog`。在 Cursor 中请使用“文件 -> 打开文件”，输入完整路径 `E:\Desktop\VibeCoding\ownerblog\plan\day4.md`。不要打开 `E:\Desktop\VibeCoding\Django+FastAPI\plan\day4.md`；那是另一个项目的同名文件，内容是登录和数据隔离。`.gitignore` 只决定 Git 是否跟踪文件，不会决定 Cursor 显示哪一个本地文件。

## Day 4 阶段总览

```text
阶段 0       启动项目并确认 Day 3 没有回归
阶段 1       根据官方文档理解今天会用到的概念
阶段 2       修改 Article 模型
阶段 3       创建 ModerationEvent 和 Notification
阶段 4       完善 ArticleChunk
阶段 5       生成并执行 migration
阶段 6       编写审核 Service
阶段 7       接入 Django Admin
阶段 8       修正 Serializer 和公开 API
阶段 9       手动验证审核流程
阶段 10      补充自动化测试
阶段 11      复盘、提交和最终验收
```

今天只完成文章审核后端基础，不实现 Chroma 写入、Embedding、GPT、评论和 Vue 管理后台。

## 0. 项目启动

### 0.1 启动后端

打开 PowerShell：

```powershell
# 进入 Django 项目目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 启动 Django 开发服务器。
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

预期：

```text
Starting development server at http://127.0.0.1:8000/
```

### 0.2 启动前端

另开 PowerShell：

```powershell
# 进入 Vue 项目目录。
cd E:\Desktop\VibeCoding\ownerblog\frontend

# 启动 Vite 开发服务器。
pnpm dev
```

预期地址：

```text
http://localhost:5173
```

### 0.3 验证 Day 3 基线

再开 PowerShell：

```powershell
# 进入后端目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 检查 Django 配置。
.\.venv\Scripts\python.exe manage.py check

# 运行现有后端测试。
.\.venv\Scripts\python.exe manage.py test

# 检查迁移是否完整。
.\.venv\Scripts\python.exe manage.py makemigrations --check

# 进入前端目录。
cd ..\frontend

# 检查前端构建。
pnpm build
```

浏览器确认：

```text
http://127.0.0.1:8000/api/articles -> 返回 200
http://localhost:5173/ -> 文章列表可以打开
http://localhost:5173/my-articles -> 登录后可以打开
```

如果基线失败，先回到 day3.md 对应章节修复，不要继续 Day 4。

### 0.4 确认本次修改的文件

在开始改代码前，打开下面这些**绝对路径**。没有的文件按本文后续步骤创建，不要在另一个项目中创建：

```text
E:\Desktop\VibeCoding\ownerblog\backend\articles\models.py
E:\Desktop\VibeCoding\ownerblog\backend\articles\serializers.py
E:\Desktop\VibeCoding\ownerblog\backend\articles\views.py
E:\Desktop\VibeCoding\ownerblog\backend\articles\tests.py
E:\Desktop\VibeCoding\ownerblog\backend\articles\admin.py
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\models.py
E:\Desktop\VibeCoding\ownerblog\backend\config\settings.py
```

每次修改前先看 Cursor 顶部标签页显示的完整路径。若标签页只显示 `day4.md`，把鼠标放在标签上即可看到完整路径；路径不是 `ownerblog` 时关闭该标签，不要继续复制代码。

## 1. 官方文档结论和概念

本节已经根据官方文档总结出今天要用的规则，不要求你自己阅读后再推理。

### 1.1 Model 和 choices

官方文档：[Django Models](https://docs.djangoproject.com/zh-hans/5.2/topics/db/models/)

Model 是 Python 类和数据库表之间的映射。字段会变成数据库列，Model 实例代表一条数据。

choices 用来限制字段可选值。数据库保存稳定的英文值，Admin 显示可读名称。因此文章状态集中写在 ArticleStatus 中，而不是在多个文件里直接写字符串。

### 1.2 ForeignKey

ForeignKey 表示两张表之间的关系：

```text
Article.author          -> 文章作者
Article.reviewed_by     -> 最近审核管理员
Notification.recipient -> 通知接收人
```

审核人使用 SET_NULL，是因为管理员账号删除后，文章历史不应该被删除。作者关系继续保留现有保护策略，因为作者决定文章所有权。

### 1.3 Migration

官方文档：[Django Migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/)

```text
修改 models.py
    -> makemigrations
    -> 生成迁移文件
    -> migrate
    -> 数据库增加新字段和新表
```

makemigrations 只生成迁移文件，migrate 才真正修改 SQLite。只改 Model 不执行 migrate，访问新字段时会出现 no such column。

### 1.4 Admin Action

官方文档：[Django Admin](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/) 和 [Django Admin Actions](https://docs.djangoproject.com/zh-hans/5.2/ref/contrib/admin/actions/)

ModelAdmin 控制 Admin 页面如何显示和筛选数据。Admin Action 是管理员对选中数据执行的动作。

审核不能只让管理员把 status 改成 published，因为通过操作还需要：

```text
检查管理员身份
检查当前状态
记录审核人和审核时间
写入 ModerationEvent
进入 indexing
```

官方文档还说明默认批量删除可能不会调用模型自定义 delete，所以本项目逐条调用 Service。

### 1.5 transaction.atomic

官方文档：[Django Transactions](https://docs.djangoproject.com/zh-hans/5.2/topics/db/transactions/)

transaction.atomic 可以把多次数据库操作变成一个整体。全部成功才提交，发生异常则回滚。

驳回动作包含：

```text
写入审核事件
写入作者通知
删除文章
```

三件事必须一起成功。

### 1.6 权限和测试

官方文档：[DRF Permissions](https://www.django-rest-framework.org/api-guide/permissions/) 和 [Django Testing](https://docs.djangoproject.com/zh-hans/5.2/topics/testing/)

认证回答“你是谁”，权限回答“你能做什么”。前端隐藏按钮不是安全措施，后端 Service 和 API 必须再次检查权限。

TestCase 使用隔离测试数据库。refresh_from_db 让测试对象重新读取数据库中的真实状态。

## 2. 文章状态设计

### 2.1 Article.status

```text
draft -> pending_review -> indexing -> published
indexing -> index_failed -> indexing
published -> offline
```

普通用户的“发布”只是提交审核。管理员通过后也不能直接公开，必须等待后续索引服务完成。

### 2.2 Article.index_status

```text
not_indexed -> indexing -> indexed
indexing -> failed
indexed -> stale
```

status 表示业务审核结果，index_status 表示知识库索引结果，两者不能合并。

### 2.3 公开门禁

列表和详情都必须同时检查：

```text
status = published
index_status = indexed
```

因此下面所有数据都不公开：

```text
draft
pending_review
indexing
index_failed
published + not_indexed
offline
```

## 3. 修改 Article 模型

### 3.1 打开文件

打开：

```text
backend/articles/models.py
```

保留现有 Article 的 author、title、summary、content、created_at 和 updated_at。

### 3.2 替换 ArticleStatus

找到现有 ArticleStatus 类，整体替换为：

```python
# 定义文章业务生命周期。
class ArticleStatus(models.TextChoices):
    # 作者正在编辑。
    DRAFT = "draft", "草稿"
    # 作者已经提交审核。
    PENDING_REVIEW = "pending_review", "待审核"
    # 管理员通过后等待索引。
    INDEXING = "indexing", "索引中"
    # 索引失败，文章仍然不能公开。
    INDEX_FAILED = "index_failed", "索引失败"
    # 只有审核通过且索引成功后才可以公开。
    PUBLISHED = "published", "已发布"
    # 管理员下架过程中的状态。
    OFFLINE = "offline", "已下架"


# 定义文章索引生命周期。
class IndexStatus(models.TextChoices):
    # 文章还没有建立索引。
    NOT_INDEXED = "not_indexed", "未索引"
    # 索引服务正在处理。
    INDEXING = "indexing", "索引中"
    # 索引已经成功写入向量库。
    INDEXED = "indexed", "已索引"
    # embedding 或 Chroma 操作失败。
    FAILED = "failed", "失败"
    # 正文变化后旧索引已经过期。
    STALE = "stale", "过期"
```

不要删除文件顶部已有的 settings、models 和 timezone 导入。

### 3.3 增加 Article 字段

找到 Article 类现有的 published_at。删除旧的 published_at，把下面代码放在 Article 类内部。

这是“字段替换”，不是把代码粘到文件末尾：`published_at` 只能保留一份。下面代码必须缩进 4 个空格，与原来的 `title`、`content` 字段处于同一层级；不要放进 `ArticleStatus` 类，也不要放进 `Meta` 类：

```python
    # 记录作者提交审核的时间。
    submitted_at = models.DateTimeField(null=True, blank=True)
    # 记录最近一次管理员审核的时间。
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # 记录文章第一次公开的时间。
    published_at = models.DateTimeField(null=True, blank=True)
    # 记录文章下架的时间。
    taken_down_at = models.DateTimeField(null=True, blank=True)
    # 记录最近审核文章的管理员。
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_articles",
    )
    # 记录执行下架操作的管理员。
    taken_down_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="taken_down_articles",
    )
    # 保存驳回或下架原因。
    moderation_reason = models.TextField(blank=True)
    # 保存索引状态，不能为 NULL。
    index_status = models.CharField(
        max_length=20,
        choices=IndexStatus.choices,
        default=IndexStatus.NOT_INDEXED,
    )
    # 记录索引正在执行哪一步。
    index_step = models.CharField(max_length=20, default="pending")
    # 保存整体索引错误。
    index_error = models.TextField(blank=True)
    # 保存 embedding 错误。
    embedding_error = models.TextField(blank=True)
    # 保存 Chroma 错误。
    chroma_error = models.TextField(blank=True)
    # 记录索引完成时间。
    indexed_at = models.DateTimeField(null=True, blank=True)
    # 保存正文哈希。
    content_hash = models.CharField(max_length=64, blank=True)
    # 保存索引版本。
    version = models.PositiveIntegerField(default=1)
```

### 3.4 增加 ModerationEvent

在 models.py 文件末尾增加。这里是“追加”：把下面整个类放在 `Article` 类结束之后，不能嵌套在 `Article` 内。文件末尾的 `ModerationEvent` 仍然属于 `articles` App，所以 Service 用 `.models` 导入它：

```python
# 保存文章和评论的审核操作历史。
class ModerationEvent(models.Model):
    # 保存对象类型，例如 article 或 comment。
    object_type = models.CharField(max_length=30)
    # 保存对象 ID，原对象删除后仍可追踪。
    object_id = models.PositiveBigIntegerField()
    # 保存执行操作的管理员。
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="moderation_events",
    )
    # 保存操作名称。
    action = models.CharField(max_length=30)
    # 保存操作前状态。
    from_status = models.CharField(max_length=30, blank=True)
    # 保存操作后状态，删除时可以为空。
    to_status = models.CharField(max_length=30, blank=True)
    # 保存审核原因。
    reason = models.TextField(blank=True)
    # 保存事件创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 让 Admin 显示可读名称。
    def __str__(self):
        # 返回对象、ID 和动作。
        return f"{self.object_type}#{self.object_id} {self.action}"
```

### 3.5 检查模型语法

```powershell
# 进入后端目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 检查文章模型的 Python 语法。
.\.venv\Scripts\python.exe -m py_compile articles\models.py
```

预期：没有输出。

## 4. 创建 Notification

### 4.1 创建 App

当前项目没有 notifications App：

```powershell
# 确保当前目录是后端目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 创建站内通知 App。
.\.venv\Scripts\python.exe manage.py startapp notifications
```

打开 backend/config/settings.py，在 INSTALLED_APPS 中增加：

```python
# 注册站内通知 App。
"notifications",
```

具体位置：在现有的 `"knowledge",` 下一行追加，结果应是：

```python
    # Day 3 已有的知识库 App。
    "knowledge",
    # Day 4 新增的站内通知 App；不注册它，迁移和 Service 都找不到 Notification。
    "notifications",
```

保存后立刻执行下面的检查。这里先检查再继续，是为了避免后面出现“找不到 notifications 应用”的连锁错误：

```powershell
# 进入后端目录，确保 manage.py 使用的是当前项目配置。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 让 Django 加载 INSTALLED_APPS 并检查 notifications 是否注册成功。
.\.venv\Scripts\python.exe manage.py check
```

预期：`System check identified no issues (0 silenced)。`

如果提示 `No module named notifications`，说明 `startapp notifications` 没有在 `backend` 目录执行；如果提示模型未找到，确认 `notifications/models.py` 已按下一小节替换。

### 4.2 替换通知模型

打开：

```text
backend/notifications/models.py
```

将整个文件替换为：

```python
# 导入项目配置的用户模型。
from django.conf import settings
# 导入数据库模型。
from django.db import models


# 保存用户看到的站内系统通知。
class Notification(models.Model):
    # 指定通知接收人。
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    # 保存通知类型。
    type = models.CharField(max_length=50)
    # 保存通知标题。
    title = models.CharField(max_length=200)
    # 保存结果说明，不保存文章正文。
    message = models.TextField()
    # 标记通知是否已读。
    is_read = models.BooleanField(default=False)
    # 保存创建时间。
    created_at = models.DateTimeField(auto_now_add=True)

    # 让 Admin 显示通知名称。
    def __str__(self):
        # 返回接收人和标题。
        return f"{self.recipient} - {self.title}"
```

### 4.3 检查

```powershell
# 检查通知模型语法。
.\.venv\Scripts\python.exe -m py_compile notifications\models.py

# 检查 App 注册。
.\.venv\Scripts\python.exe manage.py check
```

## 5. 完善 ArticleChunk

打开：

```text
backend/knowledge/models.py
```

将整个文件替换为：

```python
# 导入文章模型。
from articles.models import Article
# 导入数据库模型。
from django.db import models


# 保存清洗后的文章片段和向量文档映射。
class ArticleChunk(models.Model):
    # 每个片段属于一篇文章。
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    # 保存片段在文章中的顺序。
    chunk_index = models.PositiveIntegerField()
    # 保存清洗后的文本片段。
    content = models.TextField()
    # 索引完成前允许没有向量 ID。
    vector_document_id = models.CharField(max_length=200, blank=True)
    # 保存片段创建时间。
    created_at = models.DateTimeField(auto_now_add=True)
    # 保存片段更新时间。
    updated_at = models.DateTimeField(auto_now=True)

    # 定义数据库级联合唯一约束。
    class Meta:
        # 同一篇文章不能有两个相同序号的片段。
        constraints = [
            # 将文章和片段序号组合成唯一键。
            models.UniqueConstraint(
                fields=["article", "chunk_index"],
                name="unique_article_chunk_index",
            ),
        ]
```

## 6. 生成并执行 migration

```powershell
# 只为本次改动涉及的三个 App 生成迁移，避免误把无关改动混入 Day 4。
.\.venv\Scripts\python.exe manage.py makemigrations articles knowledge notifications

# 将迁移应用到 SQLite 数据库。
.\.venv\Scripts\python.exe manage.py migrate

# 查看迁移执行状态。
.\.venv\Scripts\python.exe manage.py showmigrations

# 检查模型和 Admin。
.\.venv\Scripts\python.exe manage.py check

# 确认没有遗漏的模型变化。
.\.venv\Scripts\python.exe manage.py makemigrations --check
```

预期：

- 新模型对应的 migration 已生成。
- migrate 中显示 OK。
- showmigrations 中新增迁移前是 [X]。
- check 和 makemigrations --check 成功。

如果出现 no such column，先执行 migrate；如果没有生成 notifications 迁移，检查 settings.py 是否注册 notifications。

## 7. 编写审核 Service

### 7.1 新建 services.py

打开：

```text
backend/articles/services.py
```

新建文件并完整复制：

```python
# 导入事务工具。
from django.db import transaction
# 导入时区工具。
from django.utils import timezone
# 导入通知模型。
from notifications.models import Notification
# 导入文章片段模型。
from knowledge.models import ArticleChunk
# 导入文章状态、索引状态和审核事件。
from .models import ArticleStatus, IndexStatus, ModerationEvent


# 检查操作者是否为管理员。
def ensure_admin(actor):
    # 未登录或不是 staff 的用户不能审核。
    if not actor.is_authenticated or not actor.is_staff:
        # 在数据库写入前阻止操作。
        raise PermissionError("只有管理员可以审核文章。")


# 清理文章数据库中的索引映射。
def cleanup_article_resources(article):
    # 删除文章对应的片段。
    ArticleChunk.objects.filter(article=article).delete()
    # Day 5 再增加 Chroma 文档清理。


# 管理员通过待审核文章。
@transaction.atomic
def approve_article(*, article, actor):
    # 检查管理员身份。
    ensure_admin(actor)
    # 只有待审核文章可以通过。
    if article.status != ArticleStatus.PENDING_REVIEW:
        # 拒绝非法状态转换。
        raise ValueError("只有待审核文章可以通过。")
    # 保存旧状态供审计使用。
    old_status = article.status
    # 进入索引流程，不能直接公开。
    article.status = ArticleStatus.INDEXING
    # 标记索引正在处理。
    article.index_status = IndexStatus.INDEXING
    # 保存审核管理员。
    article.reviewed_by = actor
    # 保存审核时间。
    article.reviewed_at = timezone.now()
    # 保存本次修改字段。
    article.save(
        update_fields=[
            "status",
            "index_status",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ],
    )
    # 保存审核历史。
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article.id,
        actor=actor,
        action="approve",
        from_status=old_status,
        to_status=article.status,
    )
    # 返回更新后的文章。
    return article


# 管理员驳回文章，文章直接删除。
@transaction.atomic
def reject_article(*, article, actor, reason):
    # 检查管理员身份。
    ensure_admin(actor)
    # 只有待审核文章可以驳回。
    if article.status != ArticleStatus.PENDING_REVIEW:
        # 拒绝非法状态转换。
        raise ValueError("只有待审核文章可以驳回。")
    # 在删除前保存文章 ID。
    article_id = article.id
    # 在删除前保存文章作者。
    author = article.author
    # 写入驳回审核记录。
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article_id,
        actor=actor,
        action="reject",
        from_status=article.status,
        to_status="",
        reason=reason,
    )
    # 创建作者通知。
    Notification.objects.create(
        recipient=author,
        type="article_rejected",
        title="文章未通过审核",
        message="你的文章未通过审核，原文章已被删除。",
    )
    # 清理文章片段。
    cleanup_article_resources(article)
    # 删除文章。
    article.delete()


# 管理员下架已经公开的文章。
@transaction.atomic
def take_down_article(*, article, actor, reason):
    # 检查管理员身份。
    ensure_admin(actor)
    # 只有已发布文章可以下架。
    if article.status != ArticleStatus.PUBLISHED:
        # 拒绝非法状态转换。
        raise ValueError("只有已发布文章可以下架。")
    # 保存文章 ID。
    article_id = article.id
    # 写入下架审核记录。
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article_id,
        actor=actor,
        action="offline",
        from_status=article.status,
        to_status=ArticleStatus.OFFLINE,
        reason=reason,
    )
    # 通知作者。
    Notification.objects.create(
        recipient=article.author,
        type="article_offline",
        title="文章已下架",
        message="你的文章已被管理员下架。",
    )
    # 清理数据库片段。
    cleanup_article_resources(article)
    # 硬删除文章。
    article.delete()
```

### 7.2 检查 Service

```powershell
# 编译审核服务。
.\.venv\Scripts\python.exe -m py_compile articles\services.py
```

预期：没有输出。

## 8. 配置 Django Admin

Admin 是 Django 自带的后台管理界面。它适合管理员审核数据，不是给普通用户使用的前端页面。本文的三个 Action 会调用前面写好的 Service，因此状态检查、审计记录、通知和片段清理不会被绕过。

### 8.1 替换 articles/admin.py

打开 backend/articles/admin.py，将整个文件替换为：

```python
# 导入 Django Admin。
from django.contrib import admin
# 导入审核服务。
from .services import approve_article, reject_article, take_down_article
# 导入文章和审核事件。
from .models import Article, ModerationEvent


# 注册文章 Admin。
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    # 显示文章、作者、业务状态、索引状态和审核时间。
    list_display = (
        "title",
        "author",
        "status",
        "index_status",
        "reviewed_at",
        "updated_at",
    )
    # 提供状态筛选。
    list_filter = ("status", "index_status")
    # 提供标题和作者搜索。
    search_fields = ("title", "author__username")
    # 服务端字段只读。
    readonly_fields = (
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
        "published_at",
        "taken_down_at",
        "reviewed_by",
        "taken_down_by",
        "index_status",
        "index_step",
        "index_error",
        "embedding_error",
        "chroma_error",
        "indexed_at",
        "content_hash",
        "version",
    )
    # 注册审核操作。
    actions = (
        "approve_selected",
        "reject_selected",
        "take_down_selected",
    )

    # 通过选中的待审核文章。
    @admin.action(description="通过选中的待审核文章")
    def approve_selected(self, request, queryset):
        # 逐篇调用服务，不能直接 queryset.update。
        for article in queryset:
            # Service 会检查状态和管理员身份。
            approve_article(article=article, actor=request.user)
        # 显示操作结果。
        self.message_user(request, "文章已进入索引流程。")

    # 驳回选中的待审核文章。
    @admin.action(description="驳回选中的待审核文章")
    def reject_selected(self, request, queryset):
        # 逐篇调用服务，保证审计和通知完整。
        for article in queryset:
            # 读取管理员填写的处理原因。
            reason = article.moderation_reason or "文章未通过审核。"
            # Service 会写审计、写通知并删除文章。
            reject_article(
                article=article,
                actor=request.user,
                reason=reason,
            )
        # 显示操作结果。
        self.message_user(request, "文章已驳回并删除。")

    # 下架选中的已发布文章。
    @admin.action(description="下架选中的已发布文章")
    def take_down_selected(self, request, queryset):
        # 逐篇调用服务，保证关联数据被清理。
        for article in queryset:
            # 读取管理员填写的处理原因。
            reason = article.moderation_reason or "文章已被管理员下架。"
            # Service 会写审计、写通知并删除文章。
            take_down_article(
                article=article,
                actor=request.user,
                reason=reason,
            )
        # 显示操作结果。
        self.message_user(request, "文章已下架。")


# 注册审核历史。
@admin.register(ModerationEvent)
class ModerationEventAdmin(admin.ModelAdmin):
    # 显示对象、动作、操作者和状态变化。
    list_display = (
        "object_type",
        "object_id",
        "action",
        "actor",
        "from_status",
        "to_status",
        "created_at",
    )
    # 提供筛选。
    list_filter = ("object_type", "action")
    # 审计历史只允许查看。
    readonly_fields = tuple(
        field.name for field in ModerationEvent._meta.fields
    )
```

### 8.2 替换 notifications/admin.py

打开 backend/notifications/admin.py，将整个文件替换为：

```python
# 导入 Django Admin。
from django.contrib import admin
# 导入通知模型。
from .models import Notification


# 注册通知，方便检查审核结果。
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # 显示接收人、类型、标题、已读状态和时间。
    list_display = (
        "recipient",
        "type",
        "title",
        "is_read",
        "created_at",
    )
    # 提供通知筛选。
    list_filter = ("type", "is_read")
    # 创建时间只读。
    readonly_fields = ("created_at",)
```

### 8.3 使用审核原因的正确顺序

`reject_selected` 和 `take_down_selected` 是列表页批量操作，Django 默认不会弹出一个额外的“原因输入框”。因此原因必须先写入文章：

```text
1. 打开 Articles 列表。
2. 点击文章标题进入详情页。
3. 在 moderation_reason 字段填写原因并点击 Save。
4. 返回 Articles 列表，勾选刚才保存的文章。
5. 选择对应 Action 并点击 Go。
```

如果没有填写原因，Service 会使用代码里的默认原因；这不会阻止操作，但审计记录中的原因会不够具体。

### 8.4 检查 Admin

```powershell
# 检查 Admin 字段和模型注册。
.\.venv\Scripts\python.exe manage.py check
```

浏览器打开：

```text
http://127.0.0.1:8000/admin/
```

预期看到 Articles、Moderation events 和 Notifications。

## 9. 修正 Serializer 和公开 API

### 9.1 修改 MyArticleSerializer

打开 backend/articles/serializers.py。保留 ArticleListSerializer 和 ArticleDetailSerializer，只把 MyArticleSerializer 的 Meta 类替换为：

```python
    # 声明 Serializer 对应 Article 模型。
    class Meta:
        # 使用 Article 模型。
        model = Article
        # 返回作者页面需要的字段。
        fields = (
            "id",
            "title",
            "summary",
            "content",
            "status",
            "created_at",
            "updated_at",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "index_status",
            "index_step",
        )
        # 这些字段只能由后端决定。
        read_only_fields = (
            "id",
            "status",
            "created_at",
            "updated_at",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "index_status",
            "index_step",
        )
```

read_only_fields 只是输入保护，View 仍然必须使用当前用户设置 author，Service 仍然必须检查管理员。

### 9.2 修改 articles/views.py

把导入：

```python
# 导入文章模型和文章状态。
from .models import Article, ArticleStatus
```

替换为：

```python
# 导入文章模型、文章状态和索引状态。
from .models import Article, ArticleStatus, IndexStatus
```

在 ArticleCollectionAPIView.get 中，把查询替换为：

```python
# 只返回已发布且索引完成的文章。
articles = Article.objects.filter(
    status=ArticleStatus.PUBLISHED,
    index_status=IndexStatus.INDEXED,
)
```

在 ArticleItemAPIView.get 中，把查询替换为：

```python
# 详情接口使用和列表接口相同的公开门禁。
article = get_object_or_404(
    Article.objects.filter(
        status=ArticleStatus.PUBLISHED,
        index_status=IndexStatus.INDEXED,
    ),
    pk=pk,
)
```

不要给 MyArticleListAPIView 加公开门禁，否则作者看不到自己的草稿。

检查：

```powershell
# 编译 Serializer。
.\.venv\Scripts\python.exe -m py_compile articles\serializers.py

# 编译 View。
.\.venv\Scripts\python.exe -m py_compile articles\views.py

# 运行文章测试。
.\.venv\Scripts\python.exe manage.py test articles
```

## 10. 手动验证

### 10.1 创建管理员

```powershell
# 进入后端目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 创建 Django Admin 管理员。
.\.venv\Scripts\python.exe manage.py createsuperuser
```

### 10.2 普通用户验证

1. 登录普通用户。
2. 打开 /my-articles。
3. 创建文章，确认状态是 draft。
4. 提交审核，确认状态是 pending_review。
5. 确认待审核文章没有编辑按钮。

在浏览器 Console 执行下面完整请求，验证两件事：请求通过 CSRF 校验，并且服务端不会接受客户端伪造的 `author` 和 `status`。原来只写 `fetch` 而没有 CSRF 请求头时，返回 `403` 是 Django 的正常拦截结果，不是本步骤的成功结果。

```javascript
// 读取当前网站 Cookie 中的指定名称。
function getCookie(name) {
  // Cookie 使用分号分隔，不使用逗号分隔。
  const cookies = document.cookie.split("; ");
  // 逐个检查 Cookie。
  for (const cookie of cookies) {
    // 将 Cookie 拆成名称和值。
    const [key, ...valueParts] = cookie.split("=");
    // 找到目标 Cookie 后返回解码后的值。
    if (key === name) {
      return decodeURIComponent(valueParts.join("="));
    }
  }
  // 没有找到 Cookie 时返回 null。
  return null;
}

// 读取 Django 之前设置的 CSRF Cookie。
const csrfToken = getCookie("csrftoken");

// 发送创建文章请求并等待结果。
fetch("/api/articles", {
  // 创建文章使用 POST。
  method: "POST",
  // JSON 声明请求体格式；X-CSRFToken 通过 Django 的 CSRF 校验。
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken,
  },
  // 携带登录后的 sessionid Cookie。
  credentials: "include",
  // 故意提交错误 author 和 published 状态。
  body: JSON.stringify({
    title: "状态伪造测试",
    summary: "测试摘要",
    content: "# 测试正文",
    author: 999999,
    status: "published",
  }),
})
  // 同时读取 HTTP 状态码和 JSON 响应。
  .then(async (response) => {
    // 将服务器结果打印出来，便于判断是 CSRF、登录还是业务校验问题。
    console.log("HTTP", response.status, await response.json());
  });
```

预期：

```text
HTTP 201
响应中的 author 是当前登录用户
响应中的 status 是 draft
响应中的 index_status 是 not_indexed
```

如果 `csrfToken` 是 `null`，先访问 `/api/auth/csrf`，刷新页面并重新登录；如果返回 `401`，说明 Session 没有携带；如果返回 `201` 但状态不是 `draft`，检查 `ArticleCollectionAPIView.post` 是否仍然使用 `status=ArticleStatus.DRAFT` 保存文章。

### 10.3 管理员通过文章

1. 打开 /admin/ 并登录管理员。
2. 进入 Articles。
3. 使用 status 筛选 pending_review。
4. 选择文章。
5. 执行“通过选中的待审核文章”。

预期：

```text
status = indexing
index_status = indexing
reviewed_by = 当前管理员
reviewed_at 不为空
存在 approve 审核记录
```

访问公开文章列表，确认文章仍不可见。这是预期结果，因为 Day 4 没有真实索引结果。

### 10.4 管理员驳回文章

1. 创建另一篇文章并提交审核。
2. 在 Admin 文章详情中填写 moderation_reason。
3. 保存文章。
4. 返回列表并选择文章。
5. 执行“驳回选中的待审核文章”。

预期：

```text
Article 已删除
ModerationEvent.action = reject
Notification.type = article_rejected
Notification.recipient = 原作者
```

### 10.5 管理员下架文章

准备一篇同时满足 published 和 indexed 的文章：

1. 在 Admin 中选择文章。
2. 填写下架原因。
3. 执行“下架选中的已发布文章”。
4. 访问公开文章列表。

预期文章从公开 API 消失，ArticleChunk 被清理，并生成 offline 审核事件和 article_offline 通知。

## 11. 自动化测试和最终检查

### 11.1 追加审核测试

打开 backend/articles/tests.py。保留原有测试，在文件顶部增加：

```python
# 导入通知模型。
from notifications.models import Notification
# 导入审核事件和索引状态。
from .models import ModerationEvent, IndexStatus
# 导入审核 Service。
from .services import approve_article, reject_article
```

把下面方法追加到现有 ArticleAPITests 类中：

```python
    # 验证管理员通过后文章进入索引流程。
    def test_admin_approve_moves_article_to_indexing(self):
        # 创建管理员。
        admin = get_user_model().objects.create_user(
            username="review-admin",
            password="password",
            is_staff=True,
        )
        # 把测试文章设置为待审核。
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        # 保存状态。
        self.draft_article.save()
        # 调用审核 Service。
        approve_article(
            article=self.draft_article,
            actor=admin,
        )
        # 重新读取数据库状态。
        self.draft_article.refresh_from_db()
        # 状态应该是 indexing。
        self.assertEqual(
            self.draft_article.status,
            ArticleStatus.INDEXING,
        )
        # 索引应该是 indexing。
        self.assertEqual(
            self.draft_article.index_status,
            IndexStatus.INDEXING,
        )
        # 审核人应该被记录。
        self.assertEqual(
            self.draft_article.reviewed_by,
            admin,
        )

    # 验证普通用户不能审核。
    def test_normal_user_cannot_approve_article(self):
        # 把测试文章设置为待审核。
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        # 保存状态。
        self.draft_article.save()
        # 普通用户调用审核 Service 应该失败。
        with self.assertRaises(PermissionError):
            # 使用普通用户执行审核。
            approve_article(
                article=self.draft_article,
                actor=self.user,
            )
        # 重新读取文章状态。
        self.draft_article.refresh_from_db()
        # 状态不能改变。
        self.assertEqual(
            self.draft_article.status,
            ArticleStatus.PENDING_REVIEW,
        )

    # 验证驳回会删除文章并通知作者。
    def test_reject_deletes_article_and_creates_notification(self):
        # 创建管理员。
        admin = get_user_model().objects.create_user(
            username="reject-admin",
            password="password",
            is_staff=True,
        )
        # 把测试文章设置为待审核。
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        # 保存状态。
        self.draft_article.save()
        # 保存文章 ID。
        article_id = self.draft_article.id
        # 调用驳回 Service。
        reject_article(
            article=self.draft_article,
            actor=admin,
            reason="需要补充技术细节",
        )
        # 文章应该被删除。
        self.assertFalse(
            Article.objects.filter(id=article_id).exists()
        )
        # 审核事件应该保留。
        self.assertTrue(
            ModerationEvent.objects.filter(
                object_id=article_id,
                action="reject",
            ).exists()
        )
        # 作者应该收到通知。
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user,
                type="article_rejected",
            ).exists()
        )
```

### 11.2 修正公开测试数据

打开 `backend/articles/tests.py`，先把导入行：

```python
from .models import Article, ArticleStatus
```

替换为：

```python
# 导入文章模型、业务状态和索引状态。
from .models import Article, ArticleStatus, IndexStatus
```

然后在 `setUp` 中找到 `self.published_article = Article.objects.create(` 这一段，在 `status=ArticleStatus.PUBLISHED,` 的下一行增加：

```python
# 已发布文章必须完成索引才能公开。
index_status=IndexStatus.INDEXED,
```

缩进要与 `status` 相同。完整结果应类似：

```python
# 创建一篇满足公开门禁的测试文章。
self.published_article = Article.objects.create(
    # 测试文章属于 setUp 创建的测试用户。
    author=self.user,
    # 测试列表和详情接口都会读取标题。
    title="已发布文章",
    # 测试列表接口会读取摘要。
    summary="已发布文章摘要",
    # 测试详情接口会读取正文。
    content="# 已发布文章正文",
    # 业务状态表示审核已通过并可公开。
    status=ArticleStatus.PUBLISHED,
    # Day 4 的公开门禁还要求索引已完成。
    index_status=IndexStatus.INDEXED,
)
```

否则新的公开门禁会把这篇测试文章正确过滤掉，`test_article_list_returns_only_published_article` 和详情测试会失败。注意：`draft_article` 不需要增加 `index_status`，它应继续使用默认值 `not_indexed`。

### 11.3 运行全部检查

```powershell
# 进入后端目录。
cd E:\Desktop\VibeCoding\ownerblog\backend

# 检查 Django 配置。
.\.venv\Scripts\python.exe manage.py check

# 检查迁移。
.\.venv\Scripts\python.exe manage.py makemigrations --check

# 运行全部后端测试。
.\.venv\Scripts\python.exe manage.py test

# 进入前端目录。
cd ..\frontend

# 构建前端。
pnpm build

# 返回项目根目录。
cd ..

# 检查差异中的空白错误。
git diff --check

# 查看最终工作区。
git status
```

预期：

```text
manage.py test -> OK
pnpm build -> built successfully
```

## 12. 复盘和最终验收

### 12.1 复盘问题

```text
1. 为什么 status 和 index_status 要分开？
2. 为什么管理员通过后只能进入 indexing？
3. 为什么驳回不保存 rejected 状态？
4. 为什么需要 ModerationEvent？
5. 为什么审核逻辑放在 Service？
6. 为什么驳回需要 transaction.atomic？
7. 为什么 readonly_fields 不能代替后端权限？
8. 为什么普通用户提交的 author 和 status 必须被忽略？
9. 为什么 ArticleChunk 需要联合唯一约束？
10. 为什么 published 文章还必须检查 index_status？
```

### 12.2 Day 4 最终标准

- [ ] Article 包含审核字段和索引字段。
- [ ] ArticleStatus 包含 draft、pending_review、indexing、index_failed、published 和 offline。
- [ ] IndexStatus 默认是 not_indexed 且不能为 NULL。
- [ ] ModerationEvent 可以记录审核操作。
- [ ] Notification 可以保存文章审核结果。
- [ ] ArticleChunk 有 article 和 chunk_index 联合唯一约束。
- [ ] 普通用户不能修改 author、status、审核字段和索引字段。
- [ ] 管理员通过文章后 status 和 index_status 都是 indexing。
- [ ] 驳回文章会删除 Article、保存审核记录并通知作者。
- [ ] 下架文章会清理 ArticleChunk 并从公开 API 消失。
- [ ] 公开 API 只返回 published + indexed 文章。
- [ ] Day 3 原有测试没有回归。
- [ ] manage.py check、迁移检查、后端测试和 pnpm build 全部通过。

### 12.3 提交

```powershell
# 确认没有提交环境变量、数据库和 Chroma 数据目录。
git status --short

# 提交 Day 4 的代码和手册。
git add backend frontend plan/day4.md
git commit -m "feat(moderation): add article review workflow"
```

Day 5 才从 indexing 继续实现 Markdown 清洗、切分、embedding、Chroma 写入和 published 状态。
