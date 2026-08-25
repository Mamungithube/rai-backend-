from rest_framework import serializers
from django.contrib.auth import get_user_model
from community.models import Community
from support.models import SupportTicket
from .models import AppPage
from drf_spectacular.utils import extend_schema_field

User = get_user_model()


class AdminUserListSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    join_date = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'photo', 'name', 'email', 'phone', 'join_date', 'status', 'is_active']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_photo(self, obj):
        if obj.profile_picture:
            url = obj.profile_picture.url
            if not url.startswith('http'):
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                from django.conf import settings
                return f"{settings.SERVER_BASE_URL}{url}"
            return url
        return None

    @extend_schema_field(serializers.CharField)
    def get_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username

    @extend_schema_field(serializers.CharField)
    def get_join_date(self, obj):
        return obj.created_at.strftime("%d %b %y, %I:%M %p")

    @extend_schema_field(serializers.CharField)
    def get_status(self, obj):
        return "Active" if obj.is_active else "Inactive"


class AdminCommunityListSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    group_link = serializers.SerializerMethodField()
    create_date = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ['id', 'photo', 'name', 'member_count', 'group_link', 'create_date', 'status']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_photo(self, obj):
        if obj.icon:
            url = obj.icon.url
            if not url.startswith('http'):
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(url)
                from django.conf import settings
                return f"{settings.SERVER_BASE_URL}{url}"
            return url
        return None

    @extend_schema_field(serializers.CharField)
    def get_group_link(self, obj):
        request = self.context.get('request')
        host = request.get_host() if request else "rai.app"
        return f"https://{host}/group/{obj.invite_code}"

    @extend_schema_field(serializers.CharField)
    def get_create_date(self, obj):
        return obj.created_at.strftime("%d %b %y, %I:%M %p")

    @extend_schema_field(serializers.CharField)
    def get_status(self, obj):
        return "Active"


class AdminSupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    create_date = serializers.SerializerMethodField()
    reply_date = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'create_date', 'reply_date', 'user_name', 'user_email',
            'message', 'admin_response', 'status'
        ]

    @extend_schema_field(serializers.CharField)
    def get_create_date(self, obj):
        return obj.created_at.strftime("%d %b %y, %I:%M %p")

    @extend_schema_field(serializers.CharField)
    def get_reply_date(self, obj):
        if obj.replied_at:
            return obj.replied_at.strftime("%d %b %y, %I:%M %p")
        return "--"


class AppPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppPage
        fields = ['slug', 'title', 'content', 'updated_at']
        read_only_fields = ['updated_at']