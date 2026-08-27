from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from .models import Article, ArticleStatus

# Create your tests here.

class ArticleAPITests(TestCase):
    def setUp(self):
        #每个测试开始前创建一个测试用户
        User = get_user_model()
        self.user =User.objects.create_user(
            username="test-owner",
            password="test-password",
        )

        #APIClient 用来模拟浏览器请求接口
        self.client = APIClient()

        #创建一篇已发布文章
        self.published_article = Article.objects.create(
            author=self.user,
            title="已发布文章",
            summary="已发布文章摘要",
            content="# 已发布文章正文",
            status=ArticleStatus.PUBLISHED,
        )

        #创建一篇草稿文章
        self.draft_article = Article.objects.create(
            author=self.user,
            title="草稿文章",
            summary="草稿文章摘要",
            content="# 草稿文章正文",
            status=ArticleStatus.DRAFT,
        )

    def test_new_article_defaults_to_draft(self):
        #不传 status 时，文章默认为草稿
        article = Article.objects.create(
            author=self.user,
            title ="默认草稿",
            content="正文",
        )
        self.assertEqual(article.status, ArticleStatus.DRAFT)

    def test_article_list_returns_only_published_article(self):
        response=self.client.get("/api/articles")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["items"]),1)
        self.assertEqual(
            response.data["items"][0]["id"],
            self.published_article.id,
        )

    def test_published_article_detail_returns_content(self):
        response=self.client.get(
            f"/api/articles/{self.published_article.id}"
        )

        self.assertEqual(response.status_code,200)
        self.assertEqual(
            response.data["title"],
            "已发布文章",
        )
        self.assertEqual(
            response.data["content"],
            "# 已发布文章正文",
        )

    def test_missing_article_returns_404(self):
        response=self.client.get("/api/articles/9999")
        self.assertEqual(response.status_code,404)
