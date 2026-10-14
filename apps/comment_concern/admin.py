from django.contrib import admin
from .models import CommentConcern


@admin.register(CommentConcern)
class CommentConcernAdmin(admin.ModelAdmin):
    list_display = ('ticket_code', 'user', 'status', 'short_message', 'created_at', 'replied_at')
    list_filter = ('status', 'created_at')
    search_fields = ('ticket_code', 'user__username', 'user__email', 'message', 'admin_reply')
    readonly_fields = ('ticket_code', 'created_at', 'updated_at', 'replied_at')
    ordering = ('-created_at',)

    def short_message(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    short_message.short_description = "Message"
