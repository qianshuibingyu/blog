"""阶段 8：执行文章索引并在全部成功后发布"""
from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone
from articles.models import Article, ArticleStatus, IndexStatus
from .indexing import prepare_article_source
from .services.content_cleaner import clean_prepared_source
from .services.chunking import MarkdownTextChunker
from .services.article_chunks import persist_article_chunks
from .llm import EmbeddingService
from .vector_store import ChromaVectorStore

"""索引任一步骤失败或任务版本已过期"""
# 定义编排失败的统一异常
class IndexPipelineError(RuntimeError):
    pass

# 表示一次索引运行的最小结果
@dataclass(frozen=True)
class IndexReport:
    article_id: int
    chunk_count: int
    vector_count: int
    content_hash: str

# 同步执行一篇文章的完整索引流程
def run_article_index(*, article_id:int) -> IndexReport:
    # 只允许已经进入 indexing 的文章开始运行
    article = _load_indexing_article(article_id)
    # 将可预期的业务或外部错误统一转换为失败状态
    try:
        _set_step(article_id, "content_validation")      # 记录当前正在执行的阶段
        prepared = prepare_article_source(article)
        _set_step(article_id, "cleaning")        # 清洗前记录
        cleaned = clean_prepared_source(prepared)
        _set_step(article_id, "chunking")
        chunks = MarkdownTextChunker().split(cleaned)
        # 空片段不能继续进入数据库和向量库
        if not chunks:
            raise IndexPipelineError("切分后没有有效片段")
        _set_step(article_id, "persistence")       # 持久化前记录
        persist_article_chunks(article_id=article_id, text_chunks=chunks)
        _set_step(article_id, "embedding")    # 向量生成前记录
        embedded_chunks = EmbeddingService(client=None).embed_article_chunks(article_id=article_id)
        _set_step(article_id, "chroma")      # Chroma 写入前记录
        vector_count = ChromaVectorStore().upsert_article_chunks(article_id=article_id, embedded_chunks=embedded_chunks)
        # 最终确认版本未变化后发布
        _publish_if_current(article_id=article_id, content_hash=cleaned.content_hash)
        # 返回成功报告
        return IndexReport(
            article_id=article_id,
            chunk_count=len(chunks),
            vector_count=vector_count,
            content_hash=cleaned.content_hash,
        )
    # 捕获所有步骤异常，确保文章不会保持假成功状态
    except Exception as exc:
        # 写入失败步骤和安全错误摘要
        _mark_failed(article_id=article_id, step=_current_step(article_id), error=exc)
        raise IndexPipelineError(f"文章索引失败：{type(exc).__name__}") from exc

# 读取并检验文章当前状态
def _load_indexing_article(article_id:int) -> Article:
    # 捕获文章不存在异常
    try:
        article = Article.objects.get(pk=article_id)
    # 将不存在转换为编排错误
    except Article.DoesNotExist as exc:
        raise IndexPipelineError("文章不存在") from exc
    # 只有审核入口设置的 indexing 状态可运行
    if article.status != ArticleStatus.INDEXING or article.index_status != IndexStatus.INDEXING:
        raise IndexPipelineError("文章不处于可索引状态")
    return article     # 返回当前文章快照

# 保存当前执行步骤
def _set_step(article_id:int, step:str) -> None:
    # 使用条件更新避免覆盖已下架文章
    Article.objects.filter(
        pk=article_id,
        status=ArticleStatus.INDEXING,
        index_status=IndexStatus.INDEXING,
    ).update(index_step=step, index_error="")

# 读取失败时的当前步骤
def _current_step(article_id:int) -> str:
    # 没有文章时返回安全的 unknown
    return Article.objects.filter(pk=article_id).values_list("index_step", flat=True).first() or "unknown"

# 将文章写入不可公开的失败状态
def _mark_failed(*, article_id:int, step:str, error:Exception) -> None:
    # 只保留步骤和异常类型，避免泄露密钥或正文
    safe_error = f"{step}: {type(error).__name__}"
    # 只把仍在当前索引状态的文章标记失败
    Article.objects.filter(
        pk=article_id,
        status=ArticleStatus.INDEXING,
    ).update(
        status=ArticleStatus.INDEX_FAILED,
        index_status=IndexStatus.FAILED,
        index_step=step,
        index_error=safe_error,
        updated_at=timezone.now(),
    )

# 在发布前重新检查文章和片段是否仍属于当前任务
def _publish_if_current(*, article_id:int, content_hash:str) -> None:
    # 用短事务完成最终状态写回
    with transaction.atomic():
        # 锁定文章行但不持有外部网络请求
        article = Article.objects.select_for_update().get(pk=article_id)
        # 检查文章没有被其他操作改变
        if article.status != ArticleStatus.INDEXING or article.index_status != IndexStatus.INDEXING:
            raise IndexPipelineError("文章状态已变化，不能发布")
        # 检查已有哈希不与本次清洗结果冲突
        if article.content_hash and article.content_hash != content_hash:
            raise IndexPipelineError("文章内容哈希已变化，不能发布")
        # 保存文章所有信息
        article.content_hash = content_hash
        article.index_step = "completed"
        article.index_status = IndexStatus.INDEXED
        article.status = ArticleStatus.PUBLISHED
        article.index_error = ""
        article.embedding_error = ""
        article.chroma_error = ""
        article.indexed_at = timezone.now()
        article.save()