from django.urls import path
from .views import (
    ArticleCollectionAPIView,
    ArticleItemAPIView,
)

urlpatterns = [
    #GET /api/articles
    path("",ArticleCollectionAPIView.as_view(),name="article-list",),
    #GET /api/articles/<id>
    path("<int:pk>",ArticleItemAPIView.as_view(),name="article-detail",),
]