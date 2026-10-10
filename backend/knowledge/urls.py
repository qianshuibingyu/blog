from django.urls import path
from .api import KnowledgeChatAPIView

urlpatterns = [
    path("chat", KnowledgeChatAPIView.as_view(), name="knowledge-chat"),
]
