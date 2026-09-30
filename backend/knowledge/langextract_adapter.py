"""LangExtract 适配器：只负责把 ParsedDocument 转换为 ExtractionResult。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# 从项目已有的 backend/.env 读取 LLM 配置，不在代码中硬编码密钥。
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from .document_types import ExtractionResult, ParsedDocument


class LangExtractAdapterError(RuntimeError):
    """LangExtract 适配器异常，避免把失败误报为成功。"""


def _build_examples(lx: Any) -> list[Any]:
    """构造最小示例，要求模型返回输入中的原文片段。"""
    return [
        lx.data.ExampleData(
            text="项目背景\n这是一个文档处理项目。",
            extractions=[
                lx.data.Extraction(
                    extraction_class="section_title",
                    extraction_text="项目背景",
                    attributes={"level": "1"},
                ),
                lx.data.Extraction(
                    extraction_class="topic",
                    extraction_text="文档处理项目",
                    attributes={},
                ),
            ],
        )
    ]


def _interval_values(interval: Any) -> tuple[int | None, int | None]:
    """兼容 LangExtract 不同版本的字符区间属性命名。"""
    if interval is None:
        return None, None
    start = getattr(interval, "start_pos", getattr(interval, "start", None))
    end = getattr(interval, "end_pos", getattr(interval, "end", None))
    return (start if isinstance(start, int) else None, end if isinstance(end, int) else None)


def _extract_fields(result: Any, document: ParsedDocument) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """把 LangExtract 输出转换成项目统一的字段和可定位来源片段。"""
    fields: dict[str, Any] = {"section_titles": [], "topics": [], "entities": []}
    source_spans: list[dict[str, Any]] = []
    warnings: list[str] = []
    for item in getattr(result, "extractions", []) or []:
        kind = str(getattr(item, "extraction_class", "")).strip().lower()
        text = getattr(item, "extraction_text", None)
        if not isinstance(text, str) or not text.strip():
            warnings.append("LangExtract 返回了缺少文本的抽取项，已忽略。")
            continue
        start, end = _interval_values(getattr(item, "char_interval", None))
        if start is None or end is None:
            warnings.append(f"抽取项未找到原文定位，已忽略：{kind or 'unknown'}。")
            continue
        entry = {"text": text, "attributes": getattr(item, "attributes", {}) or {}}
        if kind in {"section_title", "title", "heading", "章节标题"}:
            fields["section_titles"].append(entry)
        elif kind in {"topic", "主题"}:
            fields["topics"].append(entry)
        elif kind in {"entity", "实体"}:
            fields["entities"].append(entry)
        else:
            fields.setdefault("other", []).append({"class": kind, **entry})
        source_spans.append({"extraction_class": kind, "text": text, "start": start, "end": end})
    fields = {key: value for key, value in fields.items() if value}
    if not fields:
        warnings.append("LangExtract 未返回可定位的章节标题、主题或实体。")
    return fields, source_spans, warnings


def extract_structure(*, document: ParsedDocument) -> ExtractionResult:
    """从 Markdown ParsedDocument 抽取结构化元数据，不修改原 Markdown。"""
    # 校验统一输入，适配器不负责清洗、切分或发布。
    if not isinstance(document, ParsedDocument):
        raise TypeError("extract_structure 的 document 必须是 ParsedDocument。")
    if not isinstance(document.markdown, str) or not document.markdown.strip():
        raise ValueError("无法抽取结构：ParsedDocument.markdown 为空。")

    # 延迟导入依赖，使项目在未安装 LangExtract 时仍可导入其他模块。
    try:
        import langextract as lx
    except ImportError as exc:
        raise LangExtractAdapterError(
            "LangExtract 依赖不可用，请安装 langextract 后再调用 extract_structure。"
        ) from exc

    # 使用环境变量选择已配置的模型，不在异常或日志中输出密钥和正文。
    model_id = os.getenv("MODEL_NAME") or os.getenv("LANGEXTRACT_MODEL_ID") or os.getenv("LANGEXTRACT_MODEL")
    api_key = os.getenv("MODEL_API_KEY") or os.getenv("LANGEXTRACT_API_KEY")
    base_url = os.getenv("MODEL_BASE_URL")
    if not model_id or not api_key:
        raise LangExtractAdapterError(
            "未读取到项目 .env 中的 MODEL_NAME 或 MODEL_API_KEY，无法调用 LangExtract。"
        )
    try:
        # 仅传入 Markdown；不调用 Embedding、Chroma 或回答模型。
        extraction_kwargs = {
            "text_or_documents": document.markdown,
            "prompt_description": (
                "从 Markdown 中提取章节标题，以及原文中明确出现的主题或实体。"
                "extraction_text 必须逐字复制输入中的连续文本，不要改写或补充。"
            ),
            "examples": _build_examples(lx),
            "model_id": model_id,
            "api_key": api_key,
        }
        # 复用项目 .env 的 OpenAI-compatible 地址，不输出地址中的凭据。
        if base_url:
            extraction_kwargs["language_model_params"] = {"base_url": base_url}
        result = lx.extract(**extraction_kwargs)
    except Exception as exc:
        raise LangExtractAdapterError(
            f"LangExtract 抽取失败（{type(exc).__name__}），未生成伪造结果。"
        ) from exc

    # 只将抽取内容写入 ExtractionResult.metadata/fields，绝不覆盖 document.markdown。
    fields, source_spans, warnings = _extract_fields(result, document)
    return ExtractionResult(
        fields=fields,
        source_spans=source_spans,
        extractor_name="langextract",
        extractor_version=str(getattr(lx, "__version__", "unknown")),
        warnings=warnings,
    )
