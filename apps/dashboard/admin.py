from django.contrib import admin
from .models import AppPage

@admin.register(AppPage)
class AppPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "updated_at")
    readonly_fields = ("updated_at",)
    search_fields = ("title", "content")
    
    fieldsets = (
        ("Page Info", {
            "fields": ("title", "slug")
        }),
        ("Content", {
            "fields": ("content",),
            "description": "Enter the HTML or Text content for this page."
        }),
        ("Timestamps", {
            "fields": ("updated_at",)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj: 
            return self.readonly_fields + ('slug',)
        return self.readonly_fields