"""定义数据对象，不调用MinerU、LangExtract、Embedding或Chroma。不同来源必须都转换成这里定义的对象"""
from dataclasses import dataclass, field
from typing import Any

# 解析结果的一个结构区块
@dataclass
class SourceBlock:
    block_type: str
    text: str
    level: int | None=None
    source_start: int | None=None
    source_end: int | None=None
    metadata: dict[str, Any] = field(default_factory=dict)


# Markdown 或 MinerU 的统一解析结果
@dataclass
class ParsedDocument:
    source_type: str
    markdown: str
    blocks: list[SourceBlock] = field(default_factory=list)
    source_name: str=""
    parser_version: str="manual"
    metadata: dict[str, Any] = field(default_factory=dict)

# LangExtract 返回的结构化信息
@dataclass
class ExtractionResult:
    fields: dict[str, Any] = field(default_factory=dict)
    source_spans: list[dict[str, Any]] = field(default_factory=list)
    extractor_name: str = "none"
    extractor_version: str = ""
    warnings: list[str] = field(default_factory=list)
    