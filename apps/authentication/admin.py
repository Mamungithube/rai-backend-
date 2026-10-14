from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP
from django.utils.html import format_html

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "id", "username", "email", "phone", "first_name", "last_name",
        "is_email_verified", "is_phone_verified", "is_staff", "is_active",
        "is_admin", "failed_login_attempts", "account_status"
    )
    search_fields = ("username", "email", "phone", "first_name", "last_name")
    list_filter = (
        "is_email_verified", "is_phone_verified", "is_staff",
        "is_active", "is_admin", "created_at"
    )
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "failed_login_attempts", "last_failed_login")
    
    fieldsets = UserAdmin.fieldsets + (
        ("Profile Information", {
            "fields": ("phone", "bio", "profile_picture", "date_of_birth")
        }),
        ("Verification Status", {
            "fields": ("is_email_verified", "is_phone_verified", "is_admin")
        }),
        ("Security", {
            "fields": ("failed_login_attempts", "last_failed_login", "account_locked_until")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )
    
    def account_status(self, obj):
        if obj.is_account_locked():
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    account_status.short_description = "Status"

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("identifier", "code", "is_verified", "attempts", "created_at", "validity_status")
    search_fields = ("identifier", "code")
    list_filter = ("is_verified", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    
    def validity_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Expired/Exceeded</span>')
    validity_status.short_description = "Valid"
    
    actions = ['cleanup_expired_otps']
    
    def cleanup_expired_otps(self, request, queryset):
        OTP.cleanup_expired()
        self.message_user(request, "Expired OTPs cleaned up successfully.")
    cleanup_expired_otps.short_description = "Clean up expired OTPs"