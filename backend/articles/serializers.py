from rest_framework import serializers
from .models import Article

class ArticleListSerializer(serializers.ModelSerializer):
    #列表页只返回文章概要，不返回正文
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "published_at",
        )

class ArticleDetailSerializer(serializers.ModelSerializer):
    #详情页需要返回完整 Markdown 正文
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "content",
            "published_at",
        )

class MyArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "summary",
            "content",
            "status",
            "created_at",
            "updated_at",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "index_status",
            "index_step",
        )
        read_only_fields = (
            "id",
            "status",
            "created_at",
            "updated_at",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "index_status",
            "index_step",
        )