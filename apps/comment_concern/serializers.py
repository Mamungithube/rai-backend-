from rest_framework import serializers
from .models import CommentConcern


class CommentConcernSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    formatted_date = serializers.SerializerMethodField()

    class Meta:
        model = CommentConcern
        fields = [
            'id',
            'ticket_code',
            'message',
            'status',
            'status_display',
            'admin_reply',
            'created_at',
            'formatted_date',
            'replied_at'
        ]
        read_only_fields = [
            'id',
            'ticket_code',
            'status',
            'status_display',
            'admin_reply',
            'created_at',
            'formatted_date',
            'replied_at'
        ]

    def get_formatted_date(self, obj):
        if obj.created_at:
            # Format: '25 Aug 2025, 08:54 PM' matching mobile UI
            return obj.created_at.strftime("%d %b %Y, %I:%M %p")
        return None

    def validate_message(self, value):
        cleaned = value.strip() if value else ""
        if not cleaned:
            raise serializers.ValidationError("Comment & Concern message cannot be empty.")
        if len(cleaned) > 5000:
            raise serializers.ValidationError("Message cannot exceed 5000 characters.")
        return cleaned


class AdminReplyCommentConcernSerializer(serializers.Serializer):
    admin_reply = serializers.CharField(required=True, allow_blank=False)
