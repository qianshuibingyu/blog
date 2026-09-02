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

    def test_unauthenticated_user_article_requests_return_401(self):
        #未登录用户不能读取自己的文章列表
        response = self.client.get("/api/my-articles")
        self.assertEqual(response.status_code, 401)

        #未登录用户不能创建文章
        response = self.client.post(
            "/api/articles",
            {
                "title": "未登录文章",
                "content": "正文",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_my_articles_includes_all_statuses_but_only_current_user(self):
        #创建另一个用户的文章，用来检验数据隔离
        other_user = get_user_model().objects.create_user(
            username="other-user",
            password="other-password",
        )
        other_article = Article.objects.create(
            author=other_user,
            title="其他用户文章",
            content="其他用户正文",
            status=ArticleStatus.DRAFT,
        )

        #模拟当前用户已经登录
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/my-articles")

        self.assertEqual(response.status_code, 200)
        returned_ids = {item["id"] for item in response.data["items"]}
        returned_statuses = {item["status"] for item in response.data["items"]}
        self.assertIn(self.published_article.id, returned_ids)
        self.assertIn(self.draft_article.id, returned_ids)
        self.assertNotIn(other_article.id, returned_ids)
        self.assertIn("published", returned_statuses)
        self.assertIn("draft", returned_statuses)

    def test_create_article_uses_current_user_and_forces_draft(self):
        # 模拟当前用户已经登录
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/articles",
            {
                "title": "新文章",
                "summary": "新文章摘要",
                "content": "新文章正文",
                "author": 999,
                "status": "published",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        article = Article.objects.get(id=response.data["id"])
        self.assertEqual(article.author, self.user)
        self.assertEqual(article.status, ArticleStatus.DRAFT)

    def test_owner_can_edit_draft_but_not_pending_review(self):
        # 模拟当前用户已经登录
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "修改后的标题"},

            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.title, "修改后的标题")

        #待审核文章不能再次编辑
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "不应保存"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_can_submit_draft_for_review(self):
        #模拟当前用户已经登录
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f"/api/articles/{self.draft_article.id}/submit-review",
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.draft_article.refresh_from_db()
        self.assertEqual(
            self.draft_article.status,
            ArticleStatus.PENDING_REVIEW,
        )

    def test_owner_can_delete_article(self):
        #模拟当前用户已经登录
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f"/api/articles/{self.draft_article.id}"
        )

        self.assertEqual(response.status_code,204)
        self.assertFalse(
            Article.objects.filter(id=self.draft_article.id).exists()
        )

    def test_other_user_cannot_operate_my_article(self):
        #创建另一个用户并登录该用户
        other_user = get_user_model().objects.create_user(
            username="another-user",
            password="another-password",
        )
        self.client.force_authenticate(user=other_user)

        # 跨用户文章统一返回404，不裂口文章是否存在
        response = self.client.patch(
            f"/api/articles/{self.draft_article.id}",
            {"title": "越权修改"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(
            f"/api/articles/{self.draft_article.id}"
        )
        self.assertEqual(response.status_code, 404)