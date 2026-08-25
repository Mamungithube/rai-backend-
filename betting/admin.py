from django.contrib import admin
from django.utils.html import format_html
from .models import SportCategory, Match, Pick, UserParlay

@admin.register(SportCategory)
class SportCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon_preview")
    search_fields = ("name",)

    def icon_preview(self, obj):
        if obj.icon_url:
            return format_html('<img src="{}" style="width: 30px; height: 30px; border-radius: 5px;" />', obj.icon_url)
        return "-"
    icon_preview.short_description = "Icon"

class PickInline(admin.TabularInline):
    model = Pick
    extra = 0
    fields = ("team_selected", "pick_type", "point_spread", "odds_american", "confidence_percentage", "ev_percentage", "is_pick_of_the_day")
    readonly_fields = ("confidence_percentage", "ev_percentage", "edge_percentage")

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "match_title", "sport", "start_time", "is_active")
    list_filter = ("sport", "is_active", "start_time")
    search_fields = ("home_team", "away_team")
    inlines = [PickInline]
    ordering = ("-start_time",)

    def match_title(self, obj):
        return f"{obj.away_team} @ {obj.home_team}"
    match_title.short_description = "Matchup"

@admin.register(Pick)
class PickAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "team_selected", "pick_type", "odds_american", "ev_percentage", "is_pick_of_the_day")
    list_filter = ("pick_type", "is_pick_of_the_day", "created_at")
    search_fields = ("team_selected", "match__home_team", "match__away_team", "expert_name")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Core Details", {
            "fields": ("match", "team_selected", "pick_type", "point_spread", "odds_american")
        }),
        ("Calculated Metrics", {
            "fields": ("edge_percentage", "ev_percentage", "confidence_percentage")
        }),
        ("UI Presentation", {
            "fields": ("breakdown_text", "is_pick_of_the_day", "expert_name", "expert_photo")
        }),
        ("System", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    ordering = ("-created_at",)

@admin.register(UserParlay)
class UserParlayAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "risk_level", "total_odds", "overall_confidence", "created_at")
    list_filter = ("risk_level", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "created_at")
    filter_horizontal = ("picks",)
    ordering = ("-created_at",)