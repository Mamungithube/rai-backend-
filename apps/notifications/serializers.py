from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'notification_type',
            'reference_id',
            'data',
            'is_read',
            'created_at',
            'formatted_date'
        ]
        read_only_fields = [
            'id',
            'title',
            'message',
            'notification_type',
            'reference_id',
            'data',
            'created_at',
            'formatted_date'
        ]

    def get_formatted_date(self, obj):
        if obj.created_at:
            return obj.created_at.strftime("%d %b %Y, %I:%M %p")
        return None


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import FCMDevice
        model = FCMDevice
        fields = ['id', 'fcm_token', 'device_type', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']

    def validate_fcm_token(self, value):
        cleaned = value.strip() if value else ""
        if not cleaned:
            raise serializers.ValidationError("FCM token cannot be empty.")
        return cleaned


class FCMTokenRemoveSerializer(serializers.Serializer):
    fcm_token = serializers.CharField(required=True)
