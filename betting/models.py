import uuid
from django.db import models
from django.conf import settings
from django.core.cache import cache

class SportCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sport = models.ForeignKey(SportCategory, on_delete=models.CASCADE)
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    home_team_logo = models.URLField(blank=True, null=True)
    away_team_logo = models.URLField(blank=True, null=True)
    start_time = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        ordering =['start_time']
        indexes = [
            models.Index(fields=['is_active', 'start_time']),
            models.Index(fields=['sport', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete('active_matches')
        cache.delete(f'match_{self.id}')

    def delete(self, *args, **kwargs):
        cache.delete('active_matches')
        cache.delete(f'match_{self.id}')
        super().delete(*args, **kwargs)

class Pick(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="picks")
    team_selected = models.CharField(max_length=100)
    pick_type = models.CharField(max_length=50)
    point_spread = models.FloatField(null=True, blank=True)
    odds_american = models.IntegerField()
    edge_percentage = models.FloatField(default=0.0)
    ev_percentage = models.FloatField(default=0.0)
    confidence_percentage = models.IntegerField(default=0)
    breakdown_text = models.TextField(blank=True, null=True)
    is_pick_of_the_day = models.BooleanField(default=False, db_index=True)
    expert_name = models.CharField(max_length=100, blank=True, null=True)
    expert_photo = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['match', 'pick_type']),
            models.Index(fields=['is_pick_of_the_day', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'match_picks_{self.match_id}')
        if self.is_pick_of_the_day:
            cache.delete('picks_of_the_day')

    def delete(self, *args, **kwargs):
        cache.delete(f'match_picks_{self.match_id}')
        if self.is_pick_of_the_day:
            cache.delete('picks_of_the_day')
        super().delete(*args, **kwargs)

class UserParlay(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parlays")
    picks = models.ManyToManyField(Pick, related_name="parlays")
    risk_level = models.CharField(max_length=20, default="Medium")
    total_odds = models.IntegerField(default=0)
    overall_confidence = models.IntegerField(default=0)
    is_tracked = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_tracked']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'user_parlays_{self.user_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'user_parlays_{self.user_id}')
        super().delete(*args, **kwargs)

class SavedPick(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_picks")
    pick = models.ForeignKey(Pick, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('user', 'pick')
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(f'user_saved_picks_{self.user_id}')

    def delete(self, *args, **kwargs):
        cache.delete(f'user_saved_picks_{self.user_id}')
        super().delete(*args, **kwargs)