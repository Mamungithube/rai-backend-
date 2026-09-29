from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email', 'reference_id')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


from .models import FCMDevice


@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_type', 'is_active', 'short_token', 'created_at', 'updated_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'fcm_token')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)

    def short_token(self, obj):
        return obj.fcm_token[:25] + "..." if len(obj.fcm_token) > 25 else obj.fcm_token
    short_token.short_description = "FCM Token"
