"""来源处理编排，负责路由、解析和结构化抽取，不负责清洗、切分向量化或发布"""
from dataclasses import dataclass, field
from typing import Any
from .document_types import ExtractionResult, ParsedDocument
from .source_router import build_document_from_source

@dataclass
class PreparedSource:
    """阶段2最终输出，交给阶段3清洗"""
    document: ParsedDocument
    # 统一解析后的文档
    extraction: ExtractionResult
    # 结构化抽取结果
    metadata: dict[str, Any] = field(default_factory=dict)
    # 供后续 chunk 继承的文档元数据


def prepare_source_for_indexing(
    *,
    source_type: str,
    source_name: str,
    markdown: str | None=None,
    source_path: str | None = None,
) -> PreparedSource:
    """把一个来源准备成可进入阶段3的统一对象"""
    # 第一步： 将 Markdown 或原始文件统一转换为 parsedDocument
    document = build_document_from_source(
        source_type=source_type,
        markdown=markdown,
        source_path=source_path,
        source_name=source_name,
    )
    
    # 第二步：延迟导入 LangExtract，避免启动时依赖外部服务
    from .langextract_adapter import extract_structure

    # 第三步：对统一文档执行结构化抽取
    extraction = extract_structure(document=document)

    # 第四步：把来源和抽取信息汇总给后续清洗/切分阶段
    metadata = {
        "source_type": document.source_type,
        "source_name": document.source_name,
        "parser_version": document.parser_version,
        "extractor_name": extraction.extractor_name,
        "extractor_version": extraction.extractor_version,
        "extraction_fields": extraction.fields,
        "extraction_source_spans": extraction.source_spans,
        "extraction_warnings": extraction.warnings,
    }

    # 第五步：返回完整的阶段2输出
    return PreparedSource(
        document=document,
        extraction=extraction,
        metadata=metadata,
    )
