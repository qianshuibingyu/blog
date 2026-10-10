from django.db import transaction     #事务工具
from django.utils import timezone     #时区工具
from notifications.models import Notification    #通知模型
from knowledge.models import ArticleChunk     #文章片段
from knowledge.vector_store import ChromaVectorStore
from .models import ArticleStatus, IndexStatus, ModerationEvent   #文章状态、索引状态、审核事件
from knowledge.index_pipeline import run_article_index

#检查操作者是否为管理员
def ensure_admin(actor):
    if not actor.is_authenticated or not actor.is_staff:
        raise PermissionError("只有管理员可以审核文章")

# 清理文章数据库中的索引映射
def cleanup_article_resources(article):
    ChromaVectorStore().delete_article_vectors(article_id=article.id)
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
    article.index_started_at = timezone.now()
    # 后续阶段从这个步骤继续处理
    article.index_step = "content_validation"
    # 新的一次索引尝试不应显示上一次失败留下的错误
    article.index_error = ""
    article.embedding_error = ""
    article.chroma_error = ""

    article.reviewed_by = actor
    article.reviewed_at = timezone.now()

    article.version += 1

    # 保存本次修改字段
    article.save(
        update_fields=[
            "status",
            "index_status",
            "index_step",
            "index_error",
            "index_started_at",
            "embedding_error",
            "chroma_error",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
            "version",
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
    # 数据库提交后才启动索引，避免任务读取未提交的文章
    transaction.on_commit(
        lambda article_id=article.id: run_article_index(article_id=article_id)
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

"""管理员重新启动失败或过期文章的索引"""
@transaction.atomic
def retry_article_index(*, article, actor):
    ensure_admin(actor)
    retryable = (
        article.status == ArticleStatus.INDEX_FAILED
        and article.index_status == IndexStatus.FAILED
    ) or article.index_status == IndexStatus.STALE
    if not retryable:
        raise ValueError("只有索引失败或过期文章可以重试")
    old_status = article.status
    article.status = ArticleStatus.INDEXING
    article.index_status = IndexStatus.INDEXING
    article.index_step = "content_validation"
    article.index_error = ""
    article.index_started_at = timezone.now()
    article.embedding_error = ""
    article.chroma_error = ""
    article.version += 1
    article.save(
        update_fields=[
            "status", "index_status", "index_step",
            "index_error", "index_started_at", "embedding_error", "chroma_error", "updated_at",
            "version",
        ]
    )
    ModerationEvent.objects.create(
        object_type="article",
        object_id=article.id,
        actor=actor,
        action="retry_index",
        from_status=old_status,
        to_status=article.status,
    )
    transaction.on_commit(
        lambda article_id=article.id: run_article_index(article_id=article_id)
    )
    return article
