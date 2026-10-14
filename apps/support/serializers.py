from rest_framework import serializers
from .models import SupportTicket


class SupportTicketSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'message', 'status', 'status_display',
            'admin_response', 'created_at', 'replied_at'
        ]
        read_only_fields = ['id', 'status', 'admin_response', 'created_at', 'replied_at']

    def validate_message(self, value):
        if len(value) > 5000:
            raise serializers.ValidationError("Message cannot exceed 5000 characters.")
        return value

    def validate_subject(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Subject cannot be blank.")
        return value.strip()