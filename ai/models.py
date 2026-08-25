from django.db import models
from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.core.cache import cache
import uuid
import tiktoken

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations", db_index=True)
    title = models.CharField(max_length=255, blank=True, db_index=True) 
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    total_tokens_used = models.IntegerField(default=0)

    class Meta:
        ordering =['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_active', '-updated_at']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'user_conversations_{self.user_id}')
        cache.delete(f'conversation_{self.id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'user_conversations_{self.user_id}')
        cache.delete(f'conversation_{self.id}')
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Message(models.Model):
    SENDER_CHOICES = (
        ('user', 'User'),
        ('ai', 'AI'),
    )
    STATUS_CHOICES = (
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages", db_index=True)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, db_index=True)
    text = models.TextField(validators=[MaxLengthValidator(50000)], blank=True)
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', db_index=True)
    token_count = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.token_count and self.text:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                self.token_count = len(encoding.encode(self.text))
            except Exception:
                self.token_count = len(self.text) // 4
                
        super().save(*args, **kwargs)
        cache.delete(f'conversation_messages_{self.conversation_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'conversation_messages_{self.conversation_id}')
        super().delete(*args, **kwargs)

    class Meta:
        ordering = ['created_at']
        indexes =[
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['conversation', 'sender', '-created_at']),
            models.Index(fields=['conversation', 'token_count']),
            models.Index(fields=['conversation', 'sender']),
            models.Index(fields=['conversation', 'image']),
        ]