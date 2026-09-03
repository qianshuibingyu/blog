from django.db import models
from django.conf import settings

# Create your models here.
# 保存用户看到的站内系统通知
class Notification(models.Model):
    # 指定通知接收人
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # 让 Admin 显示通知名称
    def __str__(self):
        return f"{self.recipient} - {self.title}"