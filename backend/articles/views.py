from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response 
from rest_framework.views import APIView


from .models import Article, ArticleStatus, IndexStatus
from .serializers import (
    ArticleListSerializer,
    ArticleDetailSerializer,
    MyArticleSerializer,
)



# Create your views here.

# 处理 /api/articles 集合路径的 GET 和 POST
class ArticleCollectionAPIView(APIView):
    # GET 对访客开放，只返回已发布文章
    def get(self, request):
        articles = Article.objects.filter(
            status=ArticleStatus.PUBLISHED,
            index_status=IndexStatus.INDEXED,
        )
        serializer = ArticleListSerializer(
            articles,
            many=True,
        )
        return Response({"items": serializer.data})

    # POST 创建草稿，必须先确认用户已登录
    def post(self, request):
        # request.user 由 Django Session 认证产生
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录"},
                status=401,
            )

        serializer = MyArticleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = serializer.save(
            author=request.user,
            status=ArticleStatus.DRAFT,
        )

        return Response(
            MyArticleSerializer(article).data,
            status=201,
        )

class ArticleItemAPIView(APIView):
    def get(self, request, pk):
        # 详情接口仍然只公开已发布文章
        article = get_object_or_404(
            Article.objects.filter(
                status=ArticleStatus.PUBLISHED,
                index_status=IndexStatus.INDEXED,
            ),
            pk=pk,
        )

        return Response(
            ArticleDetailSerializer(article).data,
        )

    # 把“登录+是否本人文章”的判断集中到一个函数
    def _get_owner_article(self, request, pk):
        if not request.user.is_authenticated:
            return None

        return get_object_or_404(
            Article,
            pk=pk,
            author=request.user,
        )


    # PATCH 只允许作者修改自己的草稿
    def patch(self, request, pk):
        article = self._get_owner_article(request, pk)

        if article is None:
            return Response(
                {"detail": "未登录"},
                status=401,
            )

        if article.status != ArticleStatus.DRAFT:
            return Response(
                {"detail": "只有草稿可以编辑"},
                status=400,
            )
        
        # partial=True 允许只提交要修改的字段
        serializer = MyArticleSerializer(
            article,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        # Serializer 的只读字段仍不能被客户端改变
        serializer.save()
        return Response(serializer.data)

    # DELETE 删除当前用户自己的文章
    def delete(self, request, pk):
        article = self._get_owner_article(request, pk)

        if article is None:
            return Response(
                {"detail": "未登录"},
                status= 401,
            )

        article.delete()
        return Response(status=204)

# 处理 /api/my-articles，只返回当前用户的文章
class MyArticleListAPIView(APIView):
    # 当前用户通过 request.user 确定，不能接受 user_id 参数
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录"},
                status=401,
            )

        #这个过滤条件是数据隔离的核心
        articles = Article.objects.filter(
            author=request.user,
        )
        serializer = MyArticleSerializer(
            articles,
            many=True,
        )
        return Response({"items": serializer.data})

# 处理作者提交草稿审核的状态动作
class ArticleSubmitReviewAPIView(APIView):
    # POST 表示执行一次状态变更
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "未登录"},
                status=401,
            )

        article = get_object_or_404(
            Article,
            pk=pk,
            author=request.user,
        )

        if article.status != ArticleStatus.DRAFT:
            return Response(
                {"detail": "只有草稿可以提交审核"},
                status=400,
            )

        #状态转换由服务端执行，不能让客户端直接提交 status
        article.status = ArticleStatus.PENDING_REVIEW
        # 将新的状态持久化到数据库
        article.save()
        return Response(
            MyArticleSerializer(article).data,
        )