from django.db import models
from articles.models import Article

# Create your models here.

# 保存清晰后的文章片段和向量文档映射
class ArticleChunk(models.Model):
    # 每个片段属于一篇文章
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    # 保存片段在文章中的顺序、清晰后的文章片段
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True, default="")
    article_version = models.PositiveIntegerField(default=1)
    section = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    vector_document_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 定义数据库级联合唯一约束
    class Meta:
        # 同一篇文章不能有两个相同序列的片段
        constraints = [
            # 将文章和片段序号组合成唯一键
            models.UniqueConstraint(
                fields=["article", "chunk_index"],
                name="unique_article_chunk_index",
            ),
        ]