from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from .models import Pick, UserParlay
from .serializers import PickSerializer, ParlaySerializer
from .services import BettingService


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
            from .models import SavedPick
            sp, created = SavedPick.objects.get_or_create(
                user=request.user, pick=pick)
            if not created:
                sp.delete()
                return Response({"status": "removed"})
            return Response({"status": "saved"})
        except Pick.DoesNotExist:
            return Response({"error": "Pick not found"}, status=404)

    @action(detail=True, methods=['post'])
    def send_to_tracking(self, request, pk=None):
        try:
            parlay = UserParlay.objects.get(pk=pk, user=request.user)
            parlay.is_tracked = True
            parlay.save(update_fields=['is_tracked'])
            return Response({"status": "sent_to_tracking"})
        except UserParlay.DoesNotExist:
            return Response({"error": "Parlay not found"}, status=404)

    @action(detail=False, methods=['get'])
    def live_tracking(self, request):
        parlays = UserParlay.objects.filter(
            user=request.user, is_tracked=True).prefetch_related('picks__match')
        return Response(ParlaySerializer(parlays, many=True).data)
