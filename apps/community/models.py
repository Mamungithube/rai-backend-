from django.db import models
from django.conf import settings
from django.utils.crypto import get_random_string
from django.core.cache import cache
import uuid


class Community(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, max_length=500)
    icon = models.ImageField(upload_to='community_icons/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_private = models.BooleanField(default=False)
    approval_required = models.BooleanField(default=True)
    invite_code = models.CharField(max_length=20, unique=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']

    def _generate_unique_invite_code(self):
        for _ in range(10):
            code = get_random_string(12)
            if not Community.objects.filter(invite_code=code).exclude(pk=self.pk).exists():
                return code
        raise ValueError("Could not generate a unique invite code after 10 attempts.")

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self._generate_unique_invite_code()
        super().save(*args, **kwargs)
        cache.delete('all_communities')
        cache.delete(f'community_{self.id}')

    def delete(self, *args, **kwargs):
        cache.delete('all_communities')
        cache.delete(f'community_{self.id}')
        super().delete(*args, **kwargs)

    def rotate_invite_code(self):
        self.invite_code = self._generate_unique_invite_code()
        self.save(update_fields=['invite_code'])

    def __str__(self):
        return self.name


class Membership(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('member', 'Member'),
    )
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('community', 'user')
        indexes = [
            models.Index(fields=['community', 'user']),
            models.Index(fields=['user', 'role']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'_membership_{self.community_id}_{self.user_id}')
        cache.delete(f'user_memberships_{self.user_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'_membership_{self.community_id}_{self.user_id}')
        cache.delete(f'user_memberships_{self.user_id}')
        super().delete(*args, **kwargs)


class CommunityMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="messages", db_index=True)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_community_messages")
    text = models.TextField(blank=True)
    image = models.ImageField(upload_to='community_images/', null=True, blank=True)
    audio = models.FileField(upload_to='community_audio/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['community', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'community_messages_{self.community_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'community_messages_{self.community_id}')
        super().delete(*args, **kwargs)


class JoinRequest(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('community', 'user')