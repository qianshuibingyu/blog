from django.db import transaction     #事务工具
from django.utils import timezone     #时区工具
from notifications.models import Notification    #通知模型
from knowledge.models import ArticleChunk     #文章片段
from .models import ArticleStatus, IndexStatus, ModerationEvent   #文章状态、索引状态、审核事件

#检查操作者是否为管理员
def ensure_admin(actor):
    if not actor.is_authenticated or not actor.is_staff:
        raise PermissionError("只有管理员可以审核文章")

# 清理文章数据库中的索引映射
def cleanup_article_resources(article):
    ArticleChunk.objects.filter(article=article).delete()

#管理员通过待审核文章
@transaction.atomic
def approve_article(*, article, actor):
    ensure_admin(actor)
    # 只有待审核文章可以通过
    if article.status != ArticleStatus.PENDING_REVIEW:
        raise ValueError("只有待审核文章可以通过")
    # 保存旧状态
    old_status = article.status
    # 进入索引流程，不能直接公开
    article.status = ArticleStatus.INDEXING
    article.index_status = IndexStatus.INDEXING
    article.reviewed_by = actor
    article.reviewed_at = timezone.now()

    # 保存本次修改字段
    article.save(
        update_fields=[
            "status",
            "index_status",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ],
    )

    #保存审核历史
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article.id,
        actor=actor,
        action="approve",
        from_status=old_status,
        to_status=article.status,
    )
    #返回更新后的文章
    return article

#管理员驳回文章，文章直接删除
@transaction.atomic
def reject_article(*, article, actor, reason):
    ensure_admin(actor)
    # 只有待审核文章可以驳回
    if article.status != ArticleStatus.PENDING_REVIEW:
        raise ValueError("只有待审核文章可以驳回")
    # 在删除前保存文章ID、文章作者
    article_id = article.id
    author = article.author
    # 写回驳回审核记录
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article_id,
        actor=actor,
        action="reject",
        from_status=article.status,
        to_status="",
        reason=reason,
    )
    #创建作者通知
    Notification.objects.create(
        recipient=author,
        type="article_rejected",
        title="文章未通过审核",
        message="你的文章未通过审核，原文章已被删除。",
    )
    # 清理文章片段并删除文章
    cleanup_article_resources(article)
    article.delete()

# 管理员下架已经公开的文章
@transaction.atomic
def take_down_article(*, article, actor, reason):
    ensure_admin(actor)
    if article.status != ArticleStatus.PUBLISHED:
        raise ValueError("只有已发布文章可以下架")

    # 保存文章ID
    article_id = article.id
    # 写入下架审核记录
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article_id,
        actor=actor,
        action="offline",
        from_status=article.status,
        to_status=ArticleStatus.OFFLINE,
        reason=reason,
    )
    #通知作者
    Notification.objects.create(
        recipient=article.author,
        type="article_offline",
        title="文章已下架",
        message="你的文章已被管理员下架。",
    )
    # 清理数据库片段、硬删除文章
    cleanup_article_resources(article)
    article.delete()

