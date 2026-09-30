"""来源路由，只负责选择 Markdown 或 MinerU 入口，不负责清洗和向量化"""
from pathlib import Path
from .document_types import ParsedDocument, SourceBlock

class UnsupportedSourceError(ValueError):
    """输入来源类型不受支持"""

class EmptySourceError(ValueError):
    """输入没有可处理正文"""

def build_markdown_document(
    *,
    markdown: str,
    source_name: str,
) -> ParsedDocument:
    """将现有 Markdown 转为统一文档对象"""
    # 防止 None 或其他类型进入字符串处理
    if not isinstance(markdown, str):
        raise EmptySourceError("Markdown 内容必须是字符串")
    # 空文章无法进入后续清洗和索引
    if not markdown.strip():
        raise EmptySourceError("Markdown 内容不能为空")

    # 先保留整篇原文作为一个区块，后续清洗和切分阶段再细化区块
    block = SourceBlock(
        block_type="document",
        text=markdown,
        source_start=0,
        source_end=len(markdown),
    )

    # 返回统一对象，不修改原始 Markdown
    return ParsedDocument(
        source_type="markdown",
        markdown=markdown,
        blocks=[block],
        source_name=source_name,
        parser_version="direct-markdown-v1",
    )

def build_document_from_source(
    *,
    source_type: str,
    markdown: str | None=None,
    source_path: str | None=None,
    source_name: str="",
) -> ParsedDocument:
    """按照来源类型选择 Markdown 或 MinerU 入口"""
    # 当前博客文章走这里，不依赖 MinerU
    if source_type == "markdown":
        return build_markdown_document(
            markdown=markdown or "",
            source_name=source_name,
        )

    # 只有真正处理文件时才导入 MinerU 适配器
    if source_type == "mineru":
        from .mineru_adapter import parse_with_mineru
        # 没有文件路径无法解析原始文件
        if not source_path:
            raise EmptySourceError("MinerU 输入必须提供文件路径")
        path = Path(source_path)
        # 将解析工作交给指定适配器
        return parse_with_mineru(
            source_path=path,
            source_name=source_name or path.name,
        )
    # 未知来源必须显式失败，不能默认当成 Markdown
    raise UnsupportedSourceError(f"不支持的来源类型： {source_type}")
