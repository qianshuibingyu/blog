"""阶段2的 Article 来源入口，当前 Article.content 已经是 Markdown，所以先直接走 Markdown路径 """
from articles.models import Article
from .source_pipeline import PreparedSource, prepare_source_for_indexing

def prepare_article_source(article: Article) -> PreparedSource:
    """将 Article 转成阶段2的统一来源结果"""
    # 当前模型没有原始文件字段，正文来源就是 Article.content
    # 因此这里明确使用 markdown，不强行经过 MinerU
    return prepare_source_for_indexing(
        source_type="markdown",
        source_name=article.title,
        markdown=article.content,
    )