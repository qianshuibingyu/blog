from django.conf import settings
from django.db import models
from django.utils import timezone


# 文章状态定义在 Article 类外部，避免在类定义过程中无法引用 Status。
class ArticleStatus(models.TextChoices):
    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"


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

    # 发布时间，可以为空。
    published_at = models.DateTimeField(null=True, blank=True)

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