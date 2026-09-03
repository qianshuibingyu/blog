from django.contrib import admin
from .models import Article, ModerationEvent
from .services import approve_article, reject_article, take_down_article

# Register your models here.
# 注册文章 Admin
@admin.register(Article)
class ArticleAdmain(admin.ModelAdmin):
    #Admin 文章列表中显示的字段（文章、作者、业务状态、索引状态、审核时间）
    list_display = (
        "title",
        "author",
        "status",
        "index_status",
        "reviewed_at",
        "updated_at",
    )

    #右侧筛选器
    list_filter=("status", "index_status")

    #顶部搜索框搜索标题
    search_fields=("title", "author__username")

    #服务器字段只读
    readonly_fields=(
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
        "published_at",
        "taken_down_at",
        "reviewed_by",
        "taken_down_by",
        "index_status",
        "index_step",
        "index_error",
        "embedding_error",
        "chroma_error",
        "indexed_at",
        "content_hash",
        "version",
    )
    # 注册审核操作
    actions = (
        "approve_selected",
        "reject_selected",
        "take_down_selected",
    )

    #通过选中的待审核文章
    @admin.action(description="通过选中的待审核文章")
    def approve_selected(self, request, queryset):
        # 逐篇调用服务，不能直接 queryset.update
        for article in queryset:
            approve_article(article=article, actor=request.user)
        self.message_user(request, "文章已进入索引流程")

    # 驳回选中的待审核文章
    @admin.action(description="驳回选中的待审核文章")
    def reject_selected(self, request, queryset):
        # 逐篇调用服务，保证审计和通知完整
        for article in queryset:
            reason = article.moderation_reason or "文章未通过审核。"
            # Service 会写审计、写通知并删除文章
            reject_article(
                article=article,
                actor=request.user,
                reason=reason,
            )
        #显示操作结果
        self.message_user(request, "文章已驳回并删除。")  

    # 下架选中的已发布文章
    @admin.action(description="下架选中的已发布文章")
    def take_down_selected(self, request, queryset):
        # 逐篇调用服务，保证关联数据被清理
        for article in queryset:
            reason = article.moderation_reason or "文章已被管理员下架。"
            # Service 会写审计、写通知并删除文章
            take_down_article(
                article=article,
                actor=request.user,
                reason=reason,
            )
        #显示操作结果
        self.message_user(request, "文章已下架。")

# 注册审核历史
@admin.register(ModerationEvent)
class ModerationEventAdmin(admin.ModelAdmin):
    # 显示对象、动作、操作者和状态变化
    list_display = (
        "object_type",
        "object_id",
        "action",
        "actor",
        "from_status",
        "to_status",
        "created_at",
    )
    # 提供筛选
    list_filter = ("object_type", "action")
    #审计历史只允许查看
    readonly_fields = tuple(
        field.name for field in ModerationEvent._meta.fields
    )