from rest_framework import serializers
from .models import Pick, Match, UserParlay, SavedPick, UserStraightBet, BookmakerOdds


class BookmakerOddsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookmakerOdds
        fields = ['id', 'bookmaker_key', 'bookmaker_name', 'odds_american', 'point_spread', 'last_update']


class PickSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    match = serializers.UUIDField(source='match.id', read_only=True)
    home_team = serializers.CharField(source='match.home_team', read_only=True)
    away_team = serializers.CharField(source='match.away_team', read_only=True)
    home_team_logo = serializers.URLField(source='match.home_team_logo', allow_null=True, required=False, read_only=True)
    away_team_logo = serializers.URLField(source='match.away_team_logo', allow_null=True, required=False, read_only=True)
    sport = serializers.CharField(source='match.sport.name', read_only=True)
    bookmaker_odds = BookmakerOddsSerializer(many=True, read_only=True)

    class Meta:
        model = Pick
        fields = '__all__'


class ParlaySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    picks = PickSerializer(many=True, read_only=True)

    class Meta:
        model = UserParlay
        fields = ['id', 'risk_level', 'total_odds',
                  'overall_confidence', 'picks', 'created_at', 'is_tracked']


class SavedPickSerializer(serializers.ModelSerializer):
    pick = PickSerializer(read_only=True)

    class Meta:
        model = SavedPick
        fields = ['id', 'user', 'pick', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class UserStraightBetSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    pick = PickSerializer(read_only=True)

    class Meta:
        model = UserStraightBet
        fields = ['id', 'user', 'pick', 'is_tracked', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class SharePickSerializer(serializers.Serializer):
    community_id = serializers.UUIDField(required=True)
    message = serializers.CharField(required=False, allow_blank=True, default='')

