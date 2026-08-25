from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from .models import Community, Membership, CommunityMessage, JoinRequest

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    raw_id_fields = ('user',)
    fields = ('user', 'role', 'is_muted', 'joined_at')
    readonly_fields = ('joined_at',)

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon_preview", "is_private", "member_count", "created_at")
    list_filter = ("is_private", "created_at", "updated_at")
    search_fields = ("name", "description", "invite_code")
    readonly_fields = ("id", "invite_code", "created_at", "updated_at")
    inlines = [MembershipInline]
    actions = ['rotate_invite_codes']

    def icon_preview(self, obj):
        if obj.icon:
            return format_html('<img src="{}" style="width: 40px; height: 40px; border-radius: 50%;" />', obj.icon.url)
        return "No Icon"
    icon_preview.short_description = "Icon"

    def member_count(self, obj):
        return obj.memberships.count()
    member_count.short_description = "Members"

    def rotate_invite_codes(self, request, queryset):
        for community in queryset:
            community.rotate_invite_code()
        self.message_user(request, f"Rotated invite codes for {queryset.count()} communities.")
    rotate_invite_codes.short_description = "Rotate/Reset Invite Codes"

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "community", "user", "role", "is_muted", "joined_at")
    list_filter = ("role", "is_muted", "community")
    search_fields = ("user__username", "user__email", "community__name")
    raw_id_fields = ("community", "user")
    ordering = ("-joined_at",)

@admin.register(CommunityMessage)
class CommunityMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "community", "sender", "text_preview", "has_image", "created_at")
    list_filter = ("created_at", "community")
    search_fields = ("text", "sender__username", "community__name")
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("community", "sender")
    ordering = ("-created_at",)

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text
    text_preview.short_description = "Message"

    def has_image(self, obj):
        if obj.image:
            return format_html('<a href="{}" target="_blank">View Image</a>', obj.image.url)
        return "-"
    has_image.short_description = "Image"

@admin.register(JoinRequest)
class JoinRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "community", "user", "created_at")
    list_filter = ("created_at", "community")
    search_fields = ("user__username", "community__name")
    raw_id_fields = ("community", "user")
    ordering = ("-created_at",)
    actions = ['approve_requests']

    def approve_requests(self, request, queryset):
        with transaction.atomic():
            communities = [req.community_id for req in queryset]
            users = [req.user_id for req in queryset]
            
            existing_memberships = set(
                Membership.objects.filter(
                    community_id__in=communities, user_id__in=users
                ).values_list('community_id', 'user_id')
            )
            
            new_memberships = []
            for req in queryset:
                if (req.community_id, req.user_id) not in existing_memberships:
                    new_memberships.append(Membership(
                        community=req.community,
                        user=req.user,
                        role='member'
                    ))
            
            if new_memberships:
                Membership.objects.bulk_create(new_memberships)
            
            count = queryset.count()
            queryset.delete()
            
        self.message_user(request, f"Approved {count} requests successfully.")
    approve_requests.short_description = "Approve selected requests"