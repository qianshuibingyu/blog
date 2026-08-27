from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response 
from rest_framework.views import APIView


from .models import Article
from .serializers import (
    ArticleListSerializer,
    ArticleDetailSerializer,
)



# Create your views here.

class ArticleListAPIView(APIView):
    #公开文章列表不要求登录
    permission_classes = [AllowAny]

    def get(self,request):
        #只查询已发布的文章，草稿不会进入结果
        articles = Article.objects.filter(
            status = "published"
        )

        #将多个 Article 对象转换成 JSON
        serializer = ArticleListSerializer(
            articles,
            many=True,
        )

        #即使没有文章，也返回空列表，而不是报错
        return Response({
            "items": serializer.data,
        })


class ArticleDetailAPIView(APIView):
    #公开文章详情不要求登录
    permission_classes = [AllowAny]

    def get(self, request ,pk):
        #自从已发布文章中查找
        #草稿和不存在的文章都会触发 404
        article = get_object_or_404(
            Article.objects.filter(status="published"),
            pk=pk,
        )

        #将单篇 Article 转换成详情JSON
        serializer = ArticleDetailSerializer(article)

        return Response(serializer.data)