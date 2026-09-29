import uuid
import secrets
import string
from django.db import models
from django.conf import settings
from django.core.cache import cache


def generate_ticket_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))


class CommentConcern(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_code = models.CharField(max_length=20, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments_and_concerns"
    )
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    admin_reply = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['ticket_code']),
        ]

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            for _ in range(10):
                code = generate_ticket_code()
                if not CommentConcern.objects.filter(ticket_code=code).exists():
                    self.ticket_code = code
                    break
        super().save(*args, **kwargs)
        cache.delete(f'user_comments_{self.user_id}')
        cache.delete('all_comments_concerns')

    def delete(self, *args, **kwargs):
        cache.delete(f'user_comments_{self.user_id}')
        cache.delete('all_comments_concerns')
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_code} - {self.user.username} ({self.status})"
