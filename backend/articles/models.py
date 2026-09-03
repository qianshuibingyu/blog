from django.conf import settings
from django.db import models
from django.utils import timezone


# 定义文章业务生命周期
class ArticleStatus(models.TextChoices):
    DRAFT = "draft","草稿"
    PENDING_REVIEW = "pending_review","待审核"
    INDEXING = "indexing","索引中"
    INDEX_FAILED = "index_failed","索引失败"
    PUBLISHED = "published","已发布"
    OFFLINE = "offline","已下架"

#定义文章索引生命周期
class IndexStatus(models.TextChoices):
    NOT_INDEXED = "not_indexed","未索引"
    INDEXING = "indexing","索引中"
    INDEXED = "indexed","已索引"
    FAILED = "failed","失败"
    STALE = "stale","过期"



class Article(models.Model):
    # 作者关联 Django 用户；登录功能完成前允许为空。
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="articles",
    )

    # 文章标题。
    title = models.CharField(max_length=200)

    # 文章摘要，可以为空。
    summary = models.TextField(blank=True)

    # Markdown 格式的正文。
    content = models.TextField()

    # 文章状态，默认为草稿。
    status = models.CharField(
        max_length=20,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT,
        db_index=True,
    )

    # 创建时间只在第一次保存时自动设置。
    created_at = models.DateTimeField(auto_now_add=True)

    # 每次保存文章时自动更新时间。
    updated_at = models.DateTimeField(auto_now=True)

    # 记录作者提交审核的时间
    submitted_at = models.DateTimeField(null=True, blank=True)
    # 记录最近一次审核员审核的时间
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # 记录文章第一次公开的时间
    published_at = models.DateTimeField(null=True, blank=True)
    # 记录文章下架的时间
    taken_down_at = models.DateTimeField(null=True, blank=True)
    # 记录最近审核文章的管理员
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_articles",
    )
    # 记录执行下架操作的管理员
    taken_down_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="taken_down_articles",
    )
    # 保存驳回或下架原因
    moderation_reason = models.TextField()
    # 保存索引状态，不能为 NULL
    index_status = models.CharField(
        max_length=20,
        choices=IndexStatus.choices,
        default=IndexStatus.NOT_INDEXED,
    )
    #记录索引正在执行哪一步
    index_step = models.CharField(max_length=20, default="pending")
    #保存整体索引错误
    index_error = models.TextField(blank=True)
    #保存 embedding 错误
    embedding_error = models.TextField(blank=True)
    #保存 Chroma 错误
    chroma_error = models.TextField(blank=True)
    #记录索引完成时间
    indexed_at = models.DateTimeField(null=True, blank=True)
    #保存正文哈希
    content_hash = models.CharField(max_length=64, blank=True)
    #保存索引版本
    version = models.PositiveIntegerField(default=1)

    class Meta:
        # 默认按发布时间倒序，再按创建时间倒序排列。
        ordering = ["-published_at", "-created_at"]

    def save(self,*args,**kwargs):
        #第一次变为已发布时，自动记录当前时间
        if self.status == ArticleStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args,**kwargs)

    def __str__(self):
        # 在 Django Admin 中显示文章标题。
        return f"{self.id} - {self.title} ({self.status})"

# 保存文章和评论的审核操作历史
class ModerationEvent(models.Model):
    object_type = models.CharField(max_length=30)
    object_id = models.PositiveBigIntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="moderation_events",
    )
    action = models.CharField(max_length=30)
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    #让 Admin 显示可读名称
    def __str__(self):
        return f"{self.object_type}#{self.object_id} {self.action}"
