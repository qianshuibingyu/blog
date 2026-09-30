from django.test import TestCase, SimpleTestCase, override_settings
from unittest.mock import patch

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
from .document_types import ExtractionResult, ParsedDocument
from .source_pipeline import prepare_source_for_indexing, PreparedSource
from .source_router import (
    EmptySourceError,
    UnsupportedSourceError,
    build_document_from_source,
)

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
