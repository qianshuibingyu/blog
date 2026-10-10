from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

from .models import Article, ArticleStatus, IndexStatus, ModerationEvent
from notifications.models import Notification
from .services import approve_article, reject_article


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
            index_status=IndexStatus.INDEXED,
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

    # 验证管理员通过后文章进入索引流程
    def test_admin_approve_moves_article_to_indexing(self):
        admin = get_user_model().objects.create_user(
            username="review-admin",
            password="password",
            is_staff=True,
        )
        # 把测试文章设置为待审核
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        approve_article(
            article=self.draft_article,
            actor=admin,
        )
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.status, ArticleStatus.INDEXING,)
        self.assertEqual(self.draft_article.index_status, IndexStatus.INDEXING,)
        self.assertEqual(self.draft_article.reviewed_by, admin,)

    # 验证普通用户不能审核
    def test_normal_user_cannot_approve_article(self):
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        with self.assertRaises(PermissionError):
            approve_article(
                article=self.draft_article,
                actor=self.user,
            )
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.status, ArticleStatus.PENDING_REVIEW)

    # 验证驳回会删除文章并通知作者
    def test_reject_deletes_article_and_creates_notification(self):
        # 创建管理员
        admin = get_user_model().objects.create_user(
            username="reject-admin",
            password="password",
            is_staff=True,
        )
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        article_id = self.draft_article.id
        #调用驳回 Service
        reject_article(
            article=self.draft_article,
            actor=admin,
            reason="需要补充技术细节",
        )
        #文章应该被删除
        self.assertFalse(Article.objects.filter(id=article_id).exists())
        #审核事件应该保留
        self.assertTrue(ModerationEvent.objects.filter(object_id=article_id,action="reject",).exists())
        #作者应该收到通知
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user,
                type="article_rejected",
            ).exists()
        )
    
    # 测试管理员通过待审核文章后，文章会进入阶段1的索引入口
    def test_admin_approve_initializes_index_entry(self):
        admin = get_user_model().objects.create_user(
            username="index-entrydmin",
            password="password",
            is_staff=True,
        )
        # 将测试文章设置为作者已提交审核的状态
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        # 调用实际的审核通过业务函数
        approve_article(article=self.draft_article, actor=admin)
        # 从数据库重新读取，避免只检查内存中的旧对象
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.status, ArticleStatus.INDEXING)
        self.assertEqual(self.draft_article.index_status, IndexStatus.INDEXING)
        self.assertEqual(self.draft_article.index_step, "content_validation")
        self.assertEqual(self.draft_article.reviewed_by, admin)
        self.assertIsNotNone(self.draft_article.reviewed_at)
        self.assertNotEqual(self.draft_article.status, ArticleStatus.PUBLISHED)


    # 测试重新开始索引时会清理上一次失败留下的错误
    def test_admin_approve_clears_previous_index_errors(self):
        admin = get_user_model().objects.create_user(
            username="clear-index-errors-admin",
            password="password",
            is_staff=True,
        )
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.index_status = IndexStatus.FAILED
        self.draft_article.index_step = "embedding"
        self.draft_article.index_error = "旧的索引错误"
        self.draft_article.embedding_error = "旧的 embedding 错误"
        self.draft_article.chroma_error = "旧的 Chroma 错误"
        self.draft_article.save()
        # 调用审核通过入口， 开始新的一次索引尝试
        approve_article(article=self.draft_article, actor=admin)
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.index_error, "")
        self.assertEqual(self.draft_article.embedding_error, "")
        self.assertEqual(self.draft_article.chroma_error, "")
        self.assertEqual(self.draft_article.index_step, "content_validation")

    # 测试审核通过操作会写入正确的审核历史
    def test_admin_approve_creates_correct_moderation_event(self):
        admin = get_user_model().objects.create_user(
            username="audit-event-admin",
            password="password",
            is_staff=True,
        )
        self.draft_article.status = ArticleStatus.PENDING_REVIEW
        self.draft_article.save()
        # 调用审核通过入口
        approve_article(article=self.draft_article, actor=admin)
        # 查询当前文章对应的审核通过事件
        event = ModerationEvent.objects.get(
            object_type="article",
            object_id=self.draft_article.id,
            action="approve",
        )
        self.assertEqual(event.actor, admin)
        self.assertEqual(event.from_status, ArticleStatus.PENDING_REVIEW)
        self.assertEqual(event.to_status, ArticleStatus.INDEXING)

    # 测试管理员不能绕过提交审核，直接通过草稿
    def test_admin_cannot_approve_draft_directly(self):
        admin = get_user_model().objects.create_user(
            username="draft-boundary-admin",
            password="password",
            is_staff=True,
        )

        # 断言草稿调用审核通过入口会被拒绝
        with self.assertRaises(ValueError):
            approve_article(article=self.draft_article, actor=admin)

        # 从数据库重新读取文章
        self.draft_article.refresh_from_db()
        self.assertEqual(self.draft_article.status, ArticleStatus.DRAFT)

@patch("articles.services.run_article_index")
def test_approve_starts_index_after_commit(self, run_index):
    admin = get_user_model().objects.create_user(
        username="approve-trigger-admin",
        password="password",
        is_staff=True,
    )
    self.draft_article.status = ArticleStatus.PENDING_REVIEW
    self.draft_article.save()
    with self.captureOnCommitCallbacks(execute=True):
        approve_article(article=self.draft_article, actor=admin)
    run_index.assert_called_once_with(article_id=self.draft_article.id)