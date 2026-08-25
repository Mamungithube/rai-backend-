from django.db import models
from django.core.cache import cache
import uuid


class AppPage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    PAGE_CHOICES = (
        ('privacy_policy', 'Privacy Policy'),
        ('terms_conditions', 'Terms & Conditions'),
        ('about_us', 'About Us'),
    )

    slug = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="HTML content for the page")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete('all_app_pages')
        cache.delete(f'app_page_{self.slug}')

    def delete(self, *args, **kwargs):
        cache.delete('all_app_pages')
        cache.delete(f'app_page_{self.slug}')
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.get_slug_display()