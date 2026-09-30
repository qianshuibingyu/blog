"""阶段3输出的数据结构"""
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class CleanedDocument:
    """清洗后交给阶段4的文档"""
    cleaned_markdown: str
    # 保留标题和段落结构的规范化 Markdown
    sanitized_html: str
    # 经过安全标签、属性和协议过滤的 HTML
    plain_text: str
    # 从安全 HTML 提取的纯文本
    content_hash: str
    # 清洗后纯文本的 SHA-256 指纹
    original_length: int
    # 原始 Markdown 字符数
    cleaned_length: int
    # 清洗后纯文本字符数
    metadata: dict[str, Any] = field(default_factory=dict)
    # 从阶段2继承并补充的来源信息