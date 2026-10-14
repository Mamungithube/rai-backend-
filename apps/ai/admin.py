from django.contrib import admin
from .models import Conversation, Message
from django.db.models import Count
class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "text_preview", "created_at")
    ordering = ("created_at",)
    
    def text_preview(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    text_preview.short_description = "Text"

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title_preview", "is_active", "message_count", "created_at", "updated_at")
    list_filter = ("is_active", "created_at", "updated_at")
    search_fields = ("title", "user__username", "user__email")
    inlines = [MessageInline]
    ordering = ("-updated_at",)
    readonly_fields = ("id", "created_at", "updated_at")
    
    def title_preview(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title
    title_preview.short_description = "Title"
    title_preview.admin_order_field = "title"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').annotate(
            msg_count=Count('messages')
        )
    
    def message_count(self, obj):
        return obj.msg_count
    message_count.short_description = "Messages"
    message_count.admin_order_field = "msg_count"

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "sender", "text_preview", "created_at")
    list_filter = ("sender", "created_at")
    search_fields = ("text", "conversation__title", "conversation__user__username")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at")
    
    def text_preview(self, obj):
        return obj.text[:100] + "..." if len(obj.text) > 100 else obj.text
    text_preview.short_description = "Text"