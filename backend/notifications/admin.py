from django.contrib import admin
from .models import Notification

# Register your models here.

# 注册通知，方便检查审核结果
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "type",
        "title",
        "is_read",
        "created_at",
    )
    list_filter = ("type", "is_read")
    readonly_fields = ("created_at",)