# OwnerBlog RAG 最终交付路线图

## 1. 文档职责

本文是 OwnerBlog 的开发流程路线图，不是逐步操作手册。

本文回答：

- 项目分为哪些开发阶段；
- 每个阶段要解决什么问题；
- 阶段之间有什么依赖关系；
- 每个阶段产出什么模块和数据契约；
- 什么条件下可以认为阶段完成；
- 当前源码处于什么状态。

本文不展开：

- 逐行代码修改；
- PowerShell 或 Django 命令；
- 测试替身的具体写法；
- 失败后的逐项排查步骤；
- 每个文件的教学式修改过程。

上述内容统一放在：

`E:\Desktop\VibeCoding\owerblog_munalstep\rag-final-delivery-execution-manual.md`

两份文档的关系是：

```text
final-delivery-roadmap.md
  = 做什么、为什么做、先后顺序、完成定义

rag-final-delivery-execution-manual.md
  = 怎么改、改哪些文件、运行什么测试、失败怎么处理
```

开发人员应先依据本文确定阶段和边界，再使用执行手册完成具体开发。不能把执行手册中的命令和代码复制回路线图，造成职责混乱。

## 2. 最终交付目标

OwnerBlog 的本期交付目标是一个可验证的 RAG 知识问答闭环：

```text
文章创建或导入
  -> 内容解析和清洗
  -> 文章切分和来源保存
  -> Embedding 与向量写入
  -> 审核、索引和发布状态闭环
  -> 用户问题校验
  -> 闲聊分流或知识问题处理
  -> 授权范围内的混合检索
  -> 动态上下文构建
  -> 基于来源生成回答
  -> 回答清洗和来源展示
  -> 离线评估和交付验收
```

问答范围必须支持两种模式：

| 模式 | 允许使用的资料 | 网络行为 |
| --- | --- | --- |
| 联网搜索关闭 | 公开文章、公开知识库、当前用户有权限访问的私密知识库 | 不调用 MCP |
| 联网搜索开启 | 上述本地授权资料，加上网络 MCP 返回的网页来源 | 允许调用 MCP，但不得发送私密内容 |

本期交付可以继续使用 Django、SQLite、Chroma PersistentClient 和 Vue 的单机架构，但不能据此宣称高并发生产能力。团队、多知识库成员协作、Celery/Redis、高可用和企业级权限属于后续扩展，除非项目另行立项，不作为本期 RAG 闭环的隐含前置条件。

## 3. 当前源码基线

### 3.1 已具备的基础能力

| 能力 | 主要模块 | 状态 |
| --- | --- | --- |
| 文章状态和审核 | `backend/articles/models.py`、`backend/articles/services.py` | 已有草稿、待审核、索引中、索引失败、已发布和下架状态 |
| 审核后索引入口 | `backend/articles/services.py`、`backend/knowledge/index_pipeline.py` | 已有 `transaction.on_commit()` 和索引编排 |
| 内容清洗和切分 | `backend/knowledge/source_pipeline.py`、`backend/knowledge/services/` | 基础链路已存在 |
| ArticleChunk 持久化 | `backend/knowledge/services/article_chunks.py` | 已有原子替换、内容 hash 和文章版本 |
| Embedding 服务 | `backend/knowledge/llm.py` | 已有 provider、批处理、维度和有限数值校验 |
| Chroma 写入 | `backend/knowledge/vector_store.py` | 已有稳定 ID、collection 版本和 metadata |
| 回答安全门禁 | `backend/knowledge/answering.py` | 已有无来源 abstain 和回答清洗基础能力 |
| 公开向量检索 | `backend/knowledge/retrieval.py` | 只有向量检索，尚未达到混合检索标准 |
| 问答 API | `backend/knowledge/api.py` | 有基础接口，但尚未完成意图、权限和联网分流 |
| 问答前端 | `frontend/src/views/KnowledgeView.vue` | 有基础问答和来源展示，尚未完成三态和联网开关 |

### 3.2 当前未完成的交付能力

当前项目不能声明最终交付完成，主要原因是：

1. 闲聊和知识问题尚未在 API 层分流。
2. 检索只有向量召回，没有关键词召回和混合排序。
3. 文章标题、摘要尚未作为独立的增强输入参与 Embedding。
4. 回答上下文只有静态字符截断，没有动态预算和来源去重。
5. 没有公开/私密知识库模型和当前用户权限范围。
6. 没有联网搜索开关和 MCP 网络来源适配器。
7. 前端没有明确区分 `casual`、`grounded`、`abstained`。
8. 没有固定评估集、RAG 质量指标和离线评估命令。
9. 已发布文章的版本更新策略尚未落地。
10. MinerU 分支、外部服务测试隔离和部分基线测试仍需收口。

## 4. 总体阶段依赖

```text
Stage 0 交付边界和数据契约
   |
   v
Stage 1 内容来源与解析
   |
   v
Stage 2 文章索引、版本与发布
   |
   v
Stage 3 Embedding、向量库与增强输入
   |
   +----------------------+
   |                      |
   v                      v
Stage 4 意图判断       Stage 5 权限范围与知识库
   |                      |
   +----------+-----------+
              v
Stage 6 混合检索
              |
              v
Stage 7 动态上下文、回答安全与来源
              |
              +------------------+
              |                  |
              v                  v
Stage 8 联网 MCP 开关       Stage 9 前端问答体验
              |                  |
              +----------+-------+
                         v
Stage 10 RAG 评估与质量门禁
                         |
                         v
Stage 11 更新、删除、导入和部署验收
```

权限范围必须先于混合检索进入检索服务，联网 MCP 必须在权限范围完成后接入。这样可以确保网络搜索只是增加一种来源，而不是绕过本地权限过滤。

## 5. Stage 0：交付边界和数据契约

### 5.1 目标

统一文章、片段、向量、来源、问答状态和权限范围的基础定义，避免不同模块各自解释“可检索”“已发布”和“私密”。

### 当前源码位置和状态

| 当前源码 | 已有内容 | 当前问题 |
| --- | --- | --- |
| `backend/articles/models.py`：`ArticleStatus`、`IndexStatus`、`Article` | 已有草稿、待审核、索引中、索引失败、已发布、下架，以及索引步骤、错误、内容 hash、版本 | `Article` 没有公开/私密字段，也没有知识库关联 |
| `backend/knowledge/models.py`：`ArticleChunk` | 已有文章、连续片段序号、正文、正文 hash、文章版本、metadata、向量文档 ID | 没有来源类型、知识库 ID、授权范围字段 |
| `backend/knowledge/retrieval.py`：`RetrievedChunk`、`RetrievalReport` | 已有最小的向量检索结果结构和问题校验 | 只有单一 `score`，没有 `vector_score`、`keyword_score`、`final_score` 和权限范围 |
| `backend/knowledge/answering.py`：`AnswerResult`、`_source_payload()` | 已有 `grounded`、`abstained`、文章来源 URL 和正文 | 来源结构还没有私密知识库、网页来源和来源类型 |
| `backend/knowledge/api.py`：`KnowledgeChatAPIView.post()` | 已有 JSON 请求体校验、检索、回答和错误响应 | 只读取 `question`，没有 `web_search_enabled`，也没有用户范围参数 |

本阶段不是新增一个“大而全”的基础模块，而是把上述已有结构和后续新增结构固定成共同契约。后续 Stage 修改模型或响应时，必须保持这些契约的一致性。

### 本阶段要做什么

这一阶段先不做具体问答功能，而是把后续开发要共同遵守的规则定下来：

1. 明确一篇文章从草稿到发布、下架、删除的状态变化。
2. 明确什么条件下文章可以进入向量库和公开问答。
3. 明确数据库正文、Embedding 输入、Chroma 文档和回答来源的区别。
4. 明确问答 API 的请求字段、三种业务状态和来源字段。
5. 明确公开文章、公开知识库、私密知识库和网页来源的边界。
6. 明确联网搜索是用户请求开关，还是被部署配置允许的能力。

完成后，后续阶段不再自行定义状态、来源和权限规则；所有模块都按照本阶段的契约实现。

### 5.2 主要职责

- 定义文章生命周期：草稿、待审核、索引中、索引失败、已发布、下架。
- 定义公开检索门禁：文章必须已发布且已索引。
- 定义 `ArticleChunk.content` 是真实正文，不能被 Embedding 增强文本污染。
- 定义向量记录与文章、片段、文章版本和内容 hash 的关系。
- 定义问答状态：`casual`、`grounded`、`abstained`。
- 定义来源类型：公开文章、私密知识库、网页来源。
- 定义联网搜索总开关和用户请求开关的区别。

### 5.3 产出

- 文章和片段数据契约；
- 问答请求/响应契约；
- 来源对象契约；
- 公开、私密和网页来源的权限边界；
- 本期范围与后续扩展范围说明。

### 5.4 完成标准

所有后续阶段使用同一套状态、来源类型和版本规则；没有模块可以绕过发布状态或用户权限直接把内容送入 Prompt。

## 6. Stage 1：内容来源、解析和清洗

### 6.1 目标

将 Markdown、PDF、扫描文档、Word、PPT 和图片等来源转换为统一、可追溯、可安全处理的文档对象。

### 当前源码位置和状态

当前源码已经有一条“来源路由 → 结构化抽取 → 清洗”的链路：

| 当前源码 | 已有行为 | 当前缺口或风险 |
| --- | --- | --- |
| `backend/knowledge/document_types.py`：`SourceBlock`、`ParsedDocument`、`ExtractionResult` | 为 Markdown、MinerU 和 LangExtract 定义了统一数据对象 | 这些对象还没有成为文章文件导入和索引入口的完整持久化契约 |
| `backend/knowledge/source_router.py`：`build_document_from_source()` | `markdown` 走直接路径；`mineru` 走 `parse_with_mineru()` | 当前 `Article.content` 的索引入口仍固定按 Markdown 处理 |
| `backend/knowledge/source_pipeline.py`：`prepare_source_for_indexing()` | 生成统一 `ParsedDocument`，调用 LangExtract；抽取失败会降级为 warning | 需要补齐真实文件导入、失败状态和 warning 的验收覆盖 |
| `backend/knowledge/indexing.py`：`prepare_article_source()` | 当前把 `Article.content` 作为 Markdown 交给来源处理 | 没有把文章附件或原始文件接入索引入口 |
| `backend/knowledge/services/content_cleaner.py`：`clean_prepared_source()` | 规范化 Markdown、渲染 HTML、Bleach 清洗、转纯文本并生成 hash | 需要确保标题、数字、英文、代码和表格在真实文档中不被错误清除 |
| `backend/knowledge/mineru_adapter.py`：`parse_with_mineru()` | 支持本地 MinerU CLI；代码中保留远程 API 分支 | 本地成功后直接返回，远程分支不可达；远程分支使用了 `time` 但文件未导入；没有完整 PDF/OCR 验收 |

因此本阶段的开发重点是“补齐输入路径和真实验收”，不是重新发明清洗器。现有清洗结果只能作为切分输入，不能覆盖 `Article.content`。

### 本阶段要做什么

这一阶段要解决“用户提交的各种文件怎样变成可以切分的干净文本”：

1. 让 Markdown 文章直接进入内容处理流程。
2. 让 PDF、扫描 PDF、Word、PPT 和图片经过 MinerU 得到统一文档结果。
3. 让 LangExtract 提供标题、章节、主题和原文位置等结构化信息。
4. 让清洗器删除危险 HTML 和无意义格式，同时保留标题、数字、术语、代码和正文含义。
5. 保留作者提交的原文，不能用清洗结果覆盖原文。
6. 为解析成功、解析失败、抽取失败和可降级 warning 定义统一结果。

完成后，无论文章来自 Markdown 还是文件导入，后续切分阶段都只接收同一种标准文档对象。

### 6.2 主要职责

- Markdown 文章走直接解析路径。
- PDF、扫描文档和复杂文件由 MinerU 负责解析。
- LangExtract 负责结构化字段和原文位置，不负责向量检索或最终回答。
- 清洗器负责危险 HTML、脚本、格式噪音和基础正文规范化。
- 原始文章内容始终保留，清洗结果作为后续处理输入。
- 解析和抽取失败必须有明确的 warning 或 failed 状态。
- 外部 MinerU/LangExtract 服务与普通单元测试隔离。

### 6.3 产出

- 统一 `ParsedDocument` 或等价文档对象；
- 清洗后的 Markdown、HTML 和纯文本；
- 文章内容 hash；
- 解析器、抽取器和来源版本 metadata；
- 可追溯的原始来源关系。

### 6.4 依赖和完成标准

依赖 Stage 0 的内容和来源契约。完成后，Markdown 可以不依赖 MinerU 进入切分流程，真实文档可以经过 MinerU 进入同一处理流程，原文不会被清洗或抽取结果覆盖。

## 7. Stage 2：文章索引、版本与发布闭环

### 7.1 目标

保证只有成功完成内容处理、片段持久化、Embedding 和 Chroma 写入的文章才能发布和参与问答。

### 当前源码位置和状态

| 当前源码 | 已有行为 | 当前缺口或需要修正的边界 |
| --- | --- | --- |
| `backend/articles/services.py`：`approve_article()` | 管理员审核后设置 `ArticleStatus.INDEXING`、`IndexStatus.INDEXING`，清理旧错误并通过 `transaction.on_commit()` 调用 `run_article_index()` | 这是同步的提交后调用，不是 Celery 异步任务；路线图不能把它描述成已具备队列重试 |
| `backend/articles/services.py`：`retry_article_index()` | 失败或 stale 文章可以清理错误、增加 `version`、重新进入索引 | 需要验证重试时旧片段、旧向量和新版本不会混用 |
| `backend/knowledge/index_pipeline.py`：`run_article_index()` | 已按来源准备、清洗、切分、持久化、Embedding、Chroma、最终发布顺序执行 | 需要补充版本切换和发布前后旧版本可见性的测试 |
| `backend/knowledge/index_pipeline.py`：`_mark_failed()`、`_publish_if_current()` | 失败时保存步骤和错误类型；发布前检查状态与 hash | 错误状态、孤立片段和孤立向量的跨步骤一致性仍需验收 |
| `backend/knowledge/services/article_chunks.py`：`persist_article_chunks()` | 已做输入校验、连续序号校验、hash/version 校验和事务内替换 | 需要把版本切换策略与公开检索过滤明确连接起来 |
| `backend/articles/services.py`：`cleanup_article_resources()`、`take_down_article()`、`reject_article()` | 已删除 Chroma 向量和数据库片段；下架/驳回后删除文章 | 当前删除路径是硬删除，不能按“保留历史版本”来描述；若交付要求可恢复，需要另立版本/回收站设计 |

当前索引主链路是：

```text
approve_article()
  -> transaction.on_commit(run_article_index)
  -> prepare_article_source()
  -> clean_prepared_source()
  -> MarkdownTextChunker().split()
  -> persist_article_chunks()
  -> EmbeddingService().embed_article_chunks()
  -> ChromaVectorStore().upsert_article_chunks()
  -> _publish_if_current()
```

本阶段的开发工作是在这条已有链路上补版本、失败恢复和生命周期验收，不是另建一条索引入口。

### 本阶段要做什么

这一阶段要把“审核”和“索引”真正连成一个可恢复的发布流程：

1. 审核通过时把文章置为索引中，而不是直接公开。
2. 按固定顺序执行内容校验、清洗、切分、片段保存、向量生成和向量写入。
3. 每一步失败时保存失败步骤和安全错误摘要。
4. 只有全部步骤成功后，才同时更新索引成功和文章发布状态。
5. 失败文章可以重新索引，重试时不会沿用旧错误或旧片段。
6. 文章修改、下架和删除时，旧片段和旧向量不会继续参与问答。

完成后，系统可以回答“这篇文章现在是否允许被检索”，也可以回答“索引失败发生在哪一步”。

### 7.2 主要职责

- 审核通过后进入 `indexing`，不能直接发布。
- 按内容校验、清洗、切分、片段持久化、Embedding、Chroma 写入的顺序运行。
- 每一步记录当前索引步骤和安全错误摘要。
- 全部成功后才设置 `indexed` 和 `published`。
- 失败后进入 `index_failed`，支持管理员重试。
- 重新索引增加文章版本并清理不再使用的旧向量。
- 删除、下架和新版本切换时同步清理旧片段和旧向量。
- 使用事务提交后的索引入口，避免读取未提交数据。

### 7.3 产出

- 可重试的文章索引编排；
- 文章索引状态和失败原因；
- 文章版本、内容 hash 和索引时间；
- 数据库片段与向量库记录的对应关系。

### 7.4 完成标准

公开接口、公开检索和回答来源永远不会读取草稿、待审核、索引失败、下架或孤立片段。索引失败可以定位到步骤并重新执行，重复索引不会产生重复有效数据。

## 8. Stage 3：Embedding、向量库和增强输入

### 8.1 目标

建立文章片段和问题使用同一 provider/model 的稳定向量化链路，并提升标题、摘要和短关键词的召回能力。

### 当前源码位置和状态

| 当前源码 | 已有行为 | 当前缺口 |
| --- | --- | --- |
| `backend/knowledge/llm.py`：`EmbeddingService` | 已支持 `local` 和 `openai_compatible` provider、批处理、重试、查询向量和文章片段向量 | `embed_article_chunks()` 当前只把 `chunk.content` 送入 Embedding，没有标题/摘要增强文本 |
| `backend/knowledge/llm.py`：`embed_query()`、`_validate_vectors()`、`_parse_response()` | 文章和问题共用 settings 中的 provider/model；已有数量、顺序、维度、空值、NaN/Infinity 校验 | 增强输入后仍必须继续返回真实正文 `content`，不能用拼接文本污染 `EmbeddedChunk.content` |
| `backend/knowledge/services/article_chunks.py`：`persist_article_chunks()` | 已把清洗后的正文保存为 `ArticleChunk.content`，并保存 hash 和文章版本 | 需要为标题/摘要增强文本确定独立边界，不能修改该字段含义 |
| `backend/knowledge/vector_store.py`：`ChromaVectorStore` | 已使用版本化 collection、cosine metadata、稳定向量 ID，并保存文章/片段/模型/provider/维度/hash/version metadata | 现有 `_validate_inputs()` 强制 Embedding 正文等于 `ArticleChunk.content`；增强输入后要改成“来源正文一致、Embedding 输入可追溯”的契约 |
| `backend/config/settings.py`、`backend/.env.example` | 已有 provider/model/device/batch/retry 配置和 collection version | 需要补齐增强输入格式版本，并保证文章与问题始终读取同一 provider/model |
| `backend/knowledge/tests.py`：`EmbeddingServiceTests`、`ChromaVectorStoreTests` | 已有假模型、假 Chroma 和基础校验测试 | collection mock 当前没有同步断言生产代码传入的 `metadata={"hnsw:space": "cosine"}`，需要修测试而不是删生产配置 |

本阶段不能把“配置已经存在”误判为“增强输入已完成”。配置、服务封装和校验大部分已有，标题/摘要输入、输入版本和全量重索引仍是交付缺口。

### 本阶段要做什么

这一阶段要完成“文章怎么变成向量、问题怎么变成向量，以及两者为什么可以比较”：

1. 统一文章向量和问题向量使用的 provider、模型、设备和批量配置。
2. 保留向量数量、顺序、维度、空值、NaN 和 Infinity 校验。
3. 让文章向量输入由标题、摘要和正文片段组成。
4. 保证增强后的输入只送给 Embedding，不污染 `ArticleChunk.content` 和来源展示。
5. 用 collection 版本、模型、provider 和维度隔离不同向量体系。
6. 在模型或输入格式变化后提供全量重索引能力。

完成后，用户问标题词、摘要词、数字或正文事实时，都有机会命中同一篇文章的向量；新旧模型不会混在同一个检索空间中。

### 8.2 主要职责

- 统一本地或远程 Embedding provider。
- 保持文章片段数量、顺序、维度和有限数值校验。
- 文章片段 Embedding 输入包含文章标题、文章摘要和真实正文片段。
- `ArticleChunk.content` 继续保存真实正文。
- 增强文本只用于 Embedding，不用于来源展示。
- Chroma collection 按 Embedding 模型、provider 和版本隔离。
- provider、model、dimension、content hash 和 article version 写入 metadata。
- 模型或输入格式变化后进行全量重索引。

### 8.3 产出

- 文章向量服务；
- 问题向量服务；
- 版本化 Chroma collection；
- 可追溯的 EmbeddedChunk；
- 标题/摘要/正文增强输入策略。

### 8.4 完成标准

文章和问题使用同一 Embedding 配置；数字、标题和摘要词可以参与召回；增强输入不会污染真实正文；新旧 Embedding 不会混用。

## 9. Stage 4：意图判断和闲聊分流

### 9.1 目标

在检索之前识别不需要知识库的固定闲聊，减少无意义的向量、MCP 和回答模型调用。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 本阶段要改变的地方 |
| --- | --- | --- |
| `backend/knowledge/api.py`：`KnowledgeChatAPIView.post()` | 只校验 JSON 对象，然后直接调用 `retrieve_public_chunks()` 和 `answer_from_retrieval()` | 在调用检索前显式调用 `validate_question()` 和 `classify_question()` |
| `backend/knowledge/retrieval.py`：`validate_question()` | 已校验字符串、空值、长度和控制字符 | 保持它作为所有问题的第一道门，不让意图判断绕过输入校验 |
| `backend/knowledge/answering.py`：`answer_from_retrieval()` | 无来源返回 `abstained`；有来源调用回答模型 | 闲聊必须在这里之前返回 `casual`，不能伪装成 `abstained` |
| `backend/knowledge/intent.py` | 当前文件不存在 | 新增确定性规则和 `QuestionIntent`，不使用大模型分类 |

当前 API 没有任何闲聊特殊处理，所以 `你好` 仍会进入 Embedding、Chroma 和回答链路。本阶段完成的标志不是“能识别几个词”，而是这些词在调用链上完全绕过检索、回答模型和未来的 MCP。

### 本阶段要做什么

这一阶段要把问答入口拆成两条路：

1. 先校验请求是否合法。
2. 对 `你好`、`谢谢`、`你是谁`、`再见` 等固定输入做确定性分类。
3. 闲聊直接返回固定答案，不访问任何知识库或外部服务。
4. 只有知识问题才进入权限计算、检索、上下文和回答流程。
5. 让 API 返回的 `status` 能明确表达这是闲聊，不是资料不足。

完成后，问候语不会浪费检索和模型资源，知识问题仍然可以进入完整 RAG 流程。

### 9.2 主要职责

- 增加确定性的 `QuestionIntent`。
- 支持 `你好`、`谢谢`、`你是谁`、`再见` 等固定规则。
- 闲聊直接返回固定答案和空来源。
- 知识问题才进入权限、检索和回答链路。
- 输入校验必须先于意图判断。
- 闲聊不得调用 Embedding、Chroma、MCP 或回答模型。

### 9.3 产出

- `backend/knowledge/intent.py`；
- API 层的闲聊分流；
- 固定闲聊响应；
- casual 与 knowledge 的测试契约。

### 9.4 完成标准

闲聊响应稳定、无外部调用；知识问题仍能完整进入后续 RAG 流程；前端可以依据 `status` 区分闲聊和资料不足。

## 10. Stage 5：知识库范围和用户权限

### 10.1 目标

把公开文章、公开知识库和当前用户有权限的私密知识库统一成检索范围，并让数据库权限过滤成为最终权威。

### 当前源码位置和状态

| 当前源码 | 已有行为 | 当前缺口 |
| --- | --- | --- |
| `backend/articles/models.py`：`Article` | 只有 `author`，没有 `visibility`、`knowledge_base` 或成员授权关系 | 当前无法表达“公开文章”和“当前用户私密知识库” |
| `backend/articles/views.py`：`ArticleCollectionAPIView`、`ArticleItemAPIView` | 公开接口按 `PUBLISHED + INDEXED` 过滤；用户文章按 `author=request.user` 隔离 | 公开/私密不是独立权限层，问答 API 也没有接收当前用户范围 |
| `backend/knowledge/retrieval.py`：`retrieve_public_chunks()` | 只通过文章公开状态和索引状态过滤，再按向量 ID 回查数据库 | 函数名和实现都只支持 public，不能返回用户授权私密片段 |
| `backend/knowledge/vector_store.py` | Chroma metadata 有文章和片段标识，可用于缩小候选 | metadata 不是权限证明，当前没有数据库授权过滤服务 |
| `backend/knowledge/api.py`：`KnowledgeChatAPIView` | 使用 `AllowAny`，匿名请求可以问公开知识 | 未登录用户、文章作者、知识库成员之间没有不同结果范围 |

因此 Stage 5 是当前项目新增的基础能力，不是对现有某个“私密检索模块”的小修。必须先设计模型、迁移、授权范围服务和数据库最终过滤，Stage 6 才能把它作为检索输入。

### 本阶段要做什么

这一阶段要先解决“这个用户到底能看哪些资料”，再允许这些资料进入检索：

1. 为文章增加公开/私密属性。
2. 建立知识库、知识库拥有者和文章关联关系。
3. 定义公开知识库可以包含哪些文章。
4. 定义当前用户可以访问哪些私密知识库和文章。
5. 匿名用户只获得公开范围，登录用户才可以叠加自己的授权私密范围。
6. 在数据库层完成最终权限过滤，不能只相信 Chroma metadata 或前端传入的 ID。
7. 阻止未授权片段进入回答上下文、来源返回和 MCP 请求。

完成后，同一个问题会根据用户身份得到不同的合法来源集合，系统不会因为用户猜中了 ID 就暴露其他人的资料。

### 10.2 主要职责

- 增加文章公开/私密属性。
- 增加 `KnowledgeBase` 和文章关联关系。
- 记录知识库拥有者和公开/私密属性。
- 当前用户默认可以检索自己拥有或被授权的私密知识库。
- 匿名用户只能检索公开文章和公开知识库。
- Chroma metadata 只用于缩小候选，不能替代数据库权限过滤。
- 未授权片段不能进入回答 Prompt、来源列表或网络请求。
- 成员、团队和更细粒度权限作为后续扩展接入同一范围接口。

### 10.3 产出

- 知识库和文章关联模型；
- 授权范围构建服务；
- 公开/私密检索过滤；
- 跨用户访问和来源泄露防护。

### 10.4 完成标准

同一个问题在匿名用户、用户 A 和用户 B 下可以得到不同且正确的来源范围；用户不能通过文章 ID、知识库 ID 或 Chroma metadata 猜测其他用户的私密内容。

## 11. Stage 6：混合检索和结果排序

### 11.1 目标

解决短问题、数字、中文术语、英文词、标题词和摘要词只依赖向量检索时容易漏召回的问题。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 本阶段要补的内容 |
| --- | --- | --- |
| `backend/knowledge/retrieval.py`：`retrieve_public_chunks()` | 生成一个问题向量，调用 `ChromaVectorStore.query()`，把 cosine distance 转为 similarity，再回查 `ArticleChunk` | 保留这条向量通道，同时新增关键词通道和授权范围参数 |
| `backend/knowledge/retrieval.py`：`RetrievedChunk` | 只有一个 `score` 和文章/片段正文 | 增加 `vector_score`、`keyword_score`、`final_score`、来源类型等结果字段，或定义等价的不可变结果结构 |
| `backend/knowledge/retrieval.py`：`validate_question()` | 能拒绝空、超长和控制字符问题 | 继续负责格式校验；另加“没有有效知识词”的检索门禁，不能把所有短问题交给向量库 |
| `backend/knowledge/vector_store.py`：`query()` | 只能按向量查询 Chroma distance | 不在 VectorStore 中塞入 Django 关键词逻辑；关键词查询应在检索服务或独立查询服务中完成 |
| `Article.title`、`Article.summary`、`ArticleChunk.content` | 数据库中已有标题、摘要和真实正文 | 关键词检索必须在这三个字段上执行，并最终回到数据库做状态和权限过滤 |

当前检索仍是“单向量 + similarity threshold”，没有中文 n-gram、数字/英文词、标题摘要匹配、候选合并或最终混合分数。因此降低 `SIMILARITY_THRESHOLD` 不能视为完成 Stage 6，反而会增加无关片段进入回答的风险。

### 本阶段要做什么

这一阶段要把“只查向量”改成“向量和关键词共同找资料”：

1. 保留现有向量召回作为语义检索通道。
2. 增加标题、摘要和正文的关键词召回通道。
3. 让中文短语、数字、英文单词和完整短语都能参与关键词匹配。
4. 合并两条通道的候选结果，并按片段去重。
5. 分别记录向量分数和关键词分数，再计算最终排序分数。
6. 对标题或正文完整命中的关键词提供最低召回保障。
7. 对没有有效知识词的问题直接返回空结果，防止无关问题触发生成。

完成后，“9183 是什么”可以依靠数字命中，“蓝色鲸鱼是什么”可以依靠中文或语义命中，而完全无关的问题不会被低质量相似度强行回答。

### 11.2 主要职责

- 保留向量检索。
- 增加标题、摘要和正文的关键词检索。
- 支持中文短语、数字、英文单词和完整短语。
- 合并向量候选和关键词候选并去重。
- 为每个候选保存 `vector_score` 和 `keyword_score`。
- 使用统一的 `final_score` 排序。
- 对标题或正文完整命中的关键词提供最低召回保障。
- 对“文章”“它是什么”“随便说说”等无有效词问题直接返回空结果。
- 在返回结果前再次执行公开/私密权限过滤。

### 11.3 产出

- 混合检索服务；
- 查询词提取和无效问题门禁；
- 双分数结果结构；
- 去重、排序和数量限制策略。

### 11.4 完成标准

包含数字 `9183` 的短问题可以通过关键词命中；标题和摘要词可以召回；无关问题不会触发无来源生成；向量、关键词和权限三条过滤规则可以共同生效。

## 12. Stage 7：动态上下文、回答安全和来源

### 12.1 目标

将检索结果转换成受预算约束、可追溯、只包含授权资料的回答上下文。

### 当前源码位置和状态

| 当前源码 | 已有行为 | 当前缺口 |
| --- | --- | --- |
| `backend/knowledge/answering.py`：`build_prompt()` | 将所有 `report.results` 拼接后使用 `settings.MAX_CONTEXT_CHARS` 截断 | 没有按最终分数排序、来源去重、单片段预算、同文章上限或段落边界截断；可能从正文中间截断 |
| `backend/knowledge/answering.py`：`answer_from_retrieval()` | 无结果直接返回 `AnswerResult(status="abstained")`，有结果才创建回答请求 | 需要把动态 ContextBuilder 接到回答入口，并确保授权过滤发生在构建上下文之前 |
| `backend/knowledge/answering.py`：`clean_generated_answer()` | 已清理 `【source-2】`、`[source-2]`、来源行、代码围栏和多余空白 | 保留并扩展测试；清洗只处理回答文本，不能修改来源正文 |
| `backend/knowledge/answering.py`：`_source_payload()` | 已输出文章标题、URL、片段序号和正文 | 需要统一公开文章、私密知识库和网页来源字段，回答和来源继续分开返回 |

所以当前项目已经具备“无来源拒答”和“回答清洗”两个基础门禁，但还没有动态上下文处理。Stage 7 不能只增加一个更大的 `MAX_CONTEXT_CHARS`，而要把 `build_prompt()` 的静态字符串拼接升级为有预算、有排序、有来源 ID 的上下文构建过程。

### 本阶段要做什么

这一阶段要解决“检索到了很多片段，回答模型到底应该看到哪些片段”：

1. 按混合检索最终分数选择高价值片段。
2. 删除重复片段并限制同一文章占用的上下文比例。
3. 设置总上下文、单片段和片段数量预算。
4. 尽量按段落和句子边界截取，避免把事实从中间截断。
5. 给每个上下文块保留来源 ID、文章标题、片段编号和来源类型。
6. 没有来源时直接拒答，不初始化回答模型。
7. 有来源时只允许根据上下文回答，并清理模型产生的引用标记和来源行。

完成后，回答模型看到的是经过排序、预算控制和权限过滤的资料，而不是未经处理的全文拼接。

### 12.2 主要职责

- 按最终检索分数选择上下文片段。
- 对相同片段去重，对同一文章设置片段数量上限。
- 设置总上下文预算、单片段预算和总片段数量预算。
- 优先在段落、句子等完整边界截取，避免简单从字符串末尾截断。
- 每个上下文块携带来源 ID、标题、片段编号和来源类型。
- 无来源时直接 `abstained`，不调用回答模型。
- 有来源时回答只能依据上下文，不得补造外部事实。
- 清理模型引用标记、来源行、代码围栏和异常空白。
- 回答与来源分离返回，来源由数据库或 MCP 适配器生成。

### 12.3 产出

- 动态 ContextBuilder；
- 上下文预算和来源追溯策略；
- 回答模型安全门禁；
- `grounded`、`abstained` 和来源响应。

### 12.4 完成标准

上下文不是简单的全文拼接或末尾截断；每个回答事实都能追溯到授权来源；无来源不调用模型；模型输出中的引用标记不会泄露到前端。

## 13. Stage 8：联网搜索开关和 MCP 来源

### 13.1 目标

允许用户在单次问答中选择是否增加网络搜索，同时保持本地知识库的权限边界不变。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 本阶段要新增的边界 |
| --- | --- | --- |
| `backend/config/settings.py`、`backend/.env.example` | 已有模型和 Embedding 配置，没有网络搜索总开关、MCP endpoint、工具名或超时配置 | 增加服务端能力开关和 MCP 连接配置，默认关闭 |
| `backend/knowledge/api.py`：`KnowledgeChatAPIView.post()` | 只接受 `question`，没有外部来源选项 | 接受并严格校验 `web_search_enabled`，且必须再经过服务端总开关判断 |
| `backend/knowledge/retrieval.py` | 只查询本地公开 Chroma | 本地授权来源和网页来源要在统一来源契约中合并，不能把 MCP 直接塞进 Chroma 查询 |
| 项目现有 `backend/knowledge/` | 当前没有 MCP client、transport、网页来源结构或网络错误分类 | 新增隔离的 `WebSearchService`/适配器及其 fake 测试替身 |
| `frontend/src/api/articles.js` | `askKnowledge()` 只发送 `{ question }` | 发送 `web_search_enabled`，但不把 endpoint、密钥或私密内容放到前端 |

本阶段的前置条件是 Stage 5 已能生成当前用户授权的本地范围。MCP 只接收用户原始问题；不能把本地片段、标题、摘要、metadata 或 Prompt 发送到网络服务。

### 本阶段要做什么

这一阶段要增加一条可控的外部信息来源，但不能让联网搜索绕过本地权限：

1. 增加后端部署级总开关，决定系统是否允许使用网络搜索。
2. 增加本次问答的用户开关，决定本次问题是否使用 MCP。
3. 关闭时只查询公开文章、公开知识库和当前用户有权限的私密知识库。
4. 打开时在本地授权资料之外追加网页来源。
5. 通过 `WebSearchService` 隔离 MCP 协议、超时、错误和响应解析。
6. 只把用户问题发送给 MCP，不能发送私密文章正文、摘要、标题或 metadata。
7. 把网页结果标记为 `source_type=web`，和公开文章、私密知识库来源区分。
8. MCP 无结果或超时时，已有本地来源仍可回答；所有来源都为空时仍然拒答。

完成后，用户可以明确选择“只问本地知识”或“本地知识加网络搜索”，而系统不会把私密知识库内容泄露给外部网络。

### 13.2 开关模型

系统需要两层开关：

| 开关 | 作用 | 位置 |
| --- | --- | --- |
| `RAG_WEB_SEARCH_ENABLED` | 部署级能力总开关，关闭时任何请求都不能调用 MCP | 后端配置 |
| `web_search_enabled` | 用户本次问答是否允许网络搜索 | API 请求 |

请求开关打开时，问答范围是“本地授权来源 + MCP 网页来源”；关闭时只能使用“本地授权来源”。闲聊无论开关状态如何都不能调用 MCP。

### 13.3 主要职责

- 增加后端 `WebSearchService`，隔离 MCP transport 和协议细节。
- 配置 MCP endpoint、工具名、超时、最大来源数和失败策略。
- MCP 只接收用户问题，不接收私密文章正文、标题、摘要或 metadata。
- 将网页结果规范化为标题、URL、摘要和 `source_type=web`。
- 本地来源和网页来源合并后统一进入动态上下文和回答安全门禁。
- MCP 超时或无结果时，已有本地授权来源仍可继续回答。
- 本地和 MCP 都没有来源时返回 `abstained`。
- 前端显示联网开关和当前检索范围。

### 13.4 产出

- MCP 网络搜索适配器；
- 服务端和请求级开关；
- 网页来源结构；
- 私密数据不外发的边界；
- 网络失败降级策略。

### 13.5 完成标准

关闭开关时 MCP 调用次数为零；打开开关时网页来源可追溯；私密内容不进入 MCP 请求、日志或匿名响应；服务端总开关不能被客户端绕过。

当前仓库没有 MCP endpoint、工具名或 MCP 响应协议配置，因此该阶段在实际开发中必须以部署端提供 MCP 服务为前置条件，不能把当前开发环境的网络工具直接当作项目运行时能力。

## 14. Stage 9：前端问答体验

### 14.1 目标

让前端正确表达问答状态、来源类型、联网范围和服务错误，不让用户误解回答依据。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 本阶段要补的内容 |
| --- | --- | --- |
| `frontend/src/views/KnowledgeView.vue`：`submitQuestion()` | 有输入、loading、基础成功结果和错误文本 | 目前不保存或显示明确 `status`，所以 `casual`、`grounded`、`abstained` 不能分别呈现 |
| `frontend/src/views/KnowledgeView.vue`：结果模板 | 有答案文本和文章来源链接 | 需要显示资料不足、固定闲聊答案、来源类型、网页 URL 和当前联网范围 |
| `frontend/src/api/articles.js`：`askKnowledge()` | trim 后只发送 `{ question: value }` | 需要增加 `web_search_enabled` 参数并保持 API 响应原样传回 |
| 后端 `KnowledgeChatAPIView` 响应 | 当前已有 `status`、`answer`、`sources` 基础字段 | 前端要依赖状态字段渲染，不能通过答案内容猜状态 |

前端当前页面文案还明确写着“只会使用已公开并完成索引的文章”，在 Stage 5 和 Stage 8 完成后必须同步改成实际的本地授权范围与联网开关说明，否则界面会与后端行为不一致。

### 本阶段要做什么

这一阶段要把后端问答能力完整呈现给用户：

1. 让 `casual` 显示固定回答。
2. 让 `grounded` 显示答案和真实来源。
3. 让 `abstained` 显示资料不足，而不是显示成服务错误或闲聊。
4. 让网络错误、MCP 错误和回答模型错误单独呈现。
5. 增加联网搜索开关，并明确显示当前检索范围。
6. 区分公开文章、私密知识库和网页来源。
7. 清理旧结果、处理加载状态并避免重复提交。

完成后，用户能看懂答案状态、答案来源和联网范围，不需要根据回答文字猜测系统做了什么。

### 14.2 主要职责

- 区分 `casual`、`grounded` 和 `abstained`。
- `casual` 只显示固定回答，不显示资料不足。
- `grounded` 显示回答和来源。
- `abstained` 显示没有足够资料。
- 网络错误、MCP 不可用和回答模型错误单独显示。
- 增加联网搜索开关并提交 `web_search_enabled`。
- 区分公开文章、私密知识库和网页来源展示方式。
- 请求中禁止重复提交，切换问题时清理旧结果。

### 14.3 产出

- 三态问答界面；
- 联网搜索开关；
- 来源类型展示；
- 移动端和桌面端稳定布局。

### 14.4 完成标准

前端完全依据后端状态字段渲染，不通过猜测答案文字判断状态；用户能看出回答来自公开文章、私密知识库还是网页搜索。

## 15. Stage 10：RAG 评估和质量门禁

### 15.1 目标

用固定数据集和可重复指标判断检索、上下文、回答、权限和联网开关是否达到交付标准，而不是只依赖单元测试或人工感觉。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 本阶段要新增的内容 |
| --- | --- | --- |
| `backend/knowledge/tests.py` | 已有来源、清洗、切分、片段持久化、Embedding、Chroma、索引、检索、回答和 API 的单元/集成测试 | 这些测试验证代码分支，不等于固定 RAG 质量评估；缺少 golden question 和排名指标 |
| `backend/knowledge/retrieval.py`、`answering.py` | 已能产生检索报告和回答结果 | 需要通过稳定接口记录命中片段、状态、来源和耗时 |
| `backend/knowledge/` | 没有 `evaluation` 模块、评估数据集或 `evaluate_rag` management command | 新增离线评估 runner、数据格式和 JSON/Markdown 报告 |
| 外部依赖 | Embedding、回答模型、LangExtract、MinerU 和未来 MCP 都可能访问外部服务 | 评估默认使用 fake provider；真实联网评估必须显式开启并单独记录 |

当前仓库不能因为测试数量多就宣称“RAG 已评估”。Stage 10 的交付对象是可重复比较的质量报告，且必须覆盖联网关闭时 MCP 调用数为零、私密来源不泄露和无来源正确拒答。

### 本阶段要做什么

这一阶段不是继续增加业务功能，而是建立“怎么证明 RAG 质量”的方法：

1. 准备包含闲聊、知识问题、数字、标题、摘要、无关问题和权限场景的固定问题集。
2. 为每个问题标注预期状态、正确片段和参考答案。
3. 运行同一套检索、上下文、回答和权限链路，记录每次结果。
4. 计算 Hit@K、Recall@K、MRR、状态准确率、来源准确率和拒答准确率。
5. 统计检索、上下文、回答模型、Embedding 和 MCP 的耗时与调用次数。
6. 分别评估联网关闭和联网开启，确认关闭时 MCP 调用为零。
7. 将指标阈值和评估结果保存下来，后续每次检索逻辑变更都重新比较。

完成后，团队可以用同一份评估集判断一次改动是提升了召回，还是只是让模型生成了更多看似合理的答案。

### 15.2 主要职责

- 固定 golden question 数据集版本和样本格式。
- 用 fake Embedding、fake Chroma、fake 回答模型和 fake MCP 运行离线评估。
- 分开统计检索、上下文、回答、权限和联网开关指标。
- 将评估结果输出成可比较的 JSON/Markdown 报告。
- 把 Hit@K、MRR、拒答、来源、权限泄露和 MCP 调用次数纳入交付门禁。
- 真实外部服务评估必须显式允许，并和离线结果分开记录。

### 15.3 评估数据

建立版本化的 golden question 数据集，至少覆盖：

- 闲聊问题；
- 标题命中；
- 摘要命中；
- 中文短语；
- 数字关键词；
- 英文术语；
- 完全无关问题；
- 无来源拒答；
- 公开与私密权限隔离；
- 联网开关开启和关闭；
- MCP 超时或无结果；
- 来源引用和答案清洗。

每条样本至少包含问题、预期状态、正确片段 ID、参考答案和联网开关状态。

### 15.4 指标

检索指标：

- Hit@K；
- Recall@K；
- MRR；
- 关键词命中保留率。

回答指标：

- `casual`、`grounded`、`abstained` 状态准确率；
- 无来源拒答准确率；
- 来源引用准确率；
- 参考答案关键事实覆盖率；
- 回答清洗通过率。

权限和联网指标：

- 跨用户私密来源泄露数；
- 关闭联网时 MCP 调用次数；
- 私密内容进入 MCP 请求的次数；
- 网页来源 URL 可追溯率。

性能指标：

- 检索耗时；
- 上下文构建耗时；
- 回答模型耗时；
- MCP 耗时；
- Embedding、回答模型和 MCP 调用次数；
- 上下文平均和最大长度。

### 15.5 产出

- 版本化评估集；
- 离线评估运行器和管理命令；
- JSON/Markdown 评估报告；
- 交付质量阈值；
- 每次检索或回答改动后的对比结果。

### 15.6 完成标准

评估可以在 fake Embedding、fake Chroma、fake 回答模型和 fake MCP 下离线重复运行；联网评估需要显式允许。交付门槛至少包括：

- Hit@5 达到项目设定阈值；
- MRR 达到项目设定阈值；
- 无来源问题全部正确拒答；
- 来源引用没有未授权项；
- casual 不产生任何检索、模型或 MCP 调用；
- 关闭联网时 MCP 调用为零；
- 动态上下文不超过预算。

## 16. Stage 11：文章更新、删除、导入和部署验收

### 16.1 目标

验证系统在真实生命周期和部署环境中仍然保持来源一致、权限正确和数据可恢复。

### 当前源码位置和状态

| 当前源码 | 当前行为 | 当前缺口 |
| --- | --- | --- |
| `backend/articles/views.py`：`ArticleItemAPIView.patch()` | 只有文章作者能修改自己的文章，但只允许 `DRAFT` 状态 | 已发布文章不能走版本化更新；还没有“新版本索引成功后切换公开版本”的业务路径 |
| `backend/articles/views.py`：`ArticleItemAPIView.delete()` | 作者删除文章时调用 `cleanup_article_resources()`，然后硬删除文章 | 需要验证向量、片段、来源和权限范围全部清理；若需要恢复能力，必须新增明确的软删除/版本设计 |
| `backend/articles/services.py`：`cleanup_article_resources()`、`take_down_article()` | 下架和驳回会清理 Chroma 与 `ArticleChunk` | 当前逻辑是硬删除，不应在路线图中假设已经保留历史版本 |
| `backend/knowledge/mineru_adapter.py` | 有本地 MinerU 路径和不可达的远程路径代码 | 需修复远程分支结构、补 `time` 导入，并完成真实 PDF/OCR 验收 |
| 部署配置 | 有 SQLite、Chroma、模型和 Embedding 环境配置 | 没有 MCP 配置、备份恢复、健康检查和全新环境验收闭环 |

Stage 11 是生命周期和部署收口阶段。它不能用一次“文章能回答”来代替，必须验证更新、下架、删除、失败重试、文件导入、重启和恢复后的来源与权限仍然一致。

### 本阶段要做什么

这一阶段负责把开发完成的功能收口成可交付系统：

1. 已发布文章修改时创建新草稿或新版本，不直接覆盖旧索引。
2. 新版本索引成功后再切换公开版本，并清理旧向量。
3. 删除、下架和失败重试不会留下可召回的孤立数据。
4. 验证 MinerU 本地/远程路径、LangExtract 降级和外部服务隔离。
5. 在全新环境中验证数据库、Chroma、媒体文件、模型配置和 MCP 配置。
6. 验证备份恢复、启动文档、健康检查和已知限制。
7. 整理最终演示流程，确保演示不依赖手工修改数据库。

完成后，系统不仅能在开发机上回答问题，还能在重启、更新、删除、失败和恢复场景中保持数据与权限一致。

### 16.2 主要职责

- 已发布文章修改采用新草稿/新版本，不直接覆盖已发布正文。
- 新版本索引成功前，旧版本继续保持可用。
- 新版本发布后，旧版本退出公开检索并清理旧向量。
- 删除、下架和重建索引不会留下孤立片段或向量。
- MinerU 本地/远程分支互斥且有超时、重试和失败状态。
- 普通测试不访问真实 LangExtract、MinerU、回答模型或 MCP。
- 部署文档包含模型、MCP、数据库、Chroma、Media 和备份配置。
- 所有外部密钥只存在后端环境，不进入前端构建产物。

### 16.3 产出

- 文章版本更新策略；
- 删除和下架清理策略；
- 真实文件导入验收；
- 单机部署和备份恢复说明；
- 已知限制和演示脚本。

### 16.4 完成标准

全新环境能够根据部署文档启动；文章、向量、来源、私密范围和 MCP 配置可以恢复；更新、删除、下架、导入和重试不会破坏问答权限和来源可信度。

## 17. 阶段状态和重新执行范围

| 阶段 | 当前状态 | 说明 |
| --- | --- | --- |
| Stage 0 | 部分具备 | 基础状态存在，但统一数据契约和本期范围仍需固定 |
| Stage 1 | 部分具备 | Markdown 处理链存在，MinerU/LangExtract 仍需稳定性收口 |
| Stage 2 | 部分具备 | 索引入口和状态字段存在，更新版本和失败闭环需验收 |
| Stage 3 | 部分具备 | Embedding 和 Chroma 已有基础实现，增强输入和全量重索引未完成 |
| Stage 4 | 未完成 | 意图判断和闲聊分流未完成 |
| Stage 5 | 未完成 | 私密知识库和用户授权范围未完成 |
| Stage 6 | 未完成 | 关键词检索、混合排序和无效问题门禁未完成 |
| Stage 7 | 部分具备 | 回答清洗和基础门禁存在，动态上下文未完成 |
| Stage 8 | 未完成 | 联网搜索开关、MCP 适配器和网络来源未完成 |
| Stage 9 | 部分具备 | 基础问答页面存在，三态、来源类型和联网开关未完成 |
| Stage 10 | 未完成 | 没有固定 RAG 评估集和质量报告 |
| Stage 11 | 未完成 | 文章版本化更新、导入和部署交付尚未全部验收 |

阶段不是全部完成后才开始下一阶段。允许在前一阶段已有稳定契约后并行开发，但不得跳过依赖：

- Stage 5 必须先于私密检索和联网来源合并；
- Stage 6 必须先于动态上下文质量评估；
- Stage 7 必须先于回答模型和前端来源展示验收；
- Stage 8 必须先于联网开关的前端联调；
- Stage 10 必须在检索、上下文、权限和联网逻辑稳定后执行。

## 18. 最终交付判定

项目只有同时满足以下条件，才能声明 RAG 达到最终交付水平：

1. 文章从创建/导入、审核、索引、发布到下架的状态链路完整。
2. 文章片段、Embedding、Chroma 向量和来源可以相互追溯。
3. 标题、摘要和正文增强输入不会污染真实正文来源。
4. 闲聊不访问知识库、模型或 MCP。
5. 混合检索支持中文、数字、英文、标题、摘要和正文短语。
6. 检索结果经过当前用户权限过滤，私密内容不跨用户泄露。
7. 联网搜索关闭时绝不调用 MCP。
8. 联网搜索开启时网页来源可追溯，且私密内容不发送给 MCP。
9. 动态上下文有明确预算、排序、去重和来源追溯。
10. 无来源不调用回答模型，并返回 `abstained`。
11. 前端正确区分 `casual`、`grounded`、`abstained` 和服务错误。
12. RAG 评估集、检索指标、回答指标、权限指标和性能指标达到设定门槛。
13. 已发布文章更新不会覆盖旧索引或造成旧版本泄露。
14. 普通测试不依赖真实外部服务，部署和备份流程可重复执行。

在以上条件全部满足前，项目只能描述为“具备 RAG 基础能力”，不能描述为“最终交付完成”。
