"""阶段 5：把 TextChunk 原子替换为 ArticleChunk"""
from django.db import transaction
from articles.models import Article
from ..models import ArticleChunk
from .chunk_types import TextChunk

"""片段输入不符合持久化契约"""
class ChunkPersistenceError(ValueError):
    pass
    
"""只校验输入，不访问数据库"""
def validate_text_chunks(text_chunks: list[TextChunk]) -> None:
    # 检查容器类型
    if not isinstance(text_chunks, list):
        raise ChunkPersistenceError("text_chunks 必须是 list")
    # 检查列表不能为空
    if not text_chunks:
        raise ChunkPersistenceError("text_chunks 不能为空")
    # 检查元素类型
    if not all(isinstance(chunk, TextChunk) for chunk in text_chunks):
        raise ChunkPersistenceError("每一项必须是 TextChunk")
    # 读取片段序号
    indexes = [chunk.chunk_index for chunk in text_chunks]
    # 检查片段连续
    if indexes != list(range(len(text_chunks))):
        raise ChunkPersistenceError("chunk_index 必须从 0 开始连续递增")
    # 读取本批次哈希、本批次版本
    content_hash = text_chunks[0].content_hash
    version = text_chunks[0].version
    # 检查哈希不能为空
    if not content_hash:
        raise ChunkPersistenceError("content_hash 不能为空")
    # 检查每个片段
    for chunk in text_chunks:
        if not chunk.content.strip():    # 检查正文不能为空
            raise ChunkPersistenceError("content 不能为空")
        if chunk.content_length != len(chunk.content):    # 检查长度字段
            raise ChunkPersistenceError("content_length 与正文长度不一致")
        if chunk.content_hash != content_hash:      # 检查哈希统一
            raise ChunkPersistenceError("所有片段必须使用同一个 content_hash")
        if chunk.version != version:     # 检查版本统一
            raise ChunkPersistenceError("所有片段必须使用同一个 version")

"""保存文章的全部片段并返回数量"""
@transaction.atomic    # 让删除、插入和哈希更新一起提交或回滚
# 原子替换文章片段
def persist_article_chunks(*, article_id: int , text_chunks: list[TextChunk]) -> int:
    validate_text_chunks(text_chunks)
    article = Article.objects.select_for_update().get(pk=article_id)
    ArticleChunk.objects.filter(article=article).delete()
    # 构造待批量保存的对象
    rows = [
        ArticleChunk(
            article=article,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            content_hash=chunk.content_hash,
            article_version=int(chunk.version or article.version),
            section=chunk.section,
            metadata=chunk.metadata,
            vector_document_id="",
        )
        for chunk in text_chunks
    ]
    ArticleChunk.objects.bulk_create(rows)
    article.content_hash = content_hash = text_chunks[0].content_hash
    article.save(update_fields=["content_hash", "updated_at"])
    return len(rows)
