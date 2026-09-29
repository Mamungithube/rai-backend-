import uuid
from django.db import models
from django.conf import settings
from django.core.cache import cache


class Notification(models.Model):
    TYPE_CHOICES = (
        ('system', 'System'),
        ('comment_reply', 'Comment & Concern Reply'),
        ('support_reply', 'Support Ticket Reply'),
        ('betting', 'Betting / Pick of the Day'),
        ('community', 'Community'),
        ('general', 'General'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general', db_index=True)
    reference_id = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. ticket_code or object id")
    data = models.JSONField(default=dict, blank=True, help_text="Extra payload for deep linking in mobile app")
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'notification_type']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'unread_notifications_count_{self.user_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'unread_notifications_count_{self.user_id}')
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.title} ({'Read' if self.is_read else 'Unread'})"
