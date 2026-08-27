from django.urls import path
from .views import (
    ArticleListAPIView,
    ArticleDetailAPIView,
)

urlpatterns = [
    #GET /api/articles
    path("",ArticleListAPIView.as_view(), name="article-list"),
    #GET /api/articles/<id>
    path("<int:pk>",ArticleDetailAPIView.as_view(),name="article-detail"),
]