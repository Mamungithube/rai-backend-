from rest_framework import serializers
from .models import Pick, Match, UserParlay, SavedPick


class PickSerializer(serializers.ModelSerializer):
    home_team = serializers.CharField(source='match.home_team')
    away_team = serializers.CharField(source='match.away_team')
    home_team_logo = serializers.URLField(source='match.home_team_logo')
    away_team_logo = serializers.URLField(source='match.away_team_logo')
    sport = serializers.CharField(source='match.sport.name')

    class Meta:
        model = Pick
        fields = '__all__'


class ParlaySerializer(serializers.ModelSerializer):
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
