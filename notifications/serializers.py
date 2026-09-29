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
