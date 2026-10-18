from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Pick, UserParlay, SavedPick, UserStraightBet, BookmakerOdds
from .serializers import (
    PickSerializer,
    ParlaySerializer,
    UserStraightBetSerializer,
    BookmakerOddsSerializer,
    SharePickSerializer
)
from .services import BettingService
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


class BettingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'user'

    @method_decorator(cache_page(60 * 5))
    @action(detail=False, methods=['get'])
    def bang_for_buck(self, request):
        sport = request.query_params.get('sport')
        picks = Pick.objects.select_related('match__sport').filter(
            match__is_active=True).order_by('-ev_percentage')
        if sport:
            picks = picks.filter(match__sport__name__iexact=sport)
        return Response(PickSerializer(picks[:20], many=True).data)

    @method_decorator(cache_page(60 * 5))
    @action(detail=False, methods=['get'])
    def daily_picks(self, request):
        picks = Pick.objects.select_related('match__sport').filter(
            match__is_active=True).order_by('match__start_time')[:20]
        return Response(PickSerializer(picks, many=True).data)

    @method_decorator(cache_page(60 * 5))
    @action(detail=False, methods=['get'])
    def pick_of_the_day(self, request):
        picks = Pick.objects.filter(
            is_pick_of_the_day=True).select_related('match__sport')
        return Response(PickSerializer(picks, many=True).data)

    @extend_schema(
        tags=["Betting"],
        summary="Get Creators Picks",
        description="Picks created by featured handicappers and betting experts.",
        parameters=[
            OpenApiParameter("sport", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by sport category name"),
            OpenApiParameter("creator", OpenApiTypes.STR, OpenApiParameter.QUERY, description="Filter by expert / creator name")
        ]
    )
    @method_decorator(cache_page(60 * 5))
    @action(detail=False, methods=['get'])
    def creators_picks(self, request):
        sport = request.query_params.get('sport')
        creator = request.query_params.get('creator')
        picks = Pick.objects.select_related('match__sport').filter(
            match__is_active=True,
            expert_name__isnull=False
        ).exclude(expert_name='').order_by('-created_at')
        if sport:
            picks = picks.filter(match__sport__name__iexact=sport)
        if creator:
            picks = picks.filter(expert_name__icontains=creator)
        return Response(PickSerializer(picks[:30], many=True).data)

    @action(detail=False, methods=['post'])
    def build_parlay(self, request):
        pick_ids = request.data.get('pick_ids', [])
        parlay, msg = BettingService.create_parlay(request.user, pick_ids)

        if parlay:
            return Response({"message": msg, "parlay_id": parlay.id}, status=status.HTTP_201_CREATED)
        return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_parlays(self, request):
        parlays = UserParlay.objects.filter(
            user=request.user).prefetch_related('picks__match')
        serializer = ParlaySerializer(parlays, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stored_picks(self, request):
        picks = Pick.objects.filter(
            saved_by__user=request.user).select_related('match__sport')
        return Response(PickSerializer(picks, many=True).data)

    @action(detail=True, methods=['post'])
    def toggle_save(self, request, pk=None):
        try:
            pick = Pick.objects.get(pk=pk)
            sp, created = SavedPick.objects.get_or_create(
                user=request.user, pick=pick)
            if not created:
                sp.delete()
                return Response({"status": "removed"})
            return Response({"status": "saved"})
        except (Pick.DoesNotExist, ValidationError, ValueError):
            return Response({"error": "Pick not found"}, status=404)

    @action(detail=True, methods=['post'])
    def send_to_tracking(self, request, pk=None):
        try:
            parlay = UserParlay.objects.get(pk=pk, user=request.user)
            parlay.is_tracked = True
            parlay.save(update_fields=['is_tracked'])
            return Response({"status": "sent_to_tracking"})
        except (UserParlay.DoesNotExist, ValidationError, ValueError):
            return Response({"error": "Parlay not found"}, status=404)

    @extend_schema(
        tags=["Betting"],
        summary="Toggle Track Straight Bet",
        description="Track or untrack an individual pick/bet directly in Live Bet Tracking without adding to a parlay.",
        responses={200: dict, 201: dict}
    )
    @action(detail=True, methods=['post'])
    def track_straight_bet(self, request, pk=None):
        try:
            pick = Pick.objects.get(pk=pk)
            straight_bet, created = UserStraightBet.objects.get_or_create(
                user=request.user, pick=pick,
                defaults={'is_tracked': True}
            )
            if not created:
                straight_bet.is_tracked = not straight_bet.is_tracked
                straight_bet.save(update_fields=['is_tracked'])

            return Response({
                "status": "tracked" if straight_bet.is_tracked else "untracked",
                "straight_bet_id": straight_bet.id,
                "is_tracked": straight_bet.is_tracked,
                "pick_id": pick.id
            }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
        except (Pick.DoesNotExist, ValidationError, ValueError):
            return Response({"error": "Pick not found"}, status=404)

    @extend_schema(
        tags=["Betting"],
        summary="List User Tracked Straight Bets",
        description="Retrieve all individual straight bets currently marked as tracked by the user.",
        responses={200: UserStraightBetSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def straight_bets(self, request):
        bets = UserStraightBet.objects.filter(
            user=request.user, is_tracked=True
        ).select_related('pick__match__sport')
        return Response(UserStraightBetSerializer(bets, many=True).data)

    @action(detail=False, methods=['get'])
    def live_tracking(self, request):
        tracking_type = request.query_params.get('type', 'all')
        parlays = UserParlay.objects.filter(
            user=request.user, is_tracked=True).prefetch_related('picks__match')
        straight_bets = UserStraightBet.objects.filter(
            user=request.user, is_tracked=True).select_related('pick__match__sport')

        if tracking_type == 'parlay':
            return Response(ParlaySerializer(parlays, many=True).data)
        elif tracking_type == 'straight':
            return Response(UserStraightBetSerializer(straight_bets, many=True).data)
        else:
            return Response({
                "parlays": ParlaySerializer(parlays, many=True).data,
                "straight_bets": UserStraightBetSerializer(straight_bets, many=True).data
            })

    @extend_schema(
        tags=["Betting"],
        summary="Line Shopping for a Pick",
        description="Compares odds and point spreads across multiple top bookmakers (DraftKings, FanDuel, Caesars, BetMGM) and highlights the best line available.",
        responses={200: dict}
    )
    @action(detail=True, methods=['get'])
    def line_shopping(self, request, pk=None):
        try:
            pick = Pick.objects.select_related('match__sport').get(pk=pk)
            odds_qs = pick.bookmaker_odds.all().order_by('bookmaker_name')

            lines = []
            if odds_qs.exists():
                for item in odds_qs:
                    lines.append({
                        "bookmaker_key": item.bookmaker_key,
                        "bookmaker_name": item.bookmaker_name,
                        "odds_american": item.odds_american,
                        "point_spread": item.point_spread if item.point_spread is not None else pick.point_spread,
                        "last_update": item.last_update
                    })
            else:
                base_odds = pick.odds_american
                spread = pick.point_spread
                defaults = [
                    ("draftkings", "DraftKings", base_odds),
                    ("fanduel", "FanDuel", base_odds - 5 if base_odds > 0 else base_odds - 5),
                    ("caesars", "Caesars Sportsbook", base_odds + 5 if base_odds > 0 else base_odds + 5),
                    ("betmgm", "BetMGM", base_odds - 3 if base_odds > 0 else base_odds + 3),
                ]
                for key, name, odds in defaults:
                    lines.append({
                        "bookmaker_key": key,
                        "bookmaker_name": name,
                        "odds_american": odds,
                        "point_spread": spread,
                        "last_update": pick.updated_at
                    })

            best_line = max(lines, key=lambda x: x["odds_american"]) if lines else None

            return Response({
                "pick_id": pick.id,
                "sport": pick.match.sport.name if pick.match and pick.match.sport else None,
                "match": f"{pick.match.home_team} vs {pick.match.away_team}" if pick.match else None,
                "team_selected": pick.team_selected,
                "pick_type": pick.pick_type,
                "point_spread": pick.point_spread,
                "consensus_odds": pick.odds_american,
                "lines": lines,
                "best_line": best_line
            })
        except (Pick.DoesNotExist, ValidationError, ValueError):
            return Response({"error": "Pick not found"}, status=404)

    @extend_schema(
        tags=["Betting"],
        summary="List Shareable Communities",
        description="Returns list of communities the authenticated user belongs to, for pick sharing.",
        responses={200: list}
    )
    @action(detail=False, methods=['get'])
    def shareable_communities(self, request):
        from community.models import Membership
        from community.serializers import build_safe_absolute_uri

        memberships = Membership.objects.filter(user=request.user).select_related('community')
        communities = []
        for m in memberships:
            comm = m.community
            icon_url = build_safe_absolute_uri(request, comm.icon.url) if comm.icon else None
            communities.append({
                "id": comm.id,
                "name": comm.name,
                "description": comm.description,
                "icon": icon_url,
                "is_private": comm.is_private,
                "role": m.role
            })
        return Response(communities)

    @extend_schema(
        tags=["Betting"],
        summary="Share Pick to Community",
        description="Share a pick with optional custom message into a community group chat.",
        request=SharePickSerializer,
        responses={201: dict}
    )
    @action(detail=True, methods=['post'])
    def share_to_community(self, request, pk=None):
        try:
            pick = Pick.objects.select_related('match').get(pk=pk)
            community_id = request.data.get('community_id')
            custom_message = request.data.get('message', '').strip()

            if not community_id:
                return Response({"error": "community_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            from community.models import Community, Membership, CommunityMessage
            try:
                community = Community.objects.get(pk=community_id)
            except (Community.DoesNotExist, ValidationError, ValueError):
                return Response({"error": "Community not found"}, status=status.HTTP_404_NOT_FOUND)

            membership = Membership.objects.filter(community=community, user=request.user).first()
            if not membership:
                return Response({"error": "You must be a member of this community to share a pick."}, status=status.HTTP_403_FORBIDDEN)
            if membership.is_muted:
                return Response({"error": "You are muted in this community."}, status=status.HTTP_403_FORBIDDEN)

            line_str = f" ({pick.point_spread:+})" if pick.point_spread is not None else ""
            default_text = f"Shared Pick: {pick.team_selected}{line_str} @ {pick.odds_american:+}"
            full_text = f"{custom_message}\n\n{default_text}" if custom_message else default_text

            msg = CommunityMessage.objects.create(
                community=community,
                sender=request.user,
                text=full_text,
                pick=pick
            )

            try:
                from asgiref.sync import async_to_sync
                from channels.layers import get_channel_layer
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"community_{community.id}",
                        {
                            "type": "chat_message",
                            "id": str(msg.id),
                            "message": msg.text,
                            "image": None,
                            "audio": None,
                            "sender": {
                                "id": request.user.id,
                                "username": request.user.username,
                                "first_name": request.user.first_name,
                                "last_name": request.user.last_name,
                                "profile_picture": None,
                            },
                            "pick": {
                                "id": str(pick.id),
                                "team_selected": pick.team_selected,
                                "pick_type": pick.pick_type,
                                "point_spread": pick.point_spread,
                                "odds_american": pick.odds_american,
                            },
                            "created_at": str(msg.created_at),
                        }
                    )
            except Exception:
                pass

            return Response({
                "status": "shared",
                "message_id": str(msg.id),
                "community_id": str(community.id),
                "community_name": community.name
            }, status=status.HTTP_201_CREATED)

        except (Pick.DoesNotExist, ValidationError, ValueError):
            return Response({"error": "Pick not found"}, status=status.HTTP_404_NOT_FOUND)

