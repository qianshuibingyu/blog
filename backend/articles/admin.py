from django.contrib import admin
from .models import Article

# Register your models here.
@admin.register(Article)
class ArticleAdmain(admin.ModelAdmin):
    #Admin 文章列表中显示的字段
    list_display=(
        "title",
        "status",
        "author",
        "created_at",
        "updated_at",
    )

    #右侧筛选器
    list_filter=("status",)

    #顶部搜索框搜索标题
    search_fields=("title",)

    #时间字段（只读）
    readonly_fields=(
        "created_at",
        "updated_at",
        "published_at",
    )