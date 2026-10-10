from types import SimpleNamespace
from django.test import TestCase, SimpleTestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import resolve
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
from .retrieval import InvalidQuestionError, RetrievalServiceError, retrieve_public_chunks, RetrievalReport, RetrievedChunk      # 导入阶段 9 真实入口
from .answering import AnswerModelError, answer_from_retrieval, build_prompt, clean_generated_answer, _source_payload     # 导入阶段 10 真实入口
from rest_framework.test import APIRequestFactory        # 构造 DRF 请求
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_503_SERVICE_UNAVAILABLE       # 导入断言状态码
from .api import KnowledgeChatAPIView                # 导入阶段 11 真实视图
from .answering import AnswerResult                 # 导入阶段 10 输出对象

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
    @patch("knowledge.source_pipeline.extract_structure")
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
    
    def test_structure_table_and_code_are_preserved(self):
        prepared = self.make_prepared_source(
            "# RAG\n\n"
            "- 保留列表\n\n"
            "| 名称 | 说明 |\n"
            "| Chroma | 向量数据库 |\n\n"
            "```python\nprint('hello')\n```"
        )
        result = clean_prepared_source(prepared)
        self.assertIsInstance(result, CleanedDocument)
        self.assertIn("# RAG", result.cleaned_markdown)
        self.assertIn("- 保留列表", result.cleaned_markdown)
        self.assertIn("Chroma", result.plain_text)
        self.assertIn("向量数据库", result.plain_text)
        self.assertIn("print('hello')", result.plain_text)

    def test_dangerous_content_is_removed(self):
        prepared = self.make_prepared_source(
            "# 安全测试\n\n"
            "<script>alert('xss')</script>\n\n"
            "<div onclick=\"alert('xss')\">正文</div>\n\n"
            "危险链接"
        )
        result = clean_prepared_source(prepared)
        self.assertNotIn("<script", result.sanitized_html.lower())
        self.assertNotIn("onclick", result.sanitized_html.lower())
        self.assertNotIn("javascript:", result.sanitized_html.lower())
        self.assertIn("正文", result.plain_text)
    
    def test_cleaning_does_not_mutate_input(self):
        raw = "# 标题\r\n\r\n这是一段足够长的正文"
        prepared = self.make_prepared_source(raw)
        clean_prepared_source(prepared)
        self.assertEqual(prepared.document.markdown, raw)

    def test_hash_is_deterministic(self):
        self.assertEqual(build_content_hash("相同正文"), build_content_hash("相同正文"))
        self.assertNotEqual(build_content_hash("正文 A"), build_content_hash("正文 B"))


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

# 验证文章片段映射结果包含 provider 和向量维度
class ArticleEmbeddingMappingTests(TestCase):
    # 创建测试文章和文章片段
    def setUp(self):
        user = get_user_model().objects.create_user(
            username="embedding-article-user",
            password="test-password",
        )
        self.article = Article.objects.create(
            author=user,
            title="Embedding 映射测试",
            content="# 测试正文",
        )
        self.chunk = ArticleChunk.objects.create(
            article=self.article,
            chunk_index=0,
            content="测试片段正文",
        )

    # 验证文章片段向量记录了 provider 和维度
    @override_settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="test-local-model",
        EMBEDDING_BATCH_SIZE=2,
    )
    # 定义不会访问网络的假本地模型
    def test_article_chunks_record_provider_and_dimension(self):
        class FakeLocalModel:
            def encode(self, texts, **kwargs):
                return [[0.1, 0.2] for _ in texts]

        result = EmbeddingService(
            client=FakeLocalModel(),
        ).embed_article_chunks(
            article_id=self.article.id,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].article_chunk_id, self.chunk.id)
        self.assertEqual(result[0].embedding_provider, "local")
        self.assertEqual(result[0].embedding_dimension, 2)


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
        item = EmbeddedChunk(
            article_chunk_id=self.chunk.id,
            chunk_index=0,
            content="正文",
            embedding=[0.1, 0.2],
            embedding_model="test-model",
            embedding_provider="local",
            embedding_dimension=2,
        )
        count = ChromaVectorStore(client=client).upsert_article_chunks(article_id=self.article.id, embedded_chunks=[item])
        self.assertEqual(count, 1)
        self.chunk.refresh_from_db()
        self.assertEqual(self.chunk.vector_document_id, f"article:{self.article.id}:chunk:0")
        collection.upsert.assert_called_once()
        metadata = collection.upsert.call_args.kwargs["metadatas"][0]
        self.assertEqual(metadata["embedding_provider"], "local")
        self.assertEqual(metadata["embedding_dimension"], "2")
        self.assertEqual(metadata["embedding_model"], "test-model")

        # 验证过期正文不会写入 Chroma
    def test_mismatched_content_is_rejected(self):
        client, collection = self.fake_client()

        item = EmbeddedChunk(
            article_chunk_id=self.chunk.id,
            chunk_index=0,
            content="旧正文",
            embedding=[0.1, 0.2],
            embedding_model="test-model",
            embedding_provider="local",
            embedding_dimension=2,
        )

        with self.assertRaises(VectorStoreError):
            ChromaVectorStore(
                client=client,
            ).upsert_article_chunks(
                article_id=self.article.id,
                embedded_chunks=[item],
            )

        collection.upsert.assert_not_called()

    @override_settings(
    CHROMA_COLLECTION_NAME="ownerblog_articles",
    EMBEDDING_COLLECTION_VERSION="model-v1",
    )
    def test_collection_name_contains_embedding_version(self):
        client, collection = self.fake_client()
        ChromaVectorStore(client=client)
        client.get_or_create_collection.assert_called_once_with(
            name="ownerblog_articles_model-v1"
        )



# 定义阶段 8 编排测试
class IndexPipelineTests(TestCase):
    # 准备处于 indexing 的测试文章
    def setUp(self):
        # 创建测试用户和索引中文章
        user = get_user_model().objects.create_user(username="pipeline-user", password="test-password")
        self.article = Article.objects.create(
            author=user,
            title="编排测试",
            content="# 编排测试\n\n这是一段足够长的测试正文，用于验证索引流程状态和错误记录。",
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
    
    # 模拟 Embedding 服务失败
    def test_embedding_failure_records_embedding_error(self):
        with patch(
            "knowledge.index_pipeline.EmbeddingService"
        )as embedding_service:
        # 配置 Embedding 实例在生成向量时抛出异常
            embedding_service.return_value.embed_article_chunks.side_effect = (
                RuntimeError("embedding failed")
            )
            # 索引流程必须抛出统一的索引异常
            with self.assertRaises(IndexPipelineError):
                run_article_index(article_id=self.article.id)
        # 重新读取数据库中的文章状态
        self.article.refresh_from_db()
        # 文章必须进入索引失败状态
        self.assertEqual(self.article.status, ArticleStatus.INDEX_FAILED)
        self.assertEqual(self.article.index_status, IndexStatus.FAILED)
        # Embedding 错误字段必须有内容
        self.assertTrue(self.article.embedding_error)
        # 失败文章不能被发布
        self.assertNotEqual(self.article.status, ArticleStatus.PUBLISHED)

    # 同时模拟 Embedding 成功和 Chroma 写入失败
    def test_chroma_failure_records_chroma_error(self):
        with patch(
            "knowledge.index_pipeline.EmbeddingService"
        ) as embedding_service, patch(
            "knowledge.index_pipeline.ChromaVectorStore"
        ) as vector_store:
            # 模拟 Embedding 返回一个片段向量
            embedding_service.return_value.embed_article_chunks.return_value = [
                SimpleNamespace()
            ]
            # 模拟 Chroma 写入时抛出异常
            vector_store.return_value.upsert_article_chunks.side_effect = (
                RuntimeError("chroma failed")
            )
            # 索引流程必须抛出统一的索引异常
            with self.assertRaises(IndexPipelineError):
                run_article_index(article_id=self.article.id)
        # 重新读取数据库中的文章状态
        self.article.refresh_from_db()
        # 文章必须进入索引失败状态
        self.assertEqual(self.article.status, ArticleStatus.INDEX_FAILED)
        self.assertEqual(self.article.index_status, IndexStatus.FAILED)
        # Chroma 错误字段必须有内容
        self.assertTrue(self.article.chroma_error)
        # 失败文章不能被发布
        self.assertNotEqual(self.article.status, ArticleStatus.PUBLISHED)

    # 准备一个假的 Embedding 结果
    def test_embedding_is_called_on_service_instance(self):
        fake_embedded_chunks = [SimpleNamespace()]
        # 只替换实例方法，保留 EmbeddingService 类本身
        with patch.object(
            EmbeddingService,
            "embed_article_chunks",
            return_value=fake_embedded_chunks,
        ) as embed_chunks, patch(
            "knowledge.index_pipeline.ChromaVectorStore"
        ) as vector_store, patch(
            "knowledge.index_pipeline.prepare_article_source"
        ) as prepare, patch(
            "knowledge.index_pipeline.clean_prepared_source"
        ) as clean, patch(
            "knowledge.index_pipeline.MarkdownTextChunker"
        )as chunker, patch(
            "knowledge.index_pipeline.persist_article_chunks"
        ):
            # 模拟 Stage 2 返回的来源对象
            prepare.return_value = SimpleNamespace()
            # 模拟 Stage 3 返回的清洗对象
            clean.return_value = SimpleNamespace(content_hash="hash-001")
            # 模拟 Stage 4 返回一个文本片段
            chunker.return_value.split.return_value = [SimpleNamespace()]
            # 模拟 Chroma 写入成功
            vector_store.return_value.upsert_article_chunks.return_value = 1
            # 执行真实索引编排函数
            run_article_index(article_id=self.article.id)
        # 确认方法是通过 EmbeddingService 实例调用的
        embed_chunks.assert_called_once_with(article_id=self.article.id)

    

# 定义阶段 9 的公开检索测试
class PublicRetrievalTests(SimpleTestCase):
    # 验证空问题不会调用外部服务
    def test_empty_question_is_rejected(self):
        # 断言输入异常类型正确
        with self.assertRaises(InvalidQuestionError):
            # 传入空白问题
            retrieve_public_chunks(question="   ", embedding_service=MagicMock(), vector_store=MagicMock())

    # 替换真实 ORM 管理器，避免依赖测试数据
    @patch("knowledge.retrieval.ArticleChunk.objects")
    # 验证结果正文来自数据库
    def test_only_public_database_chunks_are_returned(self, objects):
        # 构造公开文章对象、数据库片段、让 ORM 链返回公开片段、构造固定查询向量服务和Chroma结果
        article = SimpleNamespace(id=1, title="公开文章")
        chunk = SimpleNamespace(id=10, article_id=1, article=article, chunk_index=0, content="数据库正文", vector_document_id="article:1:chunk:0")
        objects.filter.return_value.select_related.return_value = [chunk]
        embedder = SimpleNamespace(embed_query=lambda valuer:[0.1, 0.2])
        store = SimpleNamespace(query=lambda vector, top_k: [{"id": "article:1:chunk:0", "distance": 0.1}])
        # 覆盖测试阈值
        with self.settings(SIMILARITY_THRESHOLD=0.5, MAX_RETRIEVED_CHUNKS=5, CHROMA_QUERY_TOP_K=20):
            # 执行真实检索入口
            report = retrieve_public_chunks(question="公开文章内容", embedding_service=embedder, vector_store=store)
            # 确认正文不是来自 Chroma 返回值、接收数量正确
            self.assertEqual(report.results[0].content, "数据库正文")
            self.assertEqual(report.accepted_count, 1)

# 定义阶段 10 回答服务测试
class AnsweringServiceTests(SimpleTestCase):
    # 验证回答清洗会删除模型引用标记和重复来源，但保留实际答案。
    def test_clean_generated_answer_removes_model_markup(self):
        raw = "蓝色鲸鱼 9183【source-2】。\n来源：Cosine索引验收文章"
        self.assertEqual(clean_generated_answer(raw), "蓝色鲸鱼 9183。")

    # 构造带真实来源字段的检索报告
    def report_with_source(self):
        item = RetrievedChunk(1, "公开文章", 10, 0, "资料正文", 0.9, "article:1:chunk:0")
        # 返回阶段 9 报告
        return RetrievalReport("测试问题", [item], 1, 1)
    
    # 验证无来源时直接 bstained
    def test_empty_report_does_not_call_model(self):
        client = MagicMock()
        report = RetrievalReport("没有档案的问题", [], 0, 0)
        result = answer_from_retrieval(report, client=client)
        self.assertEqual(result.status, "abstained")
        client.chat.completions.create.assert_not_called()

    # 设置测试模型配置、验证成功回答携带来源
    @override_settings(MODEL_API_KEY="test-key", MODEL_BASE_URL="https://example.invalid", MODEL_NAME="test-model", LLM_TIMEOUT_SECONDS=1)
    def test_success_returns_real_sources(self):
        # 构造正常模型响应、假模型客户端
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="有依据的回答"))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda ** kwargs:response)))
        # 执行回答服务
        result = answer_from_retrieval(self.report_with_source(), client=client)
        # 确认回答状态和来源来自检索结果
        self.assertEqual(result.status, "grounded")
        self.assertEqual(result.sources[0]["article_id"], 1)

    # 设置测试模型配置
    @override_settings(MODEL_API_KEY="test-key", MODEL_BASE_URL="https://example.invalid", MODEL_NAME="test-model", LLM_TIMEOUT_SECONDS=1)
    # 验证模型空响应不会伪装成功
    def test_empty_model_response_is_error(self):
        # 构造空回答响应、假模型客户端
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=""))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwarts:response)))
        # 断言空回答会抛出明确异常
        with self.assertRaises(AnswerModelError):
            # 执行回答服务
            answer_from_retrieval(self.report_with_source(), client=client)

        # 设置测试模型配置
        @override_settings(MODEL_API_KEY="test-key", MODEL_BASE_URL="https://example.invalid", MODEL_NAME="test-model", LLM_TIMEOUT_SECONDS=1)
        # 验证模型异常被转换为统一错误
        def test_model_exception_is_wrapped(self):
            # 定义总是失败的假模型调用
            def raise_error(**kwargs):
                raise RuntimeError("network failure")
            # 构造失败客户端
            client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=raise_error)))
            # 断言服务抛出统一回答异常
            with self.assertRaises(AnswerModelError):
                answer_from_retrieval(self.report_with_source(), client=client)

    # 将模型上下文最大长度临时设置为20，验证 Prompt 中的资料不会超过配置长度
    @override_settings(MAX_CONTEXT_CHARS=20)
    def test_prompt_context_is_limited(self):
        item = RetrievedChunk(
            article_id=1,
            article_title="公开文章",
            article_chunk_id=10,
            chunk_index=0,
            content="这是一个超过二十个字符的长资料内容。",
            score=0.9,
            vector_document_id="article:1:chunk:0",
        )
        report = RetrievalReport(
            question="测试问题",
            results=[item],
            candidate_count=1,
            accepted_count=1,
        )
        prompt = build_prompt(report)
        self.assertIn(
            "资料：",
            prompt,
        )
        self.assertLessEqual(
            len(prompt.split("资料：\n", 1)[1]),
            20,
        )
    
    # 验证来源包含文章详情链接
    def test_sources_include_article_url(self):
        report = self.report_with_source()
        # 使用最小假模型响应，测试只关注来源链接字段。
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="有依据的回答"))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: response)))
        result = answer_from_retrieval(
            report,
            client=client,
        )
        self.assertEqual(
            result.sources[0]["article_url"],
            "/articles/1",
        )

# 定义阶段 11 API 测试
class KnowledgeChatAPITests(SimpleTestCase):
    # 为每个测试创建请求工厂
    def setUp(self):
        self.factory = APIRequestFactory()
    # 替换回答服务、检索服务
    @patch("knowledge.api.answer_from_retrieval")
    @patch("knowledge.api.retrieve_public_chunks")
    # 验证成功响应结构
    def test_success_response_contains_answer_and_sources(self, retrieve, answer):
        retrieve.return_value = RetrievalReport("问题", [], 0, 0)
        answer.return_value = AnswerResult("abstained", "资料不足", [])
        request = self.factory.post("/api/knowledge/chat", {"question":"问题"}, format="json")
        response = KnowledgeChatAPIView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["status"], "abstained")
        retrieve.assert_called_once_with(question="问题")

    # 验证空问题返回参数错误
    def test_invalid_payload_returns_400(self):
        request = self.factory.post("/api/knowledge/chat", {"question":""}, format="json")
        # 模拟阶段 9  参数校验失败
        with patch("knowledge.api.retrieve_public_chunks", side_effect=InvalidQuestionError("question 不能为空")):
            response = KnowledgeChatAPIView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    # 验证外部检索或模型失败时返回稳定的服务不可用响应
    def test_service_failure_returns_503(self):
        request = self.factory.post("/api/knowledge/chat", {"question": "问题"}, format="json")
        with patch("knowledge.api.retrieve_public_chunks", side_effect=RetrievalServiceError("检索失败")):
            response = KnowledgeChatAPIView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "知识问答服务暂时不可用，请稍后重试")


class ArticleContentPreservationTests(TestCase):
    @patch("knowledge.langextract_adapter.extract_structure")
    def test_cleaning_does_not_modify_article_content(self, extract_structure):
        extract_structure.return_value = ExtractionResult()
        user = get_user_model().objects.create_user(
            username="stage3-user",
            password="password",
        )
        raw = "# 原始标题\r\n\r\n这是一段足够长的原始正文。"
        article = Article.objects.create(
            author=user,
            title="Stage 3 测试",
            content=raw,
        )
        prepared = prepare_source_for_indexing(
            source_type="markdown",
            source_name=article.title,
            markdown=article.content,
        )
        clean_prepared_source(prepared)
        article.refresh_from_db()
        self.assertEqual(article.content, raw)

# 测试知识问答 URL 是否正确连接到视图
class KnowledgeRouteTests(SimpleTestCase):
    # 为每个路由测试创建 DRF 请求工厂
    def setUp(self):
        self.factory = APIRequestFactory()

    # 解析完整接口路径
    def test_chat_route_resolves(self):
        match = resolve("/api/knowledge/chat")
        self.assertEqual(match.view_name, "knowledge-chat",)
    
    # 构造一个模拟请求
    def test_grounded_response_contains_required_fields(self):
        request = self.factory.post(
            "/api/knowledge/chat",
            {"question": "什么事 RAG？"},
            format="json",
        )
        report = RetrievalReport(
            "什么是 RAG？", [], 0, 0,
        )
        answer = AnswerResult(
            "abstained",
            "没有足够资料回答该问题",
            [],
        )
        with patch("knowledge.api.retrieve_public_chunks", return_value=report,):
            with patch(
                "knowledge.api.answer_from_retrieval",
                return_value=answer,
            ):
                response = KnowledgeChatAPIView.as_view()(request)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(set(response.data.keys()), {"status", "answer", "sources"},)
        self.assertEqual(response.data["status"], "abstained")
        self.assertEqual(response.data["answer"], "没有足够资料回答该问题",)
        self.assertEqual(response.data["sources"], [])
