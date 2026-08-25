from django.db import models
from django.conf import settings
from django.core.cache import cache
import uuid


class SupportTicket(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=255, default="General Concern")
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', db_index=True)
    admin_response = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'user_tickets_{self.user_id}')
        cache.delete('all_support_tickets')

    def delete(self, *args, **kwargs):
        cache.delete(f'user_tickets_{self.user_id}')
        cache.delete('all_support_tickets')
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.subject} ({self.status})"