"""阶段3的 Markdown 输入校验"""
from django.conf import settings
from .errors import SourceValidationError

""" 验证 Markdown 是否具备进入清洗流程的条件
    该函数只验证，不修改输入，也不执行 Markdown 渲染 """
def validate_markdown_content(markdown: str) -> str:
    # 类型错误说明上游没有按契约传递正文
    if not isinstance(markdown, str):
        raise SourceValidationError("Markdown 内容必须是字符串")

    # 全是空白的正文没有可索引知识
    if not markdown.strip():
        raise SourceValidationError("Markdown 内容不能为空")

    # 原始字符数超过限制时，立即拒绝，避免进入渲染器
    if len(markdown) > settings.CONTENT_MAX_LENGTH:
        raise SourceValidationError("Markdown 内容超过最大长度")
    
    # 这里只做最小可见内容判断，不修改将要返回的原文
    visible_text = markdown.replace("#", " ").strip()
    if len(visible_text) < settings.CONTENT_MIN_LENGTH:
        raise SourceValidationError("Markdown 有效正文过短")

    # 返回原始内容，清晰由下一个函数负责
    return markdown