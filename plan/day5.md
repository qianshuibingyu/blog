# Phase 1 Day 5：文章索引实操手册

- 所属阶段：[Phase 1 基础版本计划](./phase1-mvp.md)
- 前置任务：[Day 4 文章审核与 Django Admin](./day4.md)
- 开始前预习：[Day 5 从 Markdown 到 Chroma 小白技术文档](../docs/day5-indexing-for-beginners.md)
- 本日上限：5 小时

> 阅读规则：严格按 Phase 顺序执行。每个 Phase 都说明打开哪个文件、修改什么、为什么修改、执行什么命令、预期看到什么。遇到错误先检查本 Phase 的“出错检查”，不要跳到后面的代码。

> 当前学习顺序调整：先完成文章编辑器、Markdown 格式按钮和预览功能。数据清洗、embedding、向量和 Chroma 暂缓学习，不作为当前编辑器功能的前置条件。正文仍然按 Markdown 原文保存；以后重新开始索引部分时，再从 Phase 1B 开始阅读。

## 1. 今天到底完成什么

Day 4 已经完成：

```text
管理员通过文章
  -> Article.status = indexing
  -> Article.index_status = indexing
```

Day 5 只把**一篇文章的首次索引成功路径**跑通：

```text
Article
  -> Markdown 原文输入和原样保存
  -> 安全渲染为网页内容
  -> 清洗 Markdown
  -> 段落切片
  -> embedding
  -> Chroma 写入
  -> ArticleChunk 写入
  -> published + indexed
  -> 检索到相关片段
```

今天不实现：

- GPT 问答接口和 Vue 问答页面。
- `rebuild_article_index` 管理命令。
- 删除/下架时的 Chroma 清理。
- 完整重试策略、重复索引和大规模召回评估。

今天必须补齐但不改变存储格式：

- 文章正文以 Markdown 原文保存到 `Article.content`。
- 普通用户使用文本编辑区输入 Markdown 源码；本日不做富文本/WYSIWYG 编辑器。
- 文章详情页把 Markdown 转为 HTML，并在 `v-html` 前执行安全过滤。
- Markdown 展示渲染和 Markdown 索引清洗是两条不同链路，不能用索引清洗结果覆盖原文。

本项目当前使用本地 embedding 模型；自动化测试仍使用假客户端，避免测试依赖模型文件加载和运行时间。远程 embedding 仍作为可选适配，不是本日默认路径。

## 2.0：先读官方文档，再开始实现

本日实现依赖多个外部组件。开始编码前，先阅读对应官方文档，并以文档中的 API 形状为准，不以旧教程或博客示例为准：

- [OpenAI Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)：embedding 用于把文本转换为向量；Python SDK 使用 `client.embeddings.create(input=..., model=...)`，批量输入后按返回项的 `index` 与原始片段对齐。文档还说明了模型的最大输入长度和 `dimensions` 参数，必须把它们纳入配置与测试约束。
- [OpenAI Embeddings API reference](https://developers.openai.com/api/reference/resources/embeddings)：核对请求字段、返回结构和 `data` 项结构。
- [Chroma Python Collection reference](https://docs.trychroma.com/reference/python/collection)：核对 `upsert`、`query`、`delete` 的 Python 参数和返回值。
- [Chroma Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)：确认查询使用 `query_embeddings` 时，查询向量维度必须和 collection 中已有向量一致，查询结果按输入查询分组返回。
- [Chroma Update Data](https://docs.trychroma.com/docs/collections/update-data)：确认 `upsert` 是“按 ID 新建或更新”，并理解同一个 ID 的幂等边界。
- [Django Database transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)：确认 `atomic()` 只管理 Django 数据库事务，`on_commit()` 回调只会在事务成功提交后执行，外部 Chroma 不会随数据库自动回滚。
- [Django Admin actions](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/actions/)：确认 Admin Action 应逐条调用业务服务，而不是用 `queryset.update()` 绕过审核事件和索引编排。

文档阅读后的实现结论：embedding 和 Chroma 都必须通过依赖注入测试；数据库状态只在本地事务中提交；外部向量写入失败必须记录失败阶段，并为后续补偿任务保留明确边界。

## 2. 五小时执行表

| 时间 | Phase | 交付物 |
| --- | --- | --- |
| 15 分钟 | 0 | Day 4 基线通过 |
| 45 分钟 | 1A | Markdown 原文输入、保存和安全展示 |
| 30 分钟 | 1B | 索引专用清洗和切片函数 |
| 35 分钟 | 2 | embedding 封装和假客户端 |
| 45 分钟 | 3 | Chroma 封装 |
| 60 分钟 | 4 | 索引 Service 成功/失败路径 |
| 25 分钟 | 5 | 接入管理员通过动作 |
| 25 分钟 | 6 | 检索和最小测试 |

超过预估时间时，按以下顺序降级：真实 API 调用、Chroma 清理、重复索引、完整测试。不得跳过索引成功后的状态验证。

## 3. Phase 0：启动并确认 Day 4 基线

### 本 Phase 官方文档

- [Django System checks](https://docs.djangoproject.com/en/5.2/topics/checks/)：理解 `manage.py check` 的用途。
- [Django Migrations](https://docs.djangoproject.com/en/5.2/topics/migrations/)：理解 `makemigrations --check` 与模型迁移状态检查。
- [Django Writing and running tests](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)：确认 `manage.py test` 的测试入口和隔离方式。

### 3.1 启动后端

打开 PowerShell：

```powershell
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check
.\.venv\Scripts\python.exe manage.py test
```

预期：`check`、迁移检查和测试全部成功。

### 3.2 检查 Day 4 文件

确认以下文件存在：

```text
E:\Desktop\VibeCoding\ownerblog\backend\articles\models.py
E:\Desktop\VibeCoding\ownerblog\backend\articles\services.py
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\models.py
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\tests.py
```

确认 `Article` 有 `status`、`index_status`、`index_step`、`index_error`、`embedding_error`、`chroma_error`、`indexed_at` 和 `content_hash`。

确认 `articles/services.py` 中的 `approve_article()` 目前只把文章设置为 `indexing`。这正是今天需要接入索引的位置。

## 4. Phase 1A：补齐 Markdown 正文闭环

### 本 Phase 官方文档

- [Marked 官方文档](https://marked.js.org/)：使用 `marked.parse()` 把 Markdown 源码转换为 HTML；官方明确说明 Marked 本身不负责清理不安全 HTML。
- [DOMPurify 官方文档](https://github.com/cure53/DOMPurify)：在把转换结果写入 DOM 前调用 `DOMPurify.sanitize()`。
- [Vue Security 官方文档](https://vuejs.org/guide/best-practices/security)：理解 `v-html` 会绕过 Vue 默认 HTML 转义，只能接收已经可信或消毒后的 HTML。

### 4.1 先确认存储契约

打开：

```text
backend/articles/models.py
backend/articles/serializers.py
frontend/src/views/MyArticlesView.vue
```

保持以下契约，不新增 `content_html` 字段，也不把 HTML 写回 `Article.content`：

```text
用户输入 Markdown 源码
  -> Article.content 原样保存
  -> API 返回 Markdown 原文
  -> 前端详情页临时转换为安全 HTML
```

`TextField` 不会验证 Markdown 语法；本日只约定内容格式，不把普通文本强行拒绝。后端不能为了展示而修改或清洗用户原文。

### 4.2 安装前端渲染依赖

打开 PowerShell：

```powershell
# 进入前端项目目录。
cd E:\Desktop\VibeCoding\ownerblog\frontend
# 安装 Markdown 解析器和 HTML 安全过滤器。
pnpm add marked dompurify
```

预期：`package.json` 和 `pnpm-lock.yaml` 增加依赖。

### 4.3 创建安全 Markdown 展示组件

创建：

```text
frontend/src/components/MarkdownContent.vue
```

写入最小实现：

```vue
<!-- 使用 Vue 的响应式计算能力，文章内容变化时自动重新渲染。 -->
<script setup>
// 导入 computed，根据 Markdown 原文计算展示 HTML。
import { computed } from "vue"
// 导入 Markdown 解析器，将 Markdown 转成 HTML。
import { marked } from "marked"
// 导入 HTML 消毒器，删除脚本和危险属性，避免 XSS。
import DOMPurify from "dompurify"

// 声明组件接收一个名为 source 的 Markdown 原文属性。
const props = defineProps({
  source: {
    // Article.content 是字符串，所以组件也要求字符串。
    type: String,
    // 没有正文时使用空字符串，避免解析 undefined。
    default: "",
  },
})

// source 改变时重新计算 HTML，供模板展示。
const renderedHtml = computed(() => {
  // 第一步：把 Markdown 语法转换为 HTML。
  const html = marked.parse(props.source || "")
  // 第二步：清除危险标签和属性。
  return DOMPurify.sanitize(html, {
    // 只保留普通 HTML，不启用 SVG 和 MathML。
    USE_PROFILES: { html: true },
  })
})
</script>

<template>
  <!-- 只把已经消毒的 HTML 写入页面，不能直接写入 API 原文。 -->
  <div class="markdown-content" v-html="renderedHtml"></div>
</template>
```

只允许这个组件使用 `v-html`。禁止直接把 API 返回的 `article.content` 绑定到 `v-html`，也禁止把 Markdown 字符串当作 Vue Template 编译。

这段代码的顺序不能调换：

```text
Markdown 原文 -> marked.parse() -> HTML -> DOMPurify.sanitize() -> v-html
```

`marked` 只负责语法转换，不负责安全过滤；`v-html` 会直接写入 HTML，所以必须先经过 `DOMPurify`。

### 4.4 接入文章详情页

打开：

```text
frontend/src/views/ArticleDetailView.vue
```

增加：

```vue
// 导入负责安全解析和展示 Markdown 的公共组件。
import MarkdownContent from "../components/MarkdownContent.vue"
```

把：

```vue
<div class="detail-body">
  <p>{{ article.content }}</p>
</div>
```

替换为：

```vue
<MarkdownContent :source="article.content" />
```

原文仍然通过 API 返回和保存；组件只在浏览器内生成展示 HTML。

### 4.5 增加作者预览入口

当前公共文章详情接口有公开门禁，只允许：

```text
status = published
index_status = indexed
```

这个门禁必须保留，不能为了预览而放开公共接口。作者需要一个独立的私有预览链路：

```text
/my-articles/:id/preview
  -> GET /api/my-articles/:id/preview
  -> 后端确认已登录且文章属于当前用户
  -> 返回该文章的 Markdown 原文
  -> MarkdownContent 安全渲染
```

打开：

```text
backend/articles/views.py
backend/config/urls.py
frontend/src/api/articles.js
frontend/src/main.js
frontend/src/views/MyArticlesView.vue
```

实现要求：

#### 4.5.1 后端预览接口

在 `backend/articles/views.py` 顶部确认导入：

```python
# get_object_or_404 负责在文章不存在或不属于当前用户时返回 404。
from django.shortcuts import get_object_or_404
# APIView 接收 HTTP 请求并返回 DRF Response。
from rest_framework.views import APIView
from rest_framework.response import Response
```

在文件末尾增加：

```python
class MyArticlePreviewAPIView(APIView):
    # GET /api/my-articles/<id>/preview：读取作者自己的文章原文。
    def get(self, request, pk):
        # 未登录用户不能进入作者私有预览。
        if not request.user.is_authenticated:
            return Response({"detail": "未登录"}, status=401)

        # 普通用户只能读取自己的文章；管理员可以读取任意文章。
        article_query = Article.objects.all()
        if not request.user.is_staff:
            article_query = article_query.filter(author=request.user)

        # 找不到文章或无权访问时统一返回 404，避免泄露文章存在性。
        article = get_object_or_404(article_query, pk=pk)
        # 返回 Markdown 原文，前端组件负责安全渲染。
        return Response(MyArticleSerializer(article).data)
```

这里不能复用 `ArticleItemAPIView`，因为公共详情接口必须继续执行 `published + indexed` 门禁；作者预览是另一条需要登录和归属校验的私有链路。

#### 4.5.2 注册后端 URL

在 `backend/config/urls.py` 的导入中增加：

```python
# 导入作者私有预览接口。
from articles.views import MyArticlePreviewAPIView
```

在 `urlpatterns` 中增加：

```python
path(
    "api/my-articles/<int:pk>/preview",
    MyArticlePreviewAPIView.as_view(),
    name="my-article-preview",
),
```

#### 4.5.3 增加前端 API 函数

在 `frontend/src/api/articles.js` 末尾增加：

```javascript
// 获取当前用户有权预览的文章 Markdown 原文。
export async function getMyArticlePreview(id) {
  // Session Cookie 会由 apiClient 自动携带。
  const { data } = await apiClient.get(`/my-articles/${id}/preview`)
  // 返回文章对象，包含 content、title、summary 和 status。
  return data
}
```

#### 4.5.4 创建预览页面

创建：

```text
frontend/src/views/MyArticlePreviewView.vue
```

写入：

```vue
<script setup>
// 页面挂载时加载文章预览数据。
import { onMounted, ref } from "vue"
import { RouterLink, useRoute, useRouter } from "vue-router"
import { getMyArticlePreview } from "../api/articles"
import MarkdownContent from "../components/MarkdownContent.vue"

// 从路由读取文章 ID，并准备登录跳转能力。
const route = useRoute()
const router = useRouter()
// 保存加载状态、错误信息和文章对象。
const article = ref(null)
const loading = ref(true)
const error = ref("")

// 进入页面后请求私有预览接口。
onMounted(async () => {
  try {
    article.value = await getMyArticlePreview(route.params.id)
  } catch (requestError) {
    // 未登录时回到登录页；其他错误在当前页面显示。
    if (requestError.response?.status === 401) {
      router.push({ path: "/login", query: { next: "/my-articles" } })
      return
    }
    error.value = requestError.response?.data?.detail || "预览失败。"
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-width detail-page">
    <!-- 返回作者文章列表，不进入公共文章详情。 -->
    <RouterLink class="back-link" to="/my-articles">返回我的文章</RouterLink>

    <div v-if="loading" class="empty-state">正在加载预览……</div>
    <div v-else-if="error" class="empty-state">{{ error }}</div>

    <article v-else-if="article" class="article-detail">
      <header>
        <span class="article-category">OwnerBlog / 预览</span>
        <h1>{{ article.title }}</h1>
        <p class="detail-excerpt">{{ article.summary }}</p>
      </header>

      <!-- MarkdownContent 内部会先解析再消毒，不能直接 v-html。 -->
      <MarkdownContent :source="article.content" />
    </article>
  </div>
</template>
```

#### 4.5.5 注册路由和预览入口

在 `frontend/src/main.js` 增加导入：

```javascript
// 导入作者文章预览页。
import MyArticlePreviewView from "./views/MyArticlePreviewView.vue"
```

在 `routes` 数组中增加：

```javascript
// 预览页不使用公共文章详情页的公开门禁。
{ path: "/my-articles/:id/preview", component: MyArticlePreviewView },
```

在 `MyArticlesView.vue` 的文章操作区域增加：

```vue
<!-- 草稿、待审核、索引中和索引失败的文章都允许作者预览。 -->
<RouterLink
  v-if="['draft', 'pending_review', 'indexing', 'index_failed'].includes(article.status)"
  class="line-button"
  :to="`/my-articles/${article.id}/preview`"
>
  预览
</RouterLink>
```

如果模板使用 `RouterLink`，先在 `<script setup>` 中确认已有：

```javascript
// 导入 RouterLink，供模板生成预览链接。
import { RouterLink, useRouter } from "vue-router"
```

- 新增 `MyArticlePreviewAPIView`，未登录返回 `401`。
- 普通用户只能预览自己的文章；其他用户访问返回 `404`。
- 管理员可以预览任意文章，便于检查审核和索引失败内容。
- 新增 `/api/my-articles/<int:pk>/preview`，复用 `MyArticleSerializer` 返回正文。
- 新增 `/my-articles/:id/preview` 页面，复用 `MarkdownContent.vue`。
- “我的文章”列表给每篇本人文章显示“预览”入口，包括 `draft`、`pending_review`、`indexing` 和 `index_failed`。
- 公共 `/articles/:id` 仍然只允许 `published + indexed`，不能复用预览接口替代公开接口。

验收：

- 作者可以预览自己的草稿和待审核文章。
- 作者不能预览其他用户的文章。
- 未登录用户不能访问作者预览接口。
- 待审核文章可以在预览页显示 Markdown 标题、粗体、列表和代码块。
- 待审核文章不会出现在公共文章列表或公共详情页。

### 4.6 编辑页的验收

在 `MyArticlesView.vue` 中继续使用 `<textarea>`，本日不引入复杂编辑器。输入并保存以下内容：

````markdown
# 索引测试文章

这是 **重要内容**。

- 第一项
- 第二项

```python
print("hello")
```
````

预期：

- 数据库和 API 中保留 `#`、`**`、列表符号和代码围栏等 Markdown 原文。
- 详情页显示标题、粗体、列表和代码块，而不是显示 Markdown 符号。
- 输入 `<script>alert(1)</script>` 后，页面不执行脚本。
- 详情页仍然只展示 `published + indexed` 文章。

出错检查：确认 `marked` 和 `dompurify` 安装在 `frontend`，确认只有消毒后的 `renderedHtml` 进入 `v-html`，确认没有把 `clean_markdown()` 的结果保存回 `Article.content`。

执行前端检查：

```powershell
cd E:\Desktop\VibeCoding\ownerblog\frontend
pnpm build
```

预期：构建成功，且没有 Vue 模板、依赖导入或 Markdown 组件错误。

## 5. Phase 1B：实现索引专用清洗和切片

### 本 Phase 官方文档

- [CommonMark Spec](https://spec.commonmark.org/0.31.2/)：了解标题、围栏代码、链接、图片和 HTML 块的 Markdown 结构。本 Phase 只做面向检索的轻量清洗，不声称实现完整 Markdown 解析器。
- [Python `re` documentation](https://docs.python.org/3/library/re.html)：核对正则表达式替换、`MULTILINE` 和 Unicode 字符串行为。

### 5.1 创建文件

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\chunking.py
```

创建以下最小实现：

```python
# 使用正则表达式处理少量 Markdown 展示噪声；这里不是完整 Markdown 解析器。
import re


def clean_markdown(content):
    """保留可检索文本，去掉图片、链接和多余空白。"""
    # 空值按空字符串处理，后面可以统一判断是否有可索引正文。
    text = content or ""
    # 删除图片语法及图片地址，避免图片 URL 占用 embedding 文本空间。
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # 保留链接显示文字，删除链接目标地址。
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # 删除 HTML 标签，但保留标签外的文字。
    text = re.sub(r"<[^>]+>", "", text)
    # 删除代码围栏标记，保留代码内容用于检索。
    text = re.sub(r"^```\w*\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    # 删除标题符号，但保留标题文字。
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # 把过多空行压缩成两个换行，减少无意义空白。
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除正文首尾空白后返回索引专用文本。
    return text.strip()


def split_into_chunks(content, title, chunk_size=1000, overlap=150):
    """优先按段落切分，过长段落再按字符切分。"""
    # overlap 必须小于 chunk_size，否则切片起点可能无法前进。
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size 必须大于 0，overlap 必须小于 chunk_size")

    # 只清洗索引副本，绝不覆盖数据库中的 Markdown 原文。
    cleaned = clean_markdown(content)
    if not cleaned:
        return []

    # 优先按空行识别段落，尽量保留文章语义边界。
    paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > chunk_size:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + paragraph
        elif len(paragraph) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                chunks.append(paragraph[start:end])
                if end >= len(paragraph):
                    break
                start = end - overlap
        else:
            current = candidate

    if current:
        chunks.append(current)

    return [
        {
            "chunk_index": index,
            "content": f"{title}\n\n{chunk}".strip(),
        }
        for index, chunk in enumerate(chunks)
    ]
```

### 5.2 为什么这样写

- `clean_markdown()` 只处理今天需要的噪声，不引入复杂 Markdown AST。
- 标题加回每个片段，检索结果脱离原文时仍有上下文。
- `chunk_index` 由切片顺序生成，后面用于 `ArticleChunk` 和 Chroma ID。
- `overlap` 必须小于 `chunk_size`，否则切片循环可能无法前进。

### 5.3 执行检查

```powershell
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe -m py_compile knowledge\chunking.py
```

预期：没有输出。

在 PowerShell 中执行简单验证：

```powershell
@'
from knowledge.chunking import split_into_chunks

result = split_into_chunks("# 标题\n\n第一段。\n\n第二段。", "测试文章", 30, 5)
print(result)
assert result
assert result[0]["chunk_index"] == 0
'@ | .\.venv\Scripts\python.exe manage.py shell
```

预期：打印至少一个片段，且片段包含“测试文章”。

出错检查：确认当前目录是 `backend`，并确认文件名是 `chunking.py` 而不是 `chunking.py.txt`。

## 6. Phase 2：封装 embedding

### 本 Phase 官方文档

- [OpenAI Vector embeddings](https://developers.openai.com/api/docs/guides/embeddings)：核对 Python SDK 调用方式、批量输入、模型最大输入长度和 `dimensions`。
- [OpenAI Embeddings API reference](https://developers.openai.com/api/reference/resources/embeddings)：核对 `input`、`model`、返回 `data` 和 `index` 字段。
- [Sentence Transformers Usage](https://www.sbert.net/docs/sentence_transformer/usage/usage.html)：核对本地模型加载和批量 `encode` 的用法。
- [BAAI/bge-small-zh-v1.5 模型卡](https://huggingface.co/BAAI/bge-small-zh-v1.5)：确认中文模型、检索指令和 512 维输出。

### 6.1 创建文件并配置本地客户端

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\llm.py
```

创建：

```python
# 读取环境变量，并提供本地 embedding；测试时允许注入假客户端。
import os
from functools import lru_cache

from openai import OpenAI


DEFAULT_LOCAL_MODEL = "BAAI/bge-small-zh-v1.5"
QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


def get_remote_embedding_client():
    # API Key 只从后端环境变量读取，不能放进 Vue 或提交到 Git。
    api_key = os.getenv("MODEL_API_KEY")
    if not api_key:
        raise RuntimeError("MODEL_API_KEY 未配置")
    return OpenAI(
        # 使用服务商要求的 API Key。
        api_key=api_key,
        # 没有配置时使用 OpenAI 默认地址；配置后支持兼容 OpenAI 的服务。
        base_url=os.getenv("MODEL_BASE_URL") or None,
        # 网络请求设置上限，避免索引流程永久等待。
        timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
    )


@lru_cache(maxsize=1)
def get_local_embedding_model():
    # 延迟导入，只有实际使用本地模型时才需要本地推理库。
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError(
            "本地 embedding 需要安装 sentence-transformers"
        ) from error
    # 第一次调用时下载模型，之后从本机缓存加载。
    model_name = os.getenv("EMBEDDING_MODEL") or DEFAULT_LOCAL_MODEL
    return SentenceTransformer(model_name)


def embed_texts(texts, client=None, is_query=False):
    """保持输入顺序返回 embedding；支持本地模型和注入式客户端。"""
    # 空输入不调用模型，也不生成空向量。
    if not texts:
        return []
    model = os.getenv("EMBEDDING_MODEL") or DEFAULT_LOCAL_MODEL
    # 传入 client 时用于 FakeClient；生产默认使用本地模型。
    if client is not None:
        response = client.embeddings.create(model=model, input=texts)
        # 按 API 返回的 index 排序，确保向量和 chunk 顺序一致。
        ordered = sorted(response.data, key=lambda item: item.index)
        embeddings = [item.embedding for item in ordered]
    elif os.getenv("EMBEDDING_PROVIDER", "local").lower() == "local":
        # 第一次调用时下载模型，之后从本机缓存加载。
        local_model = get_local_embedding_model()
        inputs = texts
        if is_query:
            # BGE 模型建议给检索问题加指令，文章片段不加指令。
            inputs = [f"{QUERY_INSTRUCTION}{text}" for text in texts]
        embeddings = local_model.encode(
            inputs,
            normalize_embeddings=True,
            convert_to_numpy=False,
            show_progress_bar=False,
        )
        embeddings = [vector.tolist() for vector in embeddings]
    elif os.getenv("EMBEDDING_PROVIDER", "local").lower() == "remote":
        # 只有明确配置 remote 时才调用远程 embedding API。
        response = get_remote_embedding_client().embeddings.create(
            model=model, input=texts,
        )
        ordered = sorted(response.data, key=lambda item: item.index)
        embeddings = [item.embedding for item in ordered]
    else:
        raise RuntimeError("EMBEDDING_PROVIDER 必须是 local 或 remote")
    if len(embeddings) != len(texts):
        raise RuntimeError("embedding 返回数量与输入数量不一致")
    dimensions = len(embeddings[0]) if embeddings else 0
    if any(len(item) != dimensions for item in embeddings):
        raise RuntimeError("embedding 向量维度不一致")
    return embeddings
```

### 6.2 配置并验证本地客户端

本项目的聊天模型和 embedding 模型分开配置。聊天模型继续由 `MODEL_NAME` 控制；文章索引默认使用本地 `BAAI/bge-small-zh-v1.5`，不调用远程 `/embeddings` 接口。

后端环境变量应类似：

```text
MODEL_API_KEY=你的服务密钥
MODEL_BASE_URL=你的 OpenAI-compatible 服务地址，可选
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
```

本地模型第一次运行时会下载，之后从本机缓存加载。不要把模型文件复制进 Git，也不要打印或提交 `MODEL_API_KEY`。配置完成后，在 `backend` 目录运行：

```powershell
@'
from knowledge.llm import embed_texts

vectors = embed_texts(["local embedding test"])
print("向量数量：", len(vectors))
print("向量维度：", len(vectors[0]))
assert len(vectors) == 1
assert len(vectors[0]) > 0
'@ | .\.venv\Scripts\python.exe manage.py shell
```

预期：

```text
向量数量： 1
向量维度： 512
```

如果这里失败，先检查 `sentence-transformers` 是否安装、模型是否下载完成、Python 环境是否为 `backend/.venv`，不要马上修改索引代码。

### 6.3 为什么测试仍然使用 FakeClient

本地模型可以验证真实向量生成，但不适合作为自动化测试的唯一依赖。模型加载可能耗时，也可能受本机依赖、缓存和硬件影响。自动化测试要用 `FakeClient` 固定返回结果，专门验证自己的代码逻辑。

两种调用方式如下：

```python
# 手动联调：不传 client，函数内部加载本地模型。
local_vectors = embed_texts(["本地模型测试"])

# 自动化测试：传入 FakeClient，不访问网络。
fake_vectors = embed_texts(
    ["第一段", "第二段"],
    client=FakeClient(),
)
```

`response.data` 的返回顺序不能直接当作输入顺序，所以代码要按返回项的 `index` 排序。`chunk_size` 是字符级教学参数，不等于模型 token 上限；正式调整切片大小前要按官方文档核对模型最大输入长度。

### 6.4 执行代码检查

```powershell
.\.venv\Scripts\python.exe -m py_compile knowledge\llm.py
```

预期：没有输出。若 `openai` 导入失败，执行 `pip install -r requirements.txt` 后重试。

## 7. Phase 3：封装 Chroma

### 本 Phase 官方文档

- [Chroma Python Collection reference](https://docs.trychroma.com/reference/python/collection)：核对 Python 版 `upsert`、`query` 和 `delete` 参数。
- [Chroma Manage Collections](https://docs.trychroma.com/docs/collections/manage-collections)：确认 `get_or_create_collection` 和 collection 的基本生命周期。
- [Chroma Update Data](https://docs.trychroma.com/docs/collections/update-data)：理解 `upsert` 按 ID 新建或更新，以及向量维度必须保持一致。

### 7.1 创建文件

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\chroma_store.py
```

创建：

```python
# Chroma 负责向量的持久化和相似度查询；ArticleChunk 仍保存关系映射。
import os
from pathlib import Path
import chromadb


def get_collection():
    # 默认使用 backend/data/chroma，也允许 .env 指定其他目录。
    raw_path = os.getenv("CHROMA_PERSIST_DIRECTORY", "./data/chroma")
    persist_path = Path(raw_path)
    if not persist_path.is_absolute():
        persist_path = Path(__file__).resolve().parents[1] / persist_path
    # 使用持久化客户端，让服务重启后仍能读取向量。
    client = chromadb.PersistentClient(path=str(persist_path))
    # collection 是 Chroma 中存储和查询向量的基本单位。
    return client.get_or_create_collection(name="ownerblog_articles")


def make_document_id(article_id, chunk_index):
    # 文章 ID 和片段序号组成稳定 ID，重复 upsert 时覆盖同一条记录。
    return f"article-{article_id}-chunk-{chunk_index}"


def upsert_chunks(article_id, chunks, embeddings, collection=None):
    # 测试时注入 fake collection，生产环境才连接本地 Chroma。
    active_collection = collection or get_collection()
    # 每个 ID、正文、向量和 metadata 必须按相同下标一一对应。
    ids = [make_document_id(article_id, item["chunk_index"]) for item in chunks]
    active_collection.upsert(
        ids=ids,
        documents=[item["content"] for item in chunks],
        embeddings=embeddings,
        metadatas=[
            {
                "article_id": str(article_id),
                "title": item.get("title", ""),
                "chunk_index": item["chunk_index"],
            }
            for item in chunks
        ],
    )
    return ids


def delete_article_chunks(article_id, collection=None):
    active_collection = collection or get_collection()
    active_collection.delete(where={"article_id": str(article_id)})


def query_chunks(query_embedding, limit=5, collection=None):
    # 用已经生成好的问题向量查询，避免 Chroma 使用不同的 embedding 模型。
    active_collection = collection or get_collection()
    return active_collection.query(
        query_embeddings=[query_embedding],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )
```

### 7.2 执行检查

```powershell
.\.venv\Scripts\python.exe -m py_compile knowledge\chroma_store.py
```

预期：没有输出。确认 `.env` 中的 `CHROMA_PERSIST_DIRECTORY` 指向 `backend/data/chroma` 或其他明确的本地目录。

不要用 `runserver` 自动重载写 Chroma：

```powershell
.\.venv\Scripts\python.exe manage.py runserver --noreload
```

## 8. Phase 4：实现最小索引 Service

### 本 Phase 官方文档

- [Django Database transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)：确认 `atomic()` 的提交/回滚边界，并明确数据库事务不会覆盖 Chroma 这类外部存储。
- [Chroma Update Data](https://docs.trychroma.com/docs/collections/update-data)：确认向量写入是外部副作用，失败补偿不能假设由 Django 自动完成。

### 8.1 创建文件

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\services.py
```

创建以下成功/失败编排。这里故意不把 Chroma 代码、模型代码写进 View 或 Admin：

```python
# 索引 Service 只负责流程编排：清洗、向量化、写 Chroma、保存数据库映射。
import hashlib
from django.db import transaction
from django.utils import timezone

from articles.models import Article, ArticleStatus, IndexStatus
from .chroma_store import upsert_chunks
from .chunking import split_into_chunks
from .llm import embed_texts
from .models import ArticleChunk


def _save_index_failure(article, step, error):
    # 任何失败都进入统一的失败状态，方便 Admin 定位阶段。
    article.status = ArticleStatus.INDEX_FAILED
    article.index_status = IndexStatus.FAILED
    article.index_step = step
    article.index_error = str(error)
    if step == "embedding":
        article.embedding_error = str(error)
    if step == "chroma":
        article.chroma_error = str(error)
    article.save(update_fields=[
        "status", "index_status", "index_step", "index_error",
        "embedding_error", "chroma_error", "updated_at",
    ])


def index_article(article, embedding_client=None, collection=None):
    # 只有审核通过、等待索引的文章才允许进入首次索引。
    if article.status != ArticleStatus.INDEXING:
        raise ValueError("只有 indexing 状态的文章可以执行首次索引")

    try:
        article.index_step = "cleaning"
        article.index_error = ""
        article.embedding_error = ""
        article.chroma_error = ""
        article.save(update_fields=[
            "index_step", "index_error", "embedding_error",
            "chroma_error", "updated_at",
        ])

        # 读取原始 Markdown，清洗结果只存在于内存中的 chunks。
        chunks = split_into_chunks(article.content, article.title)
        if not chunks:
            raise ValueError("文章没有可索引的正文")
        for item in chunks:
            item["title"] = article.title

        article.index_step = "embedding"
        article.save(update_fields=["index_step", "updated_at"])
        # 按 chunks 顺序生成向量，保证后续逐项写入对应片段。
        embeddings = embed_texts(
            [item["content"] for item in chunks],
            client=embedding_client,
        )

        article.index_step = "chroma"
        article.save(update_fields=["index_step", "updated_at"])
        # 先写外部向量库，成功后再写数据库映射和公开状态。
        vector_ids = upsert_chunks(
            article.id, chunks, embeddings, collection=collection,
        )

        # ArticleChunk 和 Article 状态必须在同一个数据库事务中提交。
        with transaction.atomic():
            ArticleChunk.objects.filter(article=article).delete()
            ArticleChunk.objects.bulk_create([
                ArticleChunk(
                    article=article,
                    chunk_index=item["chunk_index"],
                    content=item["content"],
                    vector_document_id=vector_id,
                )
                for item, vector_id in zip(chunks, vector_ids)
            ])
            article.status = ArticleStatus.PUBLISHED
            article.index_status = IndexStatus.INDEXED
            article.index_step = "completed"
            article.indexed_at = timezone.now()
            article.content_hash = hashlib.sha256(
                article.content.encode("utf-8")
            ).hexdigest()
            article.save(update_fields=[
                "status", "index_status", "index_step", "indexed_at",
                "content_hash", "published_at", "updated_at",
            ])
        # 调用方拿到的是已完成索引的文章对象。
        return article
    except Exception as error:
        # 记录失败阶段后继续抛出，让 Admin 或上层调用方决定如何提示。
        _save_index_failure(article, article.index_step or "unknown", error)
        raise
```

### 8.2 先用假客户端验证

真实客户端联调成功后，再在 `knowledge/tests.py` 中加入假客户端。假客户端需要返回 `data[index].embedding`，用于稳定测试返回顺序和数量：

```python
class FakeEmbeddingItem:
    def __init__(self, index, embedding):
        self.index = index
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(self, texts):
        self.data = [
            FakeEmbeddingItem(index, [float(index), 1.0, 0.0])
            for index, _ in enumerate(texts)
        ]


class FakeEmbeddings:
    def create(self, model, input):
        return FakeEmbeddingResponse(input)


class FakeClient:
    embeddings = FakeEmbeddings()
```

测试时将 `FakeClient()` 传给 `index_article(..., embedding_client=FakeClient())`。Chroma collection 也要使用测试 collection 或 fake collection，不要读取开发机已有数据。

### 8.3 出错检查

- `ArticleChunk` 导入失败：确认 `knowledge/models.py` 的模型名仍是 `ArticleChunk`。
- `article.save()` 报数据库字段错误：先运行 `migrate`，不要修改模型绕过错误。
- embedding 配置错误：测试使用 `FakeClient`；真实调用才需要 `.env`。
- Chroma 路径不一致：从 `backend` 启动，确认 `Path` 解析后的目录只有一个。
- 失败后文章仍是 `indexing`：检查 `except` 是否调用 `_save_index_failure()`。

## 9. Phase 5：接入管理员通过动作

### 本 Phase 官方文档

- [Django Admin actions](https://docs.djangoproject.com/en/5.2/ref/contrib/admin/actions/)：确认 Action 的函数签名和逐条处理选中对象的方式。
- [Django Database transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)：确认 `approve_article()` 返回并离开 `atomic()` 后数据库事务才完成；索引编排必须发生在审核状态提交之后。
- [Django `on_commit()`](https://docs.djangoproject.com/en/5.2/topics/db/transactions/#performing-actions-after-commit)：作为后续异步任务接入的依据，本日同步流程暂不引入任务队列。

### 9.1 修改文件

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\articles\services.py
```

不要直接在现有的 `@transaction.atomic approve_article()` 内调用索引。先保留 `approve_article()` 只负责提交审核状态，再在同一个文件中新增编排函数：

```python
def approve_and_index_article(*, article, actor):
    # 先完成并提交审核事务，确保文章离开 pending_review。
    article = approve_article(article=article, actor=actor)
    # 延迟导入，避免 articles.models 与 knowledge.services 循环导入。
    from knowledge.services import index_article

    # 在审核事务提交后执行同步索引。
    try:
        index_article(article)
    except Exception:
        # index_article 已经把失败状态写入数据库；这里不再回滚它。
        article.refresh_from_db()
    return article
```

然后打开 `backend/articles/admin.py`，把导入和 Action 调用从 `approve_article` 改为 `approve_and_index_article`。审核事件先保留，索引成功后文章才变成 `published`。

不要删除 `approve_article()` 原有的 `return article`，Day 4 的测试仍然需要它验证“审核通过后进入 indexing”。

### 9.2 今天的失败行为

`index_article()` 失败时会把文章设置为：

```text
status = index_failed
index_status = failed
index_step = 失败阶段
```

管理员看到错误后，今天可以直接通过 Django Admin 检查字段；重建命令留到后续。普通用户不能编辑这些字段，公开 API 也不会返回这篇文章。

### 9.3 执行检查

```powershell
.\.venv\Scripts\python.exe -m py_compile articles\services.py
.\.venv\Scripts\python.exe -m py_compile knowledge\services.py
.\.venv\Scripts\python.exe manage.py check
```

预期：全部成功。

## 10. Phase 6：最小检索验证

### 本 Phase 官方文档

- [Chroma Query and Get](https://docs.trychroma.com/docs/querying-collections/query-and-get)：核对 `query_embeddings`、`n_results`、`include`、距离值和结果的二维数组结构。
- [Chroma Python Collection reference](https://docs.trychroma.com/reference/python/collection)：核对最终 Python 调用签名。
- [Django QuerySet API](https://docs.djangoproject.com/en/5.2/ref/models/querysets/)：依据文章状态过滤结果，确保公开检索只返回 `published + indexed` 数据。

### 10.1 添加检索函数

在 `knowledge/services.py` 末尾加入：

```python
from .chroma_store import query_chunks


def search_similar_chunks(question, embedding_client=None, collection=None):
    if not question or not question.strip():
        raise ValueError("问题不能为空")
    query_vector = embed_texts(
        [question.strip()], client=embedding_client,
    )[0]
    result = query_chunks(query_vector, limit=5, collection=collection)
    metadatas = (result.get("metadatas") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    article_ids = [int(item["article_id"]) for item in metadatas]
    allowed_ids = set(
        Article.objects.filter(
            id__in=article_ids,
            status=ArticleStatus.PUBLISHED,
            index_status=IndexStatus.INDEXED,
        ).values_list("id", flat=True)
    )
    return [
        {
            "article_id": int(meta["article_id"]),
            "title": meta.get("title", ""),
            "content": document,
            "chunk_index": meta["chunk_index"],
            "distance": distance,
        }
        for meta, document, distance in zip(metadatas, documents, distances)
        if int(meta["article_id"]) in allowed_ids
    ]
```

### 10.2 验收

准备一篇内容明确的文章，执行管理员通过操作。预期：

```text
Article.status = published
Article.index_status = indexed
Article.index_step = completed
ArticleChunk 至少有 1 条记录
vector_document_id 不为空
公开文章 API 可以返回该文章
```

再执行一次 `search_similar_chunks()`，预期返回该文章标题、片段内容和距离值。

如果 Chroma 查询不到结果，先检查是否使用了同一个 embedding 模型、collection 名称和持久化目录。不要先修改相似度阈值掩盖空数据问题。

## 11. 今天的技术难点

今天不是把几个 SDK 方法串起来就算完成。真正需要学习的是下面 6 个问题。每个问题都要在对应 Phase 中用代码或测试验证。

### 难点一：为什么不能把 Markdown 原文直接做 embedding

Markdown 中的图片地址、链接 URL、HTML 标签和代码围栏会占用文本空间，但不一定有助于检索。完全删除 Markdown 又可能丢掉标题、代码和段落结构。

今天的取舍是：

```text
删除展示噪声
保留标题文字
保留代码内容
按段落切分
```

对应执行：Phase 1B 的 `clean_markdown()` 和 `split_into_chunks()`。

验证问题：清洗后是否还能看出文章主题？每个片段是否包含标题？空正文是否会生成空向量？

### 难点二：chunk size 和 overlap 怎么避免切坏语义

片段太短会失去上下文，片段太长会降低召回精度并增加模型成本。`overlap` 太大还会造成大量重复，甚至在循环切分时无法前进。

今天只掌握可解释的规则：段落优先，超长段落按字符拆分；`0 <= overlap < chunk_size`；每个片段有稳定的 `chunk_index`。

对应执行：Phase 1 的参数校验和切片验证。

### 难点三：embedding 的输入顺序和输出顺序

文章片段必须和向量一一对应。如果第 2 个片段保存了第 1 个向量，检索结果仍然可能有内容，但引用会错位，问题很隐蔽。

今天需要理解并验证：

```text
输入 texts[0..n]
  -> API 返回带 index 的 data
  -> 按 index 排序
  -> embeddings[0..n] 与 chunks[0..n] 对齐
```

对应执行：Phase 2 的 `embed_texts()` 和假客户端测试。

### 难点四：数据库事务不能回滚 Chroma

`transaction.atomic()` 只能保护 SQLite。Chroma 是外部持久化存储：如果 Chroma 已写入、随后 `ArticleChunk.bulk_create()` 失败，数据库回滚不会自动删除向量。

今天的最小处理方式是：

- 成功前不设置 `published + indexed`。
- 任何阶段失败都记录 `index_step` 和对应错误字段。
- 失败后设置 `index_failed + failed`。
- 重建和补偿清理明确记录为后续任务。

对应执行：Phase 4 的 `_save_index_failure()` 和失败测试。

### 难点五：审核状态和索引状态不能混为一个字段

管理员通过只代表内容审核通过，不代表向量已经写入。只有下面的组合才允许公开：

```text
Article.status = published
Article.index_status = indexed
```

索引成功前必须保持 `indexing`，失败后必须变为 `index_failed + failed`。这也是为什么不能在 Admin 中直接把文章改成 `published`。

对应执行：Phase 5 的 `approve_and_index_article()` 和公开 API 验证。

### 难点六：为什么自动化测试不能依赖真实模型服务

真实 API 会受到 Key、网络、额度和超时影响。手动联调可以使用真实 API；但若自动化测试直接调用真实服务，失败时无法判断是代码错误还是外部服务问题。

今天用依赖注入解决：

```text
生产环境：使用 OpenAI-compatible client
测试环境：传入 FakeClient
```

Chroma 也使用测试 collection 或 fake collection，不能依赖开发机已有的 `data/chroma` 数据。

### 今天掌握和后续学习的边界

今天必须掌握：清洗切片、embedding 封装、Chroma 基本写入/查询、状态成功/失败转换、假客户端测试。

后续再深入：指数退避重试、幂等重建、旧向量补偿删除、任务队列、召回率评估和相似度阈值调优。

## 12. 最小自动化测试

### 本 Phase 官方文档

- [Django Writing and running tests](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)：使用 `django.test.TestCase` 和 Django 测试数据库，不连接真实模型服务。
- [Django Advanced testing topics](https://docs.djangoproject.com/en/5.2/topics/testing/advanced/)：了解测试运行器如何创建测试数据库、运行迁移并销毁测试数据。
- [Django `captureOnCommitCallbacks()`](https://docs.djangoproject.com/en/5.2/topics/testing/tools/#django.test.TestCase.captureOnCommitCallbacks)：仅在后续改为 `transaction.on_commit()` 调度索引时使用，本日同步索引不需要它。

打开：

```text
E:\Desktop\VibeCoding\ownerblog\backend\knowledge\tests.py
```

今天至少补三类测试：

1. `split_into_chunks()`：空正文返回空列表，正常正文返回带 `chunk_index` 的片段。
2. `embed_texts()`：假客户端返回的向量数量和输入数量相同，顺序一致。
3. `index_article()`：成功后是 `published + indexed`，embedding 失败后是 `index_failed + failed`。

测试命令：

```powershell
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py test knowledge articles
```

预期：测试通过。测试不能连接真实模型服务，不能依赖 `data/chroma` 中已有的数据。

## 13. Day 5 最终验收

- [ ] 用户可以在普通文本编辑区输入 Markdown 源码，保存后 `Article.content` 保留原文。
- [ ] 文章详情页使用 Markdown 渲染组件展示标题、段落、列表、代码块和链接。
- [ ] Markdown 转 HTML 后经过 DOMPurify 消毒，恶意脚本不会执行。
- [ ] 一篇文章可以完成清洗、切片、embedding、Chroma 写入和 `ArticleChunk` 保存。
- [ ] 成功后状态为 `published + indexed`，公开 API 可以返回。
- [ ] embedding 或 Chroma 失败后状态为 `index_failed + failed`，并记录失败阶段。
- [ ] 检索结果回查 SQLite，只保留 `published + indexed` 文章。
- [ ] 测试使用假 embedding，不依赖 API Key 和网络。
- [ ] Day 3、Day 4 原有测试没有回归。

以下内容确认留到后续：重建命令、删除/下架清理、重复索引、完整重试、相似度阈值调优和 GPT 问答。

## 14. 提交前检查

```powershell
cd E:\Desktop\VibeCoding\ownerblog\backend
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
cd ..\frontend
pnpm build
cd ..
git diff --check
git status --short
```

不要提交 `.env`、SQLite 数据库、`data/chroma` 和真实 API Key。
