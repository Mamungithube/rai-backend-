import base64
import uuid
from django.core.files.base import ContentFile
from rest_framework import serializers
from .models import Community, Membership, CommunityMessage, JoinRequest
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field

User = get_user_model()

ALLOWED_IMAGE_EXTENSIONS = ['jpeg', 'jpg', 'png', 'gif', 'webp']


def build_safe_absolute_uri(request, url):
    if not url:
        return None
    if url.startswith('http'):
        return url
    if request:
        return request.build_absolute_uri(url)
    from django.conf import settings
    return f"{settings.SERVER_BASE_URL}{url}"


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            if data.startswith('data:image'):
                try:
                    format, imgstr = data.split(';base64,')
                    ext = format.split('/')[-1].lower()
                    if ext not in ALLOWED_IMAGE_EXTENSIONS:
                        raise serializers.ValidationError(
                            f"Unsupported image format '{ext}'. "
                            f"Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}."
                        )
                    data = ContentFile(
                        base64.b64decode(imgstr),
                        name=f"{uuid.uuid4().hex}.{ext}"
                    )
                except serializers.ValidationError:
                    raise
                except Exception:
                    raise serializers.ValidationError("Invalid base64 image data.")
            else:
                raise serializers.ValidationError(
                    "Expected a file upload or a base64 encoded image string."
                )
        return super().to_internal_value(data)


class UserShortSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'profile_picture']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return build_safe_absolute_uri(self.context.get('request'), obj.profile_picture.url)
        return None


class JoinRequestSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = JoinRequest
        fields = ['id', 'user', 'created_at']


class CommunityListSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True)
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ['id', 'name', 'icon', 'member_count', 'updated_at']
        read_only_fields = ['icon']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_icon(self, obj):
        if obj.icon:
            return build_safe_absolute_uri(self.context.get('request'), obj.icon.url)
        return None


class MembershipSerializer(serializers.ModelSerializer):
    user = UserShortSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'user', 'role', 'is_muted', 'joined_at']


class CommunityDetailSerializer(serializers.ModelSerializer):
    icon = Base64ImageField(required=False, allow_null=True)
    is_member = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    pending_request_count = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = [
            'id', 'name', 'description', 'icon', 'is_private', 'approval_required',
            'invite_code', 'created_at', 'member_count', 
            'is_member', 'role', 'is_muted', 'pending_request_count'
        ]

    def _get_membership(self, obj):
        cache_key = f'_membership_{obj.pk}'
        if not hasattr(self, cache_key):
            user = self.context['request'].user
            try:
                setattr(self, cache_key, Membership.objects.get(community=obj, user=user))
            except Membership.DoesNotExist:
                setattr(self, cache_key, None)
        return getattr(self, cache_key)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.icon:
            data['icon'] = build_safe_absolute_uri(self.context.get('request'), instance.icon.url)
        else:
            data['icon'] = None
        return data

    @extend_schema_field(serializers.IntegerField)
    def get_member_count(self, obj):
        return obj.memberships.count()

    @extend_schema_field(serializers.BooleanField)
    def get_is_member(self, obj):
        return self._get_membership(obj) is not None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_role(self, obj):
        membership = self._get_membership(obj)
        return membership.role if membership else None

    @extend_schema_field(serializers.BooleanField)
    def get_is_muted(self, obj):
        membership = self._get_membership(obj)
        return membership.is_muted if membership else False



    @extend_schema_field(serializers.IntegerField)
    def get_pending_request_count(self, obj):
        membership = self._get_membership(obj)
        if membership and membership.role == 'admin':
            return obj.join_requests.count()
        return 0


class CommunityMessageSerializer(serializers.ModelSerializer):
    sender = UserShortSerializer(read_only=True)
    image = serializers.SerializerMethodField()
    audio = serializers.SerializerMethodField()
    isme = serializers.SerializerMethodField()

    class Meta:
        model = CommunityMessage
        fields = ['id', 'community', 'sender', 'text', 'image', 'audio', 'created_at', 'isme']
        read_only_fields = ['id', 'created_at', 'sender', 'image', 'audio', 'isme']

    @extend_schema_field(serializers.BooleanField)
    def get_isme(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return obj.sender_id == request.user.id
        return False

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        if obj.image:
            return build_safe_absolute_uri(self.context.get('request'), obj.image.url)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_audio(self, obj):
        if obj.audio:
            return build_safe_absolute_uri(self.context.get('request'), obj.audio.url)
        return None


class CreateCommunitySerializer(serializers.ModelSerializer):
    icon = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Community
        fields = ['name', 'description', 'icon', 'is_private', 'approval_required']

    def validate_icon(self, value):
        if value and value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("Icon size cannot exceed 50MB.")
        return value


class AddMemberSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()


class ChangeMemberRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    role = serializers.ChoiceField(choices=['admin', 'member'], required=True)