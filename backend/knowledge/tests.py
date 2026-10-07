from types import SimpleNamespace
from django.test import TestCase, SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from articles.models import Article, ArticleStatus, IndexStatus
from unittest.mock import patch, MagicMock
from .models import ArticleChunk

from .services.content_cleaner import(
    build_content_hash,
    clean_prepared_source,
)
from .services.content_validation import(validate_markdown_content,)
from .services.content_types import CleanedDocument
from .services.chunk_types import TextChunk
from .services.chunking import(
    ChunkConfig,
    ChunkingError,
    MarkdownTextChunker,
)
from .services.errors import SourceValidationError
from .services.article_chunks import ChunkPersistenceError
from .services.article_chunks import persist_article_chunks
from .document_types import ExtractionResult, ParsedDocument
from .source_pipeline import prepare_source_for_indexing, PreparedSource
from .source_router import (
    EmptySourceError,
    UnsupportedSourceError,
    build_document_from_source,
)

from .llm import EmbeddingConfigurationError
from .llm import EmbeddingError
from .llm import EmbeddingResponseError
from .llm import EmbeddingService
from .llm import EmbeddedChunk

from .vector_store import ChromaVectorStore, VectorStoreError
from .index_pipeline import IndexPipelineError, run_article_index    # 导入阶段 8 真实入口

# Create your tests here.
"""测试 Markdown 是否能进入统一对象"""
class SourceRouterTests(SimpleTestCase):
    def test_markdown_returns_parsed_document(self):
        # 执行 Markdown 入口
        result = build_document_from_source(
            source_type="markdown",
            source_name="测试文章",
            markdown="# 标题\n\n正文",
        )
        
        self.assertEqual(result.source_type, "markdown")
        self.assertEqual(result.markdown, "# 标题\n\n正文")
        self.assertEqual(result.source_name, "测试文章")
        self.assertEqual(len(result.blocks), 1)

    # 空文章不得进入后续流程
    def test_empty_markdown_is_rejected(self):
        with self.assertRaises(EmptySourceError):
            build_document_from_source(
                source_type="markdown",
                source_name="空文章",
                markdown="   ",
            )

    # 未知来源不得静默当成 Markdown
    def test_unknown_source_is_rejected(self):
        with self.assertRaises(UnsupportedSourceError):
            build_document_from_source(
                source_type="unknown",
                source_name="未知来源",
                markdown="正文",
            )

"""测试阶段2的编排，不调用真实 LangExtract"""
class SourcePipelineTests(SimpleTestCase):
    @patch("knowledge.langextract_adapter.extract_structure")
    def test_pipeline_returns_prepared_source(self, mock_extract):
        # 用固定结果代替真实抽取服务
        mock_extract.return_value = ExtractionResult(
            fields={"topics": ["Django"]},
            source_spans=[
                {
                    "field": "topics",
                    "value": "Django",
                    "source_start": 0,
                    "source_end": 6,
                }
            ],
            extractor_name="fake-langextract",
            extractor_version="test",
        )

        # 执行阶段2主流程
        result = prepare_source_for_indexing(
            source_type="markdown",
            source_name="测试文章",
            markdown="# Django\n\n正文",
        )
        # 确认统一文档被保留
        self.assertEqual(result.document.source_type, "markdown")
        # 确认抽取字段被保留
        self.assertEqual(
            result.extraction.fields["topics"],
            ["Django"],
        )
        # 确认 metadata 可以传给阶段3
        self.assertEqual(
            result.metadata["extractor_name"],
            "fake-langextract",
        )
        
        # 确认抽取器被调用一次
        mock_extract.assert_called_once()

"""验证清洗前的输入边界"""
class ContentValidationTests(SimpleTestCase):
    # 空白文章不能进入 Markdown 渲染器
    def test_empty_content_is_rejected(self):
        with self.assertRaises(SourceValidationError):
            validate_markdown_content("  \n  ")
    # 非字符串说明上游没有遵循输入契约
    def test_non_string_content_is_rejected(self):
        with self.assertRaises(SourceValidationError):
            validate_markdown_content(None)

"""验证 PreparedSource 到 CleanedDocument 的转换"""
class ContentCleanerTests(SimpleTestCase):
    def make_prepared_source(self, markdown_text: str):
        # 构造阶段2的 ParsedDocument
        document = ParsedDocument(
            source_type="markdown",
            markdown=markdown_text,
            source_name="test.md",
            parser_version="test",
        )
        # 构造阶段2的抽取结果
        extraction = ExtractionResult(
            fields={"topics": ["RAG"]},
            source_spans=[],
            extractor_name="fake-langextract",
            extractor_version="test",
        )
        # 构造清洗器真实接收的 PreparedSource
        return PreparedSource(
            document=document,
            extraction=extraction,
            metadata={
                "source_name": "test.md",
                "topics": ["RAG"],
            },
        )

    def test_markdown_structure_is_preserved(self):
        # 标题、列表和代码块验证结构内容没有丢失
        prepared = self.make_prepared_source(
            "# RAG\n\n"
            "## 清洗\n\n"
            "- 保留标题\n"
            "- 保留列表\n\n"
            "```python\n"
            "print('hello')\n"
            "```"
        )
        # 执行阶段3清洗
        result = clean_prepared_source(prepared)
        # 清洗后的 Markdown 保留关键结构
        self.assertIn("# RAG", result.cleaned_markdown)
        self.assertIn("- 保留列表", result.cleaned_markdown)
        self.assertIn("print('hello')", result.cleaned_markdown)
        # 纯文本也保留主要内容
        self.assertIn("RAG", result.plain_text)
        self.assertIn("保留标题", result.plain_text)
        self.assertIn("print('hello')", result.plain_text)
        # 阶段2的 metadata 继续向后传递
        self.assertEqual(result.metadata["topics"], ["RAG"])
        # 返回值必须是阶段3定义的数据结构
        self.assertIsInstance(result, CleanedDocument)

    def test_dangerous_html_is_removed(self):
        # 构造脚本、事件属性和危险协议
        prepared = self.make_prepared_source(
            "# 安全测试\n\n"
            "<script>alert('xss')</script>\n\n"
            "<div onclick=\"alert('xss')\">正文</div>\n\n"
            "危险链接"
        )
        # 执行清洗
        result = clean_prepared_source(prepared)
        # 危险标签、属性和协议不得出现在安全 HTML
        self.assertNotIn("<script", result.sanitized_html.lower())
        self.assertNotIn("onclick", result.sanitized_html.lower())
        self.assertNotIn("javascript:", result.sanitized_html.lower())
        # 正文文本仍然保留
        self.assertIn("正文", result.plain_text)

    def test_cleaning_does_not_mutate_input(self):
        # 保留原始字符串，验证清洗只处理副本
        raw_markdown = "# 测试标题\r\n\r\n这是一段足够长的正文内容   "
        prepared = self.make_prepared_source(raw_markdown)
        # 执行清洗
        clean_prepared_source(prepared)
        # PreparedSource 中的原文必须保持原样
        self.assertEqual(
            prepared.document.markdown,
            raw_markdown,
        )

    def test_same_plain_text_has_same_hash(self):
        # 相同正文应该得到相同哈希
        self.assertEqual(
            build_content_hash("同一段正文"),
            build_content_hash("同一段正文"),
        )

    def test_hash_changes_when_plain_text_changes(self):
        # 正文变化时哈希应该变化
        self.assertNotEqual(
            build_content_hash("正文 A"),
            build_content_hash("正文 B"),
        )

    @override_settings(CONTENT_MAX_LENGTH=5)
    def test_content_over_limit_is_rejected(self):
        # 使用临时配置验证最大长度限制
        with self.assertRaises(SourceValidationError):
            validate_markdown_content("123456")

"""验证阶段 4 的切分契约"""
class TextChunkerTests(SimpleTestCase):
    # 构造测试用 CleanedDocument
    def make_document(self, text, metadata=None):
        # 返回阶段 3 的输入对象
        return CleanedDocument(
            cleaned_markdown=text,
            sanitized_html="",
            plain_text=text,
            content_hash="hash-001",
            original_length=len(text),
            cleaned_length=len(text),
            metadata=metadata or {
                "article_id": 1,
                "article_version": 3,
                "source_type": "markdown",
            },
        )
    # 创建指定配置的切分起
    def chunker(self, size=100, overlap=20, minimum=10, maximum=20):
        return MarkdownTextChunker(
            config=ChunkConfig(size, overlap, minimum, maximum),
        )
    # 测试短文只产生一个片段
    def test_short_document_has_one_chunk(self):
        chunks = self.chunker().split(self.make_document("# 标题\n\n正文"))
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertIsInstance(chunks[0], TextChunk)
    # 测试 TextChunk 字段契约
    def test_explicit_contract_fields_are_populated(self):
        chunk = self.chunker().split(self.make_document("# 标题\n\n正文"))[0]
        self.assertEqual(chunk.content_length, len(chunk.content))
        self.assertEqual(chunk.content_hash, "hash-001")
        self.assertEqual(chunk.version, 3)
        self.assertEqual(chunk.metadata["article_id"], 1)
    # 测试长文长度和序号
    def test_long_text_has_continuous_indexes_and_max_length(self):
        document = self.make_document("长文本" * 200)
        chunks = self.chunker(size=50, overlap=10).split(document)
        self.assertGreater(len(chunks), 1)
        self.assertEqual([item.chunk_index for item in chunks], list(range(len(chunks))))
        self.assertTrue(all(item.content_length <= 50 for item in chunks))
    # 测试 overlap 超长时被舍弃
    def test_overlap_is_dropped_when_it_would_overflow(self):
        document = self.make_document("第一段" * 10 + "\n\n" + "第二段" * 10)
        chunks = self.chunker(size=30, overlap=20).split(document)
        self.assertTrue(all(item.content_length <= 30 for item in chunks))
    # 测试章节变化时不跨章节 overlap
    def test_section_change_does_not_carry_overlap(self):
        document = self.make_document("# 第一章\n\n" + "甲" * 60 + "\n\n# 第二章\n\n乙")
        chunks = self.chunker(size=40, overlap=10).split(document)
        second = next(item for item in chunks if item.section == "第二章")
        self.assertTrue(second.content.startswith("# 第二章"))
    def test_same_input_is_deterministic(self):
        document = self.make_document("# 稳定\n\n" + "正文" * 100)
        first = self.chunker().split(document)
        second = self.chunker().split(document)
        self.assertEqual(first, second)
    # 测试片段数量上限
    def test_max_chunk_count_is_enforced(self):
        document = self.make_document("正文" * 1000)
        with self.assertRaises(ChunkingError):
            self.chunker(size=20, overlap=2, maximum=2).split(document)

"""定义切分配置边界测试类"""
class ChunkConfigTests(SimpleTestCase):
    # 测试 overlap 必须小于片段长度
    def test_overlap_must_be_smaller_than_size(self):
        with self.assertRaises(ChunkingError):
            ChunkConfig(10, 10, 2, 10).validate()
    # 测试最小长度不能超过最大长度
    def test_minimum_cannot_exceed_size(self):
        with self.assertRaises(ChunkingError):
            ChunkConfig(10, 2, 11, 10).validate()


# 定义阶段 5 数据库测试
class ArticleChunkPersistenceTests(TestCase):
    # 准备测试数据
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="chunk-user", password="test-password")       # 创建测试用户
        self.article = Article.objects.create(author=self.user, title="切片测试", content="# 原文")    # 创建测试文章
            # 根据正文构造片段
    def make_chunks(self, contents):
        return [
            TextChunk(index, content, len(content), "hash-001", 1, "正文", {})
            for index, content in enumerate(contents)
        ]

    # 验证保存和替换
    def test_persists_and_replaces_chunks(self):
        first_count = persist_article_chunks(
            article_id=self.article.id,
            text_chunks=self.make_chunks(["第一段", "第二段"]),
        )
        second_count = persist_article_chunks(
            article_id=self.article.id,
            text_chunks=self.make_chunks(["新正文"]),
        )
        self.assertEqual(first_count, 2)
        self.assertEqual(second_count, 1)
        self.assertEqual(
            list(self.article.chunks.values_list("content", flat=True)),
            ["新正文"],
        )  # 确认旧片段被替换

    # 验证非法输入不删除旧数据
    def test_invalid_input_does_not_delete_old_data(self):
        persist_article_chunks(
            article_id=self.article.id,
            text_chunks=self.make_chunks(["保留正文"]),
        )  # 保存有效片段
        invalid = [TextChunk(1, "错误", 2, "hash-001", 1, "正文", {})]  # 构造错误序号
        with self.assertRaises(ChunkPersistenceError):  # 断言输入校验失败
            persist_article_chunks(
                article_id=self.article.id,
                text_chunks=invalid,
            )
        self.assertEqual(self.article.chunks.count(), 1)

    # 验证空输入
    def test_empty_input_is_rejected(self):
        with self.assertRaises(ChunkPersistenceError):
            persist_article_chunks(article_id=self.article.id, text_chunks=[])


# 定义阶段 6 纯内存测试
class EmbeddingServiceTests(SimpleTestCase):
    # 构造假 OpenAI-compatible 响应
    def response(self, vectors):
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=index, embedding=vector)
                for index, vector in enumerate(vectors)
            ]
        )

    # 远程 provider 保留原有的分批和数量契约
    @override_settings(
        EMBEDDING_PROVIDER="openai_compatible",
        EMBEDDING_MODEL="test-model",
        EMBEDDING_BATCH_SIZE=2,
        EMBEDDING_MAX_RETRIES=0,
    )
    def test_remote_batches_texts_and_preserves_count(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs["input"])
            return self.response([[1.0, 2.0] for _ in kwargs["input"]])

        client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
        result = EmbeddingService(client=client).embed_texts(["一", "二", "三"])
        self.assertEqual(calls, [["一", "二"], ["三"]])
        self.assertEqual(len(result), 3)

    # 本地 provider 使用注入的假 Sentence Transformer，不访问网络
    @override_settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="test-local-model",
        EMBEDDING_BATCH_SIZE=2,
    )
    def test_local_provider_uses_encode_and_batches(self):
        calls = []

        class FakeLocalModel:
            def encode(self, texts, **kwargs):
                calls.append((list(texts), kwargs))
                return [[0.1, 0.2] for _ in texts]

        result = EmbeddingService(client=FakeLocalModel()).embed_texts(
            ["第一段", "第二段", "第三段"]
        )

        self.assertEqual(len(result), 3)
        self.assertEqual([call[0] for call in calls], [["第一段", "第二段"], ["第三段"]])
        self.assertTrue(all(call[1]["normalize_embeddings"] for call in calls))
        self.assertTrue(all(call[1]["convert_to_numpy"] is False for call in calls))
        self.assertTrue(all(call[1]["show_progress_bar"] is False for call in calls))

    # BGE 查询指令只添加到本地查询文本
    @override_settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="test-local-model",
    )
    def test_local_query_uses_retrieval_instruction(self):
        calls = []

        class FakeLocalModel:
            def encode(self, texts, **kwargs):
                calls.append(list(texts))
                return [[0.1, 0.2]]

        result = EmbeddingService(client=FakeLocalModel()).embed_query("原始问题")

        self.assertEqual(len(result), 2)
        self.assertEqual(
            calls,
            [["为这个句子生成表示以用于检索相关文章：原始问题"]],
        )

    # 本地 provider 不构造 OpenAI client，并且延迟加载本地模型
    @override_settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="test-local-model",
        EMBEDDING_DEVICE="cpu",
    )
    @patch("knowledge.llm.OpenAI")
    @patch("knowledge.llm._load_local_model")
    def test_local_provider_does_not_construct_openai(self, load_model, openai):
        fake_model = SimpleNamespace(
            encode=lambda texts, **kwargs: [[0.1, 0.2] for _ in texts]
        )
        load_model.return_value = fake_model

        result = EmbeddingService().embed_texts(["本地文本"])

        self.assertEqual(result, [[0.1, 0.2]])
        openai.assert_not_called()
        load_model.assert_called_once_with("test-local-model", "cpu")

    # 本地向量结构和维度错误必须被拒绝
    @override_settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="test-local-model",
    )
    def test_local_invalid_vectors_are_rejected(self):
        class FakeLocalModel:
            def encode(self, texts, **kwargs):
                return [[float("nan")], [0.2, 0.3]][: len(texts)]

        with self.assertRaises(EmbeddingResponseError):
            EmbeddingService(client=FakeLocalModel()).embed_texts(["一", "二"])

    # provider 边界必须明确
    @override_settings(EMBEDDING_PROVIDER="unsupported")
    def test_unsupported_provider_is_rejected(self):
        with self.assertRaises(EmbeddingConfigurationError):
            EmbeddingService(client=SimpleNamespace())

    # 输入和远程响应错误仍然按原契约处理
    @override_settings(
        EMBEDDING_PROVIDER="openai_compatible",
        EMBEDDING_MODEL="test-model",
        EMBEDDING_MAX_RETRIES=0,
    )
    def test_invalid_input_and_response_are_rejected(self):
        with self.assertRaises(EmbeddingError):
            EmbeddingService(client=SimpleNamespace()).embed_texts(["   "])

        bad = SimpleNamespace(
            embeddings=SimpleNamespace(
                create=lambda **kwargs: self.response([[1.0], [2.0], [3.0]])
            )
        )
        with self.assertRaises(EmbeddingResponseError):
            EmbeddingService(client=bad).embed_texts(["一", "二"])

# 定义阶段 7 数据库和假 Chroma 测试
class ChromaVectorStoreTests(TestCase):
    # 准备一篇文章和一个片段
    def setUp(self):
        user = get_user_model().objects.create_user(username="vector-user", password="test-password")
        self.article = Article.objects.create(author=user, title="向量测试", content="# 正文", content_hash="hash-001")
        self.chunk = ArticleChunk.objects.create(article=self.article, chunk_index=0, content="正文")

    # 构造最小可用的 Chroma 假客户端
    def fake_client(self):
        collection = MagicMock()
        collection.name = "ownerblog_articles"
        client = MagicMock()
        client.get_or_create_collection.return_value = collection
        return client, collection

    # 验证向量写入和 ID 回写
    def test_upsert_writes_stable_id_and_mapping(self):
        client, collection = self.fake_client()
        item = EmbeddedChunk(self.chunk.id, 0, "正文", [0.1,0.2], "test-model")
        count = ChromaVectorStore(client=client).upsert_article_chunks(article_id=self.article.id, embedded_chunks=[item])
        self.assertEqual(count, 1)
        self.chunk.refresh_from_db()
        self.assertEqual(self.chunk.vector_document_id, f"article:{self.article.id}:chunk:0")
        collection.upsert.assert_called_once()

    # 验证过期正文不会写入 Chroma
    def test_mismatched_content_is_rejected(self):
        client, collection = self.fake_client()
        item = EmbeddedChunk(self.chunk.id, 0, "旧正文", [0.1,0.2], "test-model")
        # 断言服务拒绝过期结果
        with self.assertRaises(VectorStoreError):
            ChromaVectorStore(client=client).upsert_article_chunks(article_id=self.article.id, embedded_chunks=[item])
        # 确认校验失败前没有写库
        collection.upsert.assert_not_called()
# 定义阶段 8 编排测试
class IndexPipelineTests(TestCase):
    # 准备处于 indexing 的测试文章
    def setUp(self):
        # 创建测试用户和索引中文章
        user = get_user_model().objects.create_user(username="pipeline-user", password="test-password")
        self.article = Article.objects.create(
            author=user,
            title="编排测试",
            content="# 正文",
            status=ArticleStatus.INDEXING,
            index_status=IndexStatus.INDEXING,
        )

    # 替换 Chroma 写入服务、Embedding 服务、持久化服务、切分器、清洗器、来源入口
    @patch("knowledge.index_pipeline.ChromaVectorStore")
    @patch("knowledge.index_pipeline.EmbeddingService")
    @patch("knowledge.index_pipeline.persist_article_chunks")
    @patch("knowledge.index_pipeline.MarkdownTextChunker")
    @patch("knowledge.index_pipeline.clean_prepared_source")
    @patch("knowledge.index_pipeline.prepare_article_source")
    # 验证成功状态流转
    def test_success_publishes_only_after_all_steps(self, prepare, clean, chunker, persist, embedder, store):
        # 设置阶段2和3假对象、非空切片结果、非空向量结果、Chroma 写入数量
        prepare.return_value = SimpleNamespace()
        clean.return_value = SimpleNamespace(content_hash="hash-001")
        chunker.return_value.split.return_value = [SimpleNamespace()]
        embedder.return_value.embed_article_chunks.return_value = [SimpleNamespace()]
        store.return_value.upsert_article_chunks.return_value = 1
        # 执行真实编排入口
        report = run_article_index(article_id=self.article.id)
        # 重新读取文章状态
        self.article.refresh_from_db()
        # 确认返回向量数量、全部成功后才发布、索引状态完成
        self.assertEqual(report.vector_count, 1)
        self.assertEqual(self.article.status, ArticleStatus.PUBLISHED)
        self.assertEqual(self.article.index_status, IndexStatus.INDEXED)

    # 让阶段 2 模拟失败
    @patch("knowledge.index_pipeline.prepare_article_source", side_effect=ValueError("cleaning failed"))
    # 验证失败不会发布
    def test_failure_marks_article_failed(self, prepare):
        # 断言编排入口返回统一失败异常
        with self.assertRaises(IndexPipelineError):
            run_article_index(article_id=self.article.id)      # 执行失败路径

        # 重新读取失败状态
        self.article.refresh_from_db()
        # 确认文章进入索引失败、索引状态进入失败
        self.assertEqual(self.article.status, ArticleStatus.INDEX_FAILED)
        self.assertEqual(self.article.index_status, IndexStatus.FAILED)