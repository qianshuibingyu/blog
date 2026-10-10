"""阶段3的Markdown清洗器"""
import hashlib
from html.parser import HTMLParser
from typing import Any

import bleach
import markdown

from .content_types import CleanedDocument
from .content_validation import validate_markdown_content
from .errors import SourceValidationError

# 只允许 Markdown 常见结构对应的 HTML 标签
ALLOWED_TAGS = [
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "del", "blockquote", "ul", "ol", "li",
    "pre", "code", "table", "thead", "tbody", "tr", "th", "td", "a",
]

# 只允许必要属性，拒绝 onclick、style 等执行或任意样式属性
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
}

# 只允许安全链接协议，禁止 javascript: 等危险协议
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

class PlainTextExtractor(HTMLParser):
    """从安全 HTML 提取保留结构边界的纯文本"""
    # 这些标签结束时补换行，避免段落和标题粘在一起
    BLOCK_TAGS = {
        "p", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "blockquote", "pre", "tr",
    }

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        # 只保存标签中的文字内容
        self.parts.append(data)
    
    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
    # br 没有结束标签，在开始位置补换行
        if tag == "br":
            self.parts.append("\n")
    
    def handle_endtag(self, tag: str) -> None:
        # 块级标签结束时补换行，保留结构边界
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def get_text(self) -> str:
        """返回规范化后的纯文本"""
        text = "".join(self.parts)
        lines = [line.rstrip() for line in text.splitlines()]
        result: list[str] = []
        blank_count = 0

        for line in lines:
            if line.strip():
                # 保留非空行，但去掉两侧无意义空白
                result.append(line.strip())
                blank_count = 0
                continue

            # 最多保留一个空行作为段落边界
            blank_count += 1
            if blank_count <= 1:
                result.append("")

        return "\n".join(result).strip()

    def normalize_markdown(markdown_text: str) -> str:
        """统一换行、行尾空格和过多空行"""
        # Windows、旧 Mac 和 Unix 换行统一为 \n
        normalized = markdown_text.replace("\r\n", "\n")
        normalized = normalized.replace("\r", "\n")
        # 删除行尾空格，但不破坏行首缩进和代码内容
        normalized = "\n".join(
            line.rstrip()
            for line in normalized.split("\n")
        )
        # 连续三个以上换行压缩为两个，仍保留段落边界
        while "\n\n\n" in normalized:
            normalized = normalized.replace("\n\n\n", "\n\n")
        return normalized.strip()

    def render_markdown(markdown_text: str) -> str:
        """将 Markdown 渲染为 HTML"""
        # fenced_code 保留代码块，tables 保留表格，nl2br 保留换行
        return markdown.markdown(
            markdown_text,
            extensions=["fenced_code", "tables", "nl2br"],
        )

    def sanitize_html(html: str) -> str:
        """删除危险标签、属性和链接协议"""
        return bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            protocols=ALLOWED_PROTOCOLS,
            strip=True,
        )
    
    def html_to_plain_text(html: str) -> str:
        """将安全 HTML 转成适合切分的纯文本"""
        parser = PlainTextExtractor()
        parser.feed(html)
        parser.close()
        return parser.get_text()

    def build_content_hash(text: str) -> str:
        """为清洗后的纯文本生成稳定 SHA-256"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def clean_prepared_source(prepared_source) -> CleanedDocument:
        """清洗阶段2的PreparedSource，并返回阶段3结果，参数使用阶段2的PreparedSource，避免引用已经废弃的ExtractedDocument 或 source_types 结构"""
        # 读取阶段2的统一Markdown输入
        original_markdown = prepared_source.document.markdown
        # 先校验，再执行任何格式处理
        validate_markdown_content(original_markdown)
        # 归一化只修改内存中的字符串，不会写回 Article.content
        cleaned_markdown = PlainTextExtractor.normalize_markdown(original_markdown)
        # 将 Markdown 转 HTML，方便进行结构化安全过滤
        rendered_html = PlainTextExtractor.render_markdown(cleaned_markdown)
        # 删除 script、style、事件属性和危险链接协议
        sanitized_html = PlainTextExtractor.sanitize_html(rendered_html)
        # 从安全 HTML 提取保留段落边界的纯文本
        plain_text = PlainTextExtractor.html_to_plain_text(sanitized_html)
        # 清洗后没有有效正文时停止，不进入阶段4
        if not plain_text.strip():
            raise SourceValidationError("Markdown 清洗后没有有效正文")
        # 使用清洗后的纯文本计算内容指纹
        content_hash = PlainTextExtractor.build_content_hash(plain_text)
        # 复制阶段2 metadata，避免修改 PreparedSource
        metadata: dict[str, Any] = dict(
            prepared_source.metadata or {}
        )
        metadata.update(
            {
                "original_length": len(original_markdown),
                "cleaned_length": len(plain_text),
                "content_hash": content_hash,
            }
        )
        # 返回阶段3结果，不写数据库、不修改文章状态
        return CleanedDocument(
            cleaned_markdown=cleaned_markdown,
            sanitized_html=sanitized_html,
            plain_text=plain_text,
            content_hash=content_hash,
            original_length=len(original_markdown),
            cleaned_length=len(plain_text),
            metadata=metadata,
        )


# Public module-level API used by the pipeline and tests.
def build_content_hash(text: str) -> str:
    return PlainTextExtractor.build_content_hash(text)


def clean_prepared_source(prepared_source) -> CleanedDocument:
    return PlainTextExtractor.clean_prepared_source(prepared_source)
