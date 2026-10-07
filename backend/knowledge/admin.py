from django.contrib import admin
from .models import ArticleChunk

# Register your models here.
# 注册文章片段
@admin.register(ArticleChunk)
# 定义只读查看配置
class ArticleChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "article", "vector_document_id", "created_at")   # 列表字段
    search_fields = ("content", "vector_document_id")     #搜索字段
    list_filter = ("article",)         #文章筛选
    readonly_fields = ("article", "chunk_index", "content", "vector_document_id", "created_at", "updated_at")   # 只读设置，禁止后台修改
    # 禁止手工新增片段
    def has_add_permission(self, request):
        return False
    # 禁止手工删除片段
    def has_delete_permission(self, request, obj=None):
        return False